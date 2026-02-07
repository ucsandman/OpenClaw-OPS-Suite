#!/usr/bin/env python3
"""
System Health Check — databases, services, critical files, binaries.

Usage:
    python health_check.py quick       # files + databases (no network)
    python health_check.py full        # everything
    python health_check.py databases   # just databases
    python health_check.py services    # just services
    python health_check.py --json      # JSON output
"""

import argparse
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

# Resolve project root (clawd/)
ROOT = Path(__file__).resolve().parent.parent.parent

# Import resilience utilities from sibling package
sys.path.insert(0, str(ROOT / "tools" / "core"))
from resilience import check_service, check_port  # noqa: E402

# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

OK = "OK"
WARN = "WARN"
FAIL = "FAIL"

_COLORS = {OK: "\033[92m", WARN: "\033[93m", FAIL: "\033[91m"}
_RESET = "\033[0m"


def _result(name, status, detail=""):
    return {"name": name, "status": status, "detail": detail}


def _print_result(r):
    color = _COLORS.get(r["status"], "")
    tag = f"[{r['status']}]"
    detail = f" - {r['detail']}" if r["detail"] else ""
    print(f"  {color}{tag:6s}{_RESET} {r['name']}{detail}")


# ---------------------------------------------------------------------------
# Category: Databases
# ---------------------------------------------------------------------------


def check_databases():
    results = []
    db_files = sorted(
        p
        for p in ROOT.rglob("*.db")
        if "tools/installed" not in p.as_posix()
        and "node_modules" not in p.as_posix()
    )
    if not db_files:
        results.append(_result("SQLite databases", WARN, "No .db files found"))
        return results

    for db_path in db_files:
        rel = db_path.relative_to(ROOT)
        if not db_path.exists():
            results.append(_result(str(rel), FAIL, "File missing"))
            continue
        if db_path.stat().st_size == 0:
            results.append(_result(str(rel), FAIL, "Empty file (0 bytes)"))
            continue
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.execute("PRAGMA integrity_check")
            row = cur.fetchone()
            conn.close()
            if row and row[0] == "ok":
                size_kb = db_path.stat().st_size / 1024
                results.append(
                    _result(str(rel), OK, f"{size_kb:.0f} KB, integrity ok")
                )
            else:
                results.append(
                    _result(str(rel), FAIL, f"integrity_check: {row}")
                )
        except Exception as exc:
            results.append(_result(str(rel), FAIL, str(exc)))
    return results


# ---------------------------------------------------------------------------
# Category: Services
# ---------------------------------------------------------------------------


def check_services():
    results = []

    # Ollama
    ollama = check_service("http://localhost:11434", timeout=5)
    if ollama["available"]:
        results.append(
            _result(
                "Ollama (localhost:11434)",
                OK,
                f"status {ollama['status']}, {ollama['latency_ms']}ms",
            )
        )
    else:
        results.append(
            _result("Ollama (localhost:11434)", WARN, ollama["error"] or "unreachable")
        )

    # Neon (optional — only if DATABASE_URL set)
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")
    if db_url:
        # Extract host from postgres:// URL
        try:
            from urllib.parse import urlparse

            host = urlparse(db_url).hostname
            port = urlparse(db_url).port or 5432
            if check_port(host, port, timeout=5):
                results.append(_result(f"Neon ({host}:{port})", OK, "TCP reachable"))
            else:
                results.append(
                    _result(f"Neon ({host}:{port})", WARN, "TCP unreachable")
                )
        except Exception as exc:
            results.append(_result("Neon", WARN, f"URL parse error: {exc}"))
    else:
        results.append(
            _result("Neon (DATABASE_URL)", WARN, "Not configured (optional)")
        )

    return results


# ---------------------------------------------------------------------------
# Category: Critical Files
# ---------------------------------------------------------------------------


def check_critical_files():
    results = []

    checks = [
        ("MEMORY.md", True),
        ("TOOLS.md", False),
        ("HEARTBEAT.md", False),
        ("memory/heartbeat-state.json", True),
    ]

    for relpath, required in checks:
        fp = ROOT / relpath
        if not fp.exists():
            status = FAIL if required else WARN
            results.append(_result(relpath, status, "Missing"))
            continue
        if fp.stat().st_size == 0:
            results.append(_result(relpath, WARN, "Empty"))
            continue
        # JSON validity check for .json files
        if fp.suffix == ".json":
            try:
                json.loads(fp.read_text(encoding="utf-8"))
                results.append(_result(relpath, OK, "Valid JSON"))
            except json.JSONDecodeError as exc:
                results.append(_result(relpath, FAIL, f"Invalid JSON: {exc}"))
        else:
            size_kb = fp.stat().st_size / 1024
            results.append(_result(relpath, OK, f"{size_kb:.1f} KB"))

    # secrets/ dir
    secrets_dir = ROOT / "secrets"
    if secrets_dir.is_dir():
        results.append(_result("secrets/", OK, "Directory exists"))
    else:
        results.append(_result("secrets/", WARN, "Missing"))

    # .gitignore contains .env
    gitignore = ROOT / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if ".env" in content:
            results.append(_result(".gitignore has .env", OK, "Listed"))
        else:
            results.append(_result(".gitignore has .env", FAIL, ".env NOT in .gitignore"))
    else:
        results.append(_result(".gitignore", FAIL, "File missing"))

    return results


# ---------------------------------------------------------------------------
# Category: Binaries
# ---------------------------------------------------------------------------


def check_binaries():
    results = []
    required = ["ollama"]
    optional = ["tesseract", "pandoc", "gog"]

    for name in required:
        path = shutil.which(name)
        if path:
            results.append(_result(name, OK, path))
        else:
            results.append(_result(name, FAIL, "Not found in PATH"))

    for name in optional:
        path = shutil.which(name)
        if path:
            results.append(_result(name, OK, path))
        else:
            results.append(_result(name, WARN, "Not found (optional)"))

    return results


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

CATEGORIES = {
    "databases": ("Databases", check_databases),
    "services": ("Services", check_services),
    "files": ("Critical Files", check_critical_files),
    "binaries": ("Binaries", check_binaries),
}

PROFILES = {
    "quick": ["files", "databases"],
    "full": ["databases", "services", "files", "binaries"],
    "databases": ["databases"],
    "services": ["services"],
}


def run(profile="full", as_json=False):
    cats = PROFILES.get(profile, PROFILES["full"])
    all_results = {}
    totals = {OK: 0, WARN: 0, FAIL: 0}

    for key in cats:
        label, fn = CATEGORIES[key]
        results = fn()
        all_results[key] = results
        for r in results:
            totals[r["status"]] = totals.get(r["status"], 0) + 1

    if as_json:
        print(json.dumps({"profile": profile, "categories": all_results, "totals": totals}, indent=2))
        return totals

    print(f"\n{'='*50}")
    print(f"  System Health Check  [{profile}]")
    print(f"{'='*50}\n")

    for key in cats:
        label, _ = CATEGORIES[key]
        print(f"  [{label}]")
        for r in all_results[key]:
            _print_result(r)
        print()

    # Summary line
    summary_parts = []
    if totals[OK]:
        summary_parts.append(f"{_COLORS[OK]}{totals[OK]} OK{_RESET}")
    if totals[WARN]:
        summary_parts.append(f"{_COLORS[WARN]}{totals[WARN]} WARN{_RESET}")
    if totals[FAIL]:
        summary_parts.append(f"{_COLORS[FAIL]}{totals[FAIL]} FAIL{_RESET}")
    print(f"  Summary: {' | '.join(summary_parts)}")
    print()

    return totals


def main():
    parser = argparse.ArgumentParser(description="System health check")
    parser.add_argument(
        "profile",
        nargs="?",
        default="full",
        choices=list(PROFILES.keys()),
        help="Check profile (default: full)",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    totals = run(profile=args.profile, as_json=args.json)

    # Exit code: 1 if any FAIL
    if totals.get(FAIL, 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
