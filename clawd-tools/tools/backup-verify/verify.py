#!/usr/bin/env python3
"""
Backup Verification — non-destructive git health checks.

Usage:
    python verify.py          # full check
    python verify.py --json   # JSON output
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

OK = "OK"
WARN = "WARN"
FAIL = "FAIL"

_COLORS = {OK: "\033[92m", WARN: "\033[93m", FAIL: "\033[91m"}
_RESET = "\033[0m"


def _result(name, status, detail=""):
    return {"name": name, "status": status, "detail": detail}


def _git(*args, cwd=None):
    """Run a git command and return (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            ["git"] + list(args),
            capture_output=True,
            text=True,
            timeout=10,
            cwd=cwd or str(ROOT),
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except FileNotFoundError:
        return -1, "", "git not found"


def check_last_commit_age():
    """Warn if >24h, fail if >72h since last commit."""
    rc, out, err = _git("log", "-1", "--format=%cI")
    if rc != 0 or not out:
        return _result("Last commit age", FAIL, err or "No commits found")

    try:
        commit_dt = datetime.fromisoformat(out)
        now = datetime.now(timezone.utc)
        # Ensure commit_dt is timezone-aware
        if commit_dt.tzinfo is None:
            commit_dt = commit_dt.replace(tzinfo=timezone.utc)
        age_hours = (now - commit_dt).total_seconds() / 3600
        age_str = f"{age_hours:.1f}h ago"

        if age_hours > 72:
            return _result("Last commit age", FAIL, f"{age_str} (>72h)")
        elif age_hours > 24:
            return _result("Last commit age", WARN, f"{age_str} (>24h)")
        else:
            return _result("Last commit age", OK, age_str)
    except Exception as exc:
        return _result("Last commit age", FAIL, str(exc))


def check_uncommitted_changes():
    """Warn if there are modified files."""
    rc, out, _ = _git("status", "--porcelain")
    if rc != 0:
        return _result("Uncommitted changes", FAIL, "git status failed")

    if not out:
        return _result("Uncommitted changes", OK, "Working tree clean")

    lines = [l for l in out.splitlines() if l.strip()]
    return _result("Uncommitted changes", WARN, f"{len(lines)} modified/untracked files")


def check_remote_exists():
    """Report if origin remote is configured."""
    rc, out, _ = _git("remote", "-v")
    if rc != 0 or not out:
        return _result("Remote (origin)", WARN, "No remotes configured")

    if "origin" in out:
        # Extract origin URL
        for line in out.splitlines():
            if line.startswith("origin") and "(push)" in line:
                url = line.split()[1]
                return _result("Remote (origin)", OK, url)
        return _result("Remote (origin)", OK, "Configured")

    return _result("Remote (origin)", WARN, "origin not found in remotes")


def check_unpushed_commits():
    """Warn if there are commits not pushed to origin/master."""
    rc, out, err = _git("log", "origin/master..HEAD", "--oneline")
    if rc != 0:
        if "unknown revision" in err:
            return _result("Unpushed commits", WARN, "No origin/master tracking branch")
        return _result("Unpushed commits", WARN, err[:80])

    if not out:
        return _result("Unpushed commits", OK, "Up to date with origin/master")

    count = len(out.splitlines())
    return _result("Unpushed commits", WARN, f"{count} commit(s) ahead of origin/master")


def check_critical_file_freshness():
    """Check if key files were modified since last commit."""
    results = []
    files = ["MEMORY.md", "memory/heartbeat-state.json"]

    for relpath in files:
        fp = ROOT / relpath
        if not fp.exists():
            results.append(_result(f"Freshness: {relpath}", WARN, "File missing"))
            continue

        # Check if file has uncommitted changes
        rc, out, _ = _git("diff", "--name-only", "HEAD", "--", relpath)
        rc2, out2, _ = _git("diff", "--name-only", "--cached", "--", relpath)
        if out or out2:
            results.append(
                _result(f"Freshness: {relpath}", WARN, "Modified since last commit")
            )
        else:
            results.append(_result(f"Freshness: {relpath}", OK, "Committed"))

    return results


def check_backup_script():
    """Verify backup script exists."""
    script = ROOT / "scripts" / "backup_to_github.ps1"
    if script.exists():
        size = script.stat().st_size
        return _result("Backup script", OK, f"scripts/backup_to_github.ps1 ({size} bytes)")
    return _result("Backup script", WARN, "scripts/backup_to_github.ps1 missing")


def run(as_json=False):
    results = []
    results.append(check_last_commit_age())
    results.append(check_uncommitted_changes())
    results.append(check_remote_exists())
    results.append(check_unpushed_commits())
    results.extend(check_critical_file_freshness())
    results.append(check_backup_script())

    totals = {OK: 0, WARN: 0, FAIL: 0}
    for r in results:
        totals[r["status"]] = totals.get(r["status"], 0) + 1

    if as_json:
        print(json.dumps({"checks": results, "totals": totals}, indent=2))
        return totals

    print(f"\n{'='*50}")
    print("  Backup Verification")
    print(f"{'='*50}\n")

    for r in results:
        color = _COLORS.get(r["status"], "")
        tag = f"[{r['status']}]"
        detail = f" - {r['detail']}" if r["detail"] else ""
        print(f"  {color}{tag:6s}{_RESET} {r['name']}{detail}")

    print()
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
    parser = argparse.ArgumentParser(description="Backup verification")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    totals = run(as_json=args.json)
    if totals.get(FAIL, 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
