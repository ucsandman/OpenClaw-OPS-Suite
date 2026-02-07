#!/usr/bin/env python3
"""
AgentForge Error Logger
Track mistakes, why they happened, prevention strategies.

Usage:
    python errors.py log "what went wrong" --context "situation" --severity high
    python errors.py resolve <id> --fix "what fixed it" --prevention "how to prevent"
    python errors.py patterns
    python errors.py list [--unresolved]
"""

import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "errors.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        error TEXT NOT NULL,
        context TEXT,
        severity TEXT DEFAULT 'medium',
        category TEXT,
        resolved INTEGER DEFAULT 0,
        fix TEXT,
        prevention TEXT,
        recurrence_count INTEGER DEFAULT 1
    )''')
    
    conn.commit()
    conn.close()

def log_error(error, context=None, severity='medium', category=None):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check if similar error exists
    c.execute('SELECT id, recurrence_count FROM errors WHERE error LIKE ?', (f'%{error[:30]}%',))
    existing = c.fetchone()
    
    if existing:
        c.execute('UPDATE errors SET recurrence_count = recurrence_count + 1, timestamp = ? WHERE id = ?',
                  (datetime.now().isoformat(), existing[0]))
        print(f"[!] Error #{existing[0]} recurred (count: {existing[1] + 1})")
        print(f"    {error[:60]}...")
    else:
        c.execute('''INSERT INTO errors (timestamp, error, context, severity, category)
                     VALUES (?, ?, ?, ?, ?)''',
                  (datetime.now().isoformat(), error, context, severity, category))
        error_id = c.lastrowid
        print(f"[X] Error #{error_id} logged")
        print(f"    {error[:60]}...")
        if severity == 'high':
            print(f"    SEVERITY: HIGH - needs immediate attention!")
    
    conn.commit()
    conn.close()

def resolve_error(error_id, fix=None, prevention=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''UPDATE errors SET resolved = 1, fix = ?, prevention = ?
                 WHERE id = ?''', (fix, prevention, error_id))
    
    conn.commit()
    conn.close()
    
    print(f"[OK] Error #{error_id} resolved")
    if fix:
        print(f"    Fix: {fix[:60]}...")
    if prevention:
        print(f"    Prevention: {prevention[:60]}...")

def list_errors(unresolved_only=False):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if unresolved_only:
        c.execute('SELECT id, error, severity, recurrence_count, resolved FROM errors WHERE resolved = 0 ORDER BY severity DESC, recurrence_count DESC')
    else:
        c.execute('SELECT id, error, severity, recurrence_count, resolved FROM errors ORDER BY timestamp DESC LIMIT 20')
    
    errors = c.fetchall()
    conn.close()
    
    if not errors:
        print("No errors found.")
        return
    
    severity_emoji = {'high': '[!!!]', 'medium': '[!]', 'low': '[.]'}
    
    print(f"\n{'='*60}")
    print("ERROR LOG")
    print(f"{'='*60}")
    
    for e in errors:
        emoji = severity_emoji.get(e[2], '[?]')
        status = '[OK]' if e[4] else '[X]'
        recur = f"(x{e[3]})" if e[3] > 1 else ""
        print(f"\n  #{e[0]} {status} {emoji} {recur}")
        print(f"      {e[1][:55]}...")

def analyze_patterns():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print(f"\n{'='*60}")
    print("ERROR PATTERNS")
    print(f"{'='*60}")
    
    # By severity
    c.execute('SELECT severity, COUNT(*), SUM(recurrence_count) FROM errors GROUP BY severity')
    by_severity = c.fetchall()
    
    if by_severity:
        print("\n[BY SEVERITY]")
        for s in by_severity:
            print(f"  {s[0]}: {s[1]} errors, {s[2]} total occurrences")
    
    # Most recurring
    c.execute('SELECT error, recurrence_count FROM errors WHERE recurrence_count > 1 ORDER BY recurrence_count DESC LIMIT 5')
    recurring = c.fetchall()
    
    if recurring:
        print("\n[MOST RECURRING]")
        for r in recurring:
            print(f"  x{r[1]}: {r[0][:50]}...")
    
    # Unresolved
    c.execute('SELECT COUNT(*) FROM errors WHERE resolved = 0')
    unresolved = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM errors')
    total = c.fetchone()[0]
    
    print(f"\n[RESOLUTION RATE]")
    if total > 0:
        print(f"  Resolved: {total - unresolved}/{total} ({100*(total-unresolved)/total:.0f}%)")
        print(f"  Unresolved: {unresolved}")
    
    conn.close()

def main():
    parser = argparse.ArgumentParser(description='Error Logger')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Log
    log_parser = subparsers.add_parser('log', help='Log an error')
    log_parser.add_argument('error', help='What went wrong')
    log_parser.add_argument('--context', '-c', help='Context/situation')
    log_parser.add_argument('--severity', '-s', choices=['low', 'medium', 'high'], default='medium')
    log_parser.add_argument('--category', help='Error category')
    
    # Resolve
    resolve_parser = subparsers.add_parser('resolve', help='Resolve an error')
    resolve_parser.add_argument('id', type=int)
    resolve_parser.add_argument('--fix', '-f', help='What fixed it')
    resolve_parser.add_argument('--prevention', '-p', help='How to prevent')
    
    # List
    list_parser = subparsers.add_parser('list', help='List errors')
    list_parser.add_argument('--unresolved', '-u', action='store_true')
    
    # Patterns
    subparsers.add_parser('patterns', help='Analyze patterns')
    
    # Init
    subparsers.add_parser('init', help='Initialize database')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_db()
        print("Error database initialized.")
    elif args.command == 'log':
        log_error(args.error, args.context, args.severity, args.category)
    elif args.command == 'resolve':
        resolve_error(args.id, args.fix, args.prevention)
    elif args.command == 'list':
        list_errors(args.unresolved)
    elif args.command == 'patterns':
        analyze_patterns()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
