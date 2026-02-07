#!/usr/bin/env python3
"""
Audit Logger - Track all external actions the agent takes.
Every email, post, API call, file modification logged with timestamps.

Part of the AgentForge Toolkit by Practical Systems.
"""

import sys
import sqlite3
import hashlib
import json
from datetime import datetime
from pathlib import Path
import argparse

# Fix Windows Unicode encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = Path(__file__).parent / "audit.db"

def init_db():
    """Initialize the audit database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action_type TEXT NOT NULL,
            target TEXT,
            content_hash TEXT,
            content_preview TEXT,
            metadata TEXT,
            session_key TEXT,
            success INTEGER DEFAULT 1,
            notes TEXT
        )
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_action_type ON audit_log(action_type)
    ''')
    conn.commit()
    conn.close()

def log_action(action_type: str, target: str = None, content: str = None, 
               metadata: dict = None, session_key: str = None, success: bool = True, notes: str = None):
    """Log an external action."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    content_hash = None
    content_preview = None
    if content:
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        # SECURITY: Hash the preview too - don't store plaintext that might contain secrets
        # Store truncated hash + length indicator for debugging
        preview_hash = hashlib.sha256(content[:200].encode()).hexdigest()[:12]
        content_preview = f"[HASHED:{preview_hash}|len:{len(content)}]"
    
    c.execute('''
        INSERT INTO audit_log (timestamp, action_type, target, content_hash, 
                               content_preview, metadata, session_key, success, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(),
        action_type,
        target,
        content_hash,
        content_preview,
        json.dumps(metadata) if metadata else None,
        session_key,
        1 if success else 0,
        notes
    ))
    
    conn.commit()
    log_id = c.lastrowid
    conn.close()
    
    print(f"[OK] Logged: [{action_type}] → {target or 'N/A'} (id: {log_id})")
    return log_id

def get_recent(limit: int = 20, action_type: str = None):
    """Get recent audit entries."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if action_type:
        c.execute('''
            SELECT id, timestamp, action_type, target, content_preview, success, notes
            FROM audit_log WHERE action_type = ?
            ORDER BY timestamp DESC LIMIT ?
        ''', (action_type, limit))
    else:
        c.execute('''
            SELECT id, timestamp, action_type, target, content_preview, success, notes
            FROM audit_log ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
    
    rows = c.fetchall()
    conn.close()
    return rows

def get_stats():
    """Get audit statistics."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM audit_log')
    total = c.fetchone()[0]
    
    c.execute('''
        SELECT action_type, COUNT(*) as count 
        FROM audit_log GROUP BY action_type ORDER BY count DESC
    ''')
    by_type = c.fetchall()
    
    c.execute('''
        SELECT COUNT(*) FROM audit_log 
        WHERE timestamp > datetime('now', '-24 hours')
    ''')
    last_24h = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM audit_log WHERE success = 0')
    failures = c.fetchone()[0]
    
    conn.close()
    
    return {
        'total': total,
        'by_type': by_type,
        'last_24h': last_24h,
        'failures': failures
    }

def search(query: str, limit: int = 50):
    """Search audit log."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT id, timestamp, action_type, target, content_preview, notes
        FROM audit_log 
        WHERE target LIKE ? OR content_preview LIKE ? OR notes LIKE ?
        ORDER BY timestamp DESC LIMIT ?
    ''', (f'%{query}%', f'%{query}%', f'%{query}%', limit))
    
    rows = c.fetchall()
    conn.close()
    return rows

def main():
    parser = argparse.ArgumentParser(description='Audit Logger - Track external actions')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Log command
    log_parser = subparsers.add_parser('log', help='Log an action')
    log_parser.add_argument('action_type', help='Type: email, post, api, file, message, browser')
    log_parser.add_argument('--target', '-t', help='Target (email address, URL, file path)')
    log_parser.add_argument('--content', '-c', help='Content (will be hashed)')
    log_parser.add_argument('--notes', '-n', help='Additional notes')
    log_parser.add_argument('--failed', action='store_true', help='Mark as failed')
    
    # Recent command
    recent_parser = subparsers.add_parser('recent', help='Show recent entries')
    recent_parser.add_argument('--limit', '-l', type=int, default=20)
    recent_parser.add_argument('--type', '-t', help='Filter by action type')
    
    # Stats command
    subparsers.add_parser('stats', help='Show statistics')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search audit log')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', '-l', type=int, default=50)
    
    args = parser.parse_args()
    
    if args.command == 'log':
        log_action(
            args.action_type,
            target=args.target,
            content=args.content,
            success=not args.failed,
            notes=args.notes
        )
    
    elif args.command == 'recent':
        entries = get_recent(args.limit, args.type)
        if not entries:
            print("No audit entries found.")
            return
        
        print(f"\n{'ID':<5} {'Time':<20} {'Type':<10} {'Target':<30} {'Status':<6}")
        print("-" * 75)
        for entry in entries:
            id_, ts, action_type, target, preview, success, notes = entry
            ts_short = ts[5:16] if ts else ""
            target_short = (target[:28] + "..") if target and len(target) > 30 else (target or "")
            status = "[OK]" if success else "[X]"
            print(f"{id_:<5} {ts_short:<20} {action_type:<10} {target_short:<30} {status:<6}")
    
    elif args.command == 'stats':
        stats = get_stats()
        print(f"\n[#] Audit Statistics")
        print(f"   Total entries: {stats['total']}")
        print(f"   Last 24 hours: {stats['last_24h']}")
        print(f"   Failures: {stats['failures']}")
        print(f"\n   By Type:")
        for action_type, count in stats['by_type']:
            print(f"      {action_type}: {count}")
    
    elif args.command == 'search':
        results = search(args.query, args.limit)
        if not results:
            print(f"No results for '{args.query}'")
            return
        
        print(f"\nResults for '{args.query}':")
        for entry in results:
            id_, ts, action_type, target, preview, notes = entry
            print(f"  [{id_}] {ts[:16]} {action_type} → {target}")
            if preview:
                print(f"      {preview[:80]}...")
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
