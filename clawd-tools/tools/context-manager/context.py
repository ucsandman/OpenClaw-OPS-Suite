#!/usr/bin/env python3
"""
AgentForge Context Manager
Manage conversation context, auto-summarize, and maintain coherence across long sessions.

Usage:
    python context.py capture "key point or decision"
    python context.py summary
    python context.py thread <name> --add "content"
    python context.py thread <name> --view
    python context.py compress
    python context.py export
    python context.py status
"""

import sqlite3
import json
import argparse
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "context.db"
EXPORT_PATH = Path(__file__).parent / "data" / "session-context.md"

def init_db():
    """Initialize the context database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Key points - important things to remember this session
    c.execute('''CREATE TABLE IF NOT EXISTS key_points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT DEFAULT 'general',
        importance INTEGER DEFAULT 5,
        session_id TEXT,
        compressed INTEGER DEFAULT 0
    )''')
    
    # Threads - ongoing conversation topics
    c.execute('''CREATE TABLE IF NOT EXISTS threads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        created TEXT NOT NULL,
        last_updated TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        summary TEXT
    )''')
    
    # Thread entries - individual items in a thread
    c.execute('''CREATE TABLE IF NOT EXISTS thread_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        content TEXT NOT NULL,
        entry_type TEXT DEFAULT 'note',
        FOREIGN KEY (thread_id) REFERENCES threads(id)
    )''')
    
    # Session summaries - compressed context from past sessions
    c.execute('''CREATE TABLE IF NOT EXISTS session_summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_date TEXT NOT NULL,
        summary TEXT NOT NULL,
        key_decisions TEXT,
        open_items TEXT,
        token_estimate INTEGER
    )''')
    
    # Active context - what's currently relevant
    c.execute('''CREATE TABLE IF NOT EXISTS active_context (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        context_type TEXT NOT NULL,
        content TEXT NOT NULL,
        relevance_score INTEGER DEFAULT 5,
        expires TEXT
    )''')
    
    conn.commit()
    conn.close()

def capture_point(content, category='general', importance=5):
    """Capture a key point from the current conversation."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    session_id = datetime.now().strftime('%Y-%m-%d')
    
    c.execute('''INSERT INTO key_points (timestamp, content, category, importance, session_id)
                 VALUES (?, ?, ?, ?, ?)''',
              (datetime.now().isoformat(), content, category, importance, session_id))
    
    point_id = c.lastrowid
    conn.commit()
    conn.close()
    
    importance_stars = "*" * importance
    print(f"[CAPTURED] #{point_id} [{category}] {importance_stars}")
    print(f"  {content}")
    return point_id

def get_summary(include_threads=True, include_recent=True):
    """Get a summary of current context."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n{'='*60}")
    print(f"CONTEXT SUMMARY - {today}")
    print(f"{'='*60}")
    
    # Today's key points
    c.execute('''SELECT content, category, importance FROM key_points 
                 WHERE session_id = ? AND compressed = 0
                 ORDER BY importance DESC, timestamp DESC''', (today,))
    points = c.fetchall()
    
    if points:
        print(f"\n[KEY POINTS TODAY] ({len(points)})")
        for p in points:
            stars = "*" * p[2]
            print(f"  [{p[1]}] {stars} {p[0][:70]}{'...' if len(p[0]) > 70 else ''}")
    
    # Active threads
    if include_threads:
        c.execute('''SELECT name, summary, last_updated FROM threads 
                     WHERE status = 'active'
                     ORDER BY last_updated DESC LIMIT 5''')
        threads = c.fetchall()
        
        if threads:
            print(f"\n[ACTIVE THREADS] ({len(threads)})")
            for t in threads:
                print(f"  > {t[0]}")
                if t[1]:
                    print(f"    {t[1][:60]}...")
    
    # Recent session summaries
    if include_recent:
        c.execute('''SELECT session_date, summary FROM session_summaries 
                     ORDER BY session_date DESC LIMIT 3''')
        summaries = c.fetchall()
        
        if summaries:
            print(f"\n[RECENT SESSIONS]")
            for s in summaries:
                print(f"  {s[0]}: {s[1][:60]}...")
    
    conn.close()

def manage_thread(name, add=None, view=False, close=False, summary=None):
    """Manage conversation threads."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get or create thread
    c.execute('SELECT id, status FROM threads WHERE name = ?', (name,))
    thread = c.fetchone()
    
    if not thread and (add or summary):
        c.execute('''INSERT INTO threads (name, created, last_updated)
                     VALUES (?, ?, ?)''',
                  (name, datetime.now().isoformat(), datetime.now().isoformat()))
        thread_id = c.lastrowid
        print(f"[NEW THREAD] Created: {name}")
    elif thread:
        thread_id = thread[0]
    else:
        print(f"Thread '{name}' not found.")
        conn.close()
        return
    
    if add:
        c.execute('''INSERT INTO thread_entries (thread_id, timestamp, content)
                     VALUES (?, ?, ?)''',
                  (thread_id, datetime.now().isoformat(), add))
        c.execute('UPDATE threads SET last_updated = ? WHERE id = ?',
                  (datetime.now().isoformat(), thread_id))
        print(f"[ADDED] to {name}: {add[:50]}...")
    
    if summary:
        c.execute('UPDATE threads SET summary = ? WHERE id = ?', (summary, thread_id))
        print(f"[SUMMARY] {name}: {summary[:50]}...")
    
    if close:
        c.execute('UPDATE threads SET status = "closed" WHERE id = ?', (thread_id,))
        print(f"[CLOSED] Thread: {name}")
    
    if view:
        c.execute('''SELECT timestamp, content, entry_type FROM thread_entries 
                     WHERE thread_id = ? ORDER BY timestamp''', (thread_id,))
        entries = c.fetchall()
        
        c.execute('SELECT summary, created, status FROM threads WHERE id = ?', (thread_id,))
        thread_info = c.fetchone()
        
        print(f"\n{'='*60}")
        print(f"THREAD: {name}")
        print(f"{'='*60}")
        print(f"Status: {thread_info[2]} | Created: {thread_info[1][:10]}")
        if thread_info[0]:
            print(f"Summary: {thread_info[0]}")
        print(f"\n[ENTRIES] ({len(entries)})")
        for e in entries:
            print(f"  {e[0][:16]} [{e[2]}] {e[1]}")
    
    conn.commit()
    conn.close()

def compress_context():
    """Compress old context into summaries."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Get uncompressed points from previous days
    c.execute('''SELECT session_id, GROUP_CONCAT(content, ' | ') as points, COUNT(*) as count
                 FROM key_points 
                 WHERE compressed = 0 AND session_id < ?
                 GROUP BY session_id''', (today,))
    
    old_sessions = c.fetchall()
    
    if not old_sessions:
        print("No old context to compress.")
        conn.close()
        return
    
    for session in old_sessions:
        session_date = session[0]
        points = session[1]
        count = session[2]
        
        # Create a simple summary (in real use, could use LLM)
        summary = f"{count} key points captured"
        
        c.execute('''INSERT INTO session_summaries (session_date, summary, key_decisions)
                     VALUES (?, ?, ?)''',
                  (session_date, summary, points[:500]))
        
        # Mark as compressed
        c.execute('UPDATE key_points SET compressed = 1 WHERE session_id = ?', (session_date,))
        
        print(f"[COMPRESSED] {session_date}: {count} points -> summary")
    
    conn.commit()
    conn.close()

def export_context():
    """Export current context to a markdown file for easy reference."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    output = [f"# Session Context - {today}\n"]
    output.append(f"*Generated: {datetime.now().isoformat()}*\n")
    
    # Key points
    c.execute('''SELECT content, category, importance FROM key_points 
                 WHERE session_id = ? AND compressed = 0
                 ORDER BY importance DESC''', (today,))
    points = c.fetchall()
    
    if points:
        output.append("\n## Key Points\n")
        for p in points:
            output.append(f"- **[{p[1]}]** {'*' * p[2]} {p[0]}\n")
    
    # Active threads
    c.execute('''SELECT name, summary FROM threads WHERE status = 'active' ''')
    threads = c.fetchall()
    
    if threads:
        output.append("\n## Active Threads\n")
        for t in threads:
            output.append(f"### {t[0]}\n")
            if t[1]:
                output.append(f"{t[1]}\n")
    
    # Recent summaries
    c.execute('''SELECT session_date, summary FROM session_summaries 
                 ORDER BY session_date DESC LIMIT 5''')
    summaries = c.fetchall()
    
    if summaries:
        output.append("\n## Recent Session Summaries\n")
        for s in summaries:
            output.append(f"- **{s[0]}**: {s[1]}\n")
    
    conn.close()
    
    # Write to file
    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EXPORT_PATH, 'w') as f:
        f.writelines(output)
    
    print(f"[EXPORTED] Context written to {EXPORT_PATH}")
    return EXPORT_PATH

def get_status():
    """Get context manager status."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    c.execute('SELECT COUNT(*) FROM key_points WHERE session_id = ? AND compressed = 0', (today,))
    today_points = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM key_points WHERE compressed = 0')
    total_points = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM threads WHERE status = "active"')
    active_threads = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM session_summaries')
    summaries = c.fetchone()[0]
    
    conn.close()
    
    print(f"\n{'='*40}")
    print("CONTEXT MANAGER STATUS")
    print(f"{'='*40}")
    print(f"  Today's key points: {today_points}")
    print(f"  Total uncompressed: {total_points}")
    print(f"  Active threads: {active_threads}")
    print(f"  Session summaries: {summaries}")
    print(f"\n  Database: {DB_PATH}")

def main():
    parser = argparse.ArgumentParser(description='AgentForge Context Manager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Capture
    capture_parser = subparsers.add_parser('capture', help='Capture a key point')
    capture_parser.add_argument('content', help='The key point')
    capture_parser.add_argument('--category', '-c', default='general',
                                help='Category (decision/task/insight/question)')
    capture_parser.add_argument('--importance', '-i', type=int, default=5,
                                help='Importance 1-10')
    
    # Summary
    summary_parser = subparsers.add_parser('summary', help='Get context summary')
    summary_parser.add_argument('--no-threads', action='store_true')
    summary_parser.add_argument('--no-recent', action='store_true')
    
    # Thread
    thread_parser = subparsers.add_parser('thread', help='Manage threads')
    thread_parser.add_argument('name', help='Thread name')
    thread_parser.add_argument('--add', '-a', help='Add entry')
    thread_parser.add_argument('--view', '-v', action='store_true')
    thread_parser.add_argument('--close', action='store_true')
    thread_parser.add_argument('--summary', '-s', help='Set summary')
    
    # Compress
    subparsers.add_parser('compress', help='Compress old context')
    
    # Export
    subparsers.add_parser('export', help='Export context to markdown')
    
    # Status
    subparsers.add_parser('status', help='Show status')
    
    # Init
    subparsers.add_parser('init', help='Initialize database')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_db()
        print("Context database initialized.")
    elif args.command == 'capture':
        capture_point(args.content, args.category, args.importance)
    elif args.command == 'summary':
        get_summary(not args.no_threads, not args.no_recent)
    elif args.command == 'thread':
        manage_thread(args.name, args.add, args.view, args.close, args.summary)
    elif args.command == 'compress':
        compress_context()
    elif args.command == 'export':
        export_context()
    elif args.command == 'status':
        get_status()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
