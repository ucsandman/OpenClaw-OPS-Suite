"""Skill Safety Checker

Goal
----
Lightweight static scan to reduce risk when using *third‑party* ("open") Clawdbot skills.

This is NOT a sandbox and cannot guarantee safety.
It is a fast, deterministic review aid that flags common foot-guns:
- network exfil patterns (curl/wget/Invoke-WebRequest, requests, fetch)
- code execution (eval/exec, subprocess/os.system)
- destructive commands (rm/del/format)
- secrets in code (api keys, Bearer tokens, private keys, DATABASE_URL)
- paths outside workspace

Usage
-----
python tools/security/skill_checker.py scan
python tools/security/skill_checker.py scan --paths "C:\\some\\dir" "C:\\other"
python tools/security/skill_checker.py scan --json out.json
python tools/security/skill_checker.py scan --fail-on high

Exit codes
----------
0: no findings at/above fail threshold
1: findings at/above fail threshold
2: unexpected error
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
import sys


# ----------------------------
# Findings model
# ----------------------------

SEVERITY_ORDER = {"low": 10, "medium": 20, "high": 30}


@dataclass
class Finding:
    severity: str
    rule_id: str
    message: str
    path: str
    line: Optional[int] = None
    snippet: Optional[str] = None


# ----------------------------
# Rules
# ----------------------------

# Regex rules are intentionally broad: we prefer false positives over misses.
RULES: List[Tuple[str, str, re.Pattern, str]] = [
    (
        "high",
        "EXEC_EVAL",
        re.compile(r"(?<!\.)\b(eval|exec)\s*\(", re.IGNORECASE),
        "Dynamic code execution (eval/exec)",
    ),
    (
        "high",
        "SUBPROCESS_SHELL",
        re.compile(r"\b(subprocess\.(Popen|run|call)|os\.system)\b", re.IGNORECASE),
        "Shell execution (subprocess/os.system)",
    ),
    (
        "high",
        "POWERSHELL_ENCODED",
        re.compile(r"-EncodedCommand\b|-enc\b", re.IGNORECASE),
        "PowerShell encoded command flag (obfuscation/exfil risk)",
    ),
    (
        "high",
        "DESTRUCTIVE_CMD",
        re.compile(r"\b(rm\s+-rf|del\s+/f|Remove-Item\s+-Recurse\s+-Force|diskpart\b|shutdown\b)\b", re.IGNORECASE),
        "Potentially destructive command",
    ),
    (
        "medium",
        "NETWORK_TOOL",
        re.compile(r"\b(curl|wget|Invoke-WebRequest|iwr|Invoke-RestMethod|irm)\b", re.IGNORECASE),
        "Direct network tool usage",
    ),
    (
        "medium",
        "HTTP_LIB",
        re.compile(r"\b(requests\.|httpx\.|urllib\.|fetch\(|axios\b)"),
        "HTTP client usage",
    ),
    (
        "high",
        "SECRET_BEARER",
        re.compile(r"Bearer\s+[A-Za-z0-9\-_.=]{10,}"),
        "Bearer token-like string present",
    ),
    (
        "high",
        "SECRET_OPENAI",
        re.compile(r"\bsk-[A-Za-z0-9]{10,}"),
        "OpenAI-style API key pattern present",
    ),
    (
        "high",
        "SECRET_PRIVATE_KEY",
        re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|PRIVATE) KEY-----"),
        "PEM private key material present",
    ),
    (
        "high",
        "SECRET_DBURL",
        re.compile(r"\bDATABASE_URL\b|postgres(ql)?://|mysql://|sqlite:///"),
        "Database URL / DATABASE_URL reference",
    ),
    (
        "low",
        "SUSPICIOUS_BASE64",
        re.compile(r"\bbase64\b", re.IGNORECASE),
        "Base64 usage (often used for obfuscation; review)",
    ),
]

# Files we scan. Expand as needed.
SCAN_EXTS = {
    ".md",
    ".py",
    ".js",
    ".ts",
    ".json",
    ".yaml",
    ".yml",
    ".ps1",
    ".sh",
    ".bat",
}

# Skip dependencies and generated output by default.
IGNORE_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "out",
    ".next",
    ".venv",
    "venv",
    "__pycache__",
}


def default_scan_paths() -> List[Path]:
    """Default to first-party local skills + installed clawdbot skills."""
    paths: List[Path] = []

    # Workspace first-party skills
    paths.append(Path.cwd() / "skills")

    # Installed clawdbot skills (global npm). Allow override.
    # NOTE: safe to scan read-only; this is a review tool.
    npm_skills = Path(os.environ.get(
        "CLAWDBOT_INSTALLED_SKILLS_DIR",
        "",
    ))
    if str(npm_skills).strip():
        paths.append(npm_skills)

    # De-dup and keep existing dirs only.
    out: List[Path] = []
    seen = set()
    for p in paths:
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        if str(rp).lower() in seen:
            continue
        seen.add(str(rp).lower())
        if rp.exists():
            out.append(rp)
    return out


def iter_files(paths: Iterable[Path]) -> Iterable[Path]:
    for base in paths:
        if not base.exists():
            continue
        if base.is_file():
            if base.suffix.lower() in SCAN_EXTS:
                yield base
            continue

        for p in base.rglob("*"):
            # Skip ignored directories anywhere in the path.
            if any(part in IGNORE_DIRS for part in p.parts):
                continue
            if p.is_file() and p.suffix.lower() in SCAN_EXTS:
                yield p


def scan_text_file(path: Path) -> List[Finding]:
    findings: List[Finding] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        findings.append(Finding(
            severity="medium",
            rule_id="READ_ERROR",
            message=f"Could not read file: {e}",
            path=str(path),
        ))
        return findings

    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        for severity, rule_id, rx, msg in RULES:
            if rx.search(line):
                findings.append(Finding(
                    severity=severity,
                    rule_id=rule_id,
                    message=msg,
                    path=str(path),
                    line=idx,
                    snippet=line.strip()[:300],
                ))

    # Extra heuristic: absolute paths outside the workspace
    # We flag Windows absolute paths; reviewer decides if it's legitimate.
    workspace = str(Path.cwd().resolve()).lower()
    win_path_rx = re.compile(r"[A-Za-z]:\\[^\s\"']+")
    for idx, line in enumerate(lines, start=1):
        for m in win_path_rx.finditer(line):
            p = m.group(0)
            try:
                rp = str(Path(p).resolve()).lower()
            except Exception:
                rp = p.lower()
            if workspace not in rp:
                findings.append(Finding(
                    severity="low",
                    rule_id="ABS_PATH_OUTSIDE_WORKSPACE",
                    message="Absolute path appears outside current workspace; review for portability/safety",
                    path=str(path),
                    line=idx,
                    snippet=line.strip()[:300],
                ))

    return findings


def severity_ge(a: str, b: str) -> bool:
    return SEVERITY_ORDER.get(a, 0) >= SEVERITY_ORDER.get(b, 0)


def main() -> int:
    # Avoid Windows console encoding crashes when files contain emojis.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Static safety scan for Clawdbot skills")
    sub = ap.add_subparsers(dest="cmd", required=True)

    scan = sub.add_parser("scan", help="Scan skill directories/files")
    scan.add_argument(
        "--paths",
        nargs="*",
        help="Paths to scan (defaults: workspace skills + installed clawdbot skills)",
    )
    scan.add_argument(
        "--json",
        dest="json_out",
        help="Write findings as JSON to this file",
    )
    scan.add_argument(
        "--fail-on",
        choices=["low", "medium", "high"],
        default="high",
        help="Exit nonzero if any findings at or above this severity (default: high)",
    )
    scan.add_argument(
        "--max",
        type=int,
        default=2000,
        help="Max findings to report (default: 2000)",
    )

    args = ap.parse_args()

    if args.cmd == "scan":
        if args.paths:
            scan_paths = [Path(p) for p in args.paths]
        else:
            scan_paths = default_scan_paths()

        all_findings: List[Finding] = []
        for fpath in iter_files(scan_paths):
            all_findings.extend(scan_text_file(fpath))
            if len(all_findings) >= args.max:
                all_findings = all_findings[: args.max]
                break

        # Write JSON if requested
        if args.json_out:
            outp = Path(args.json_out)
            outp.parent.mkdir(parents=True, exist_ok=True)
            outp.write_text(
                json.dumps([asdict(f) for f in all_findings], indent=2),
                encoding="utf-8",
            )

        # Human report
        if not all_findings:
            print("No findings.")
        else:
            by_sev = {"high": 0, "medium": 0, "low": 0}
            for f in all_findings:
                by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
            print(f"Findings: high={by_sev.get('high',0)} medium={by_sev.get('medium',0)} low={by_sev.get('low',0)}")
            for f in all_findings[:200]:
                loc = f"{f.path}:{f.line}" if f.line else f.path
                print(f"- [{f.severity.upper()}] {f.rule_id} {loc}\n    {f.message}\n    {f.snippet or ''}")
            if len(all_findings) > 200:
                print(f"... ({len(all_findings)-200} more not shown)")

        fail = any(severity_ge(f.severity, args.fail_on) for f in all_findings)
        return 1 if fail else 0

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise SystemExit(2)
