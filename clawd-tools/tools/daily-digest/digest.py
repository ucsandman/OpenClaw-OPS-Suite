#!/usr/bin/env python3
"""
AgentForge Daily Digest Generator
Auto-compile the day's work into clean summaries.

Usage:
    python digest.py generate           # Generate today's digest
    python digest.py generate --date 2026-02-03
    python digest.py save               # Save to memory file
    python digest.py email              # Format for email
"""

import sqlite3
import json
import argparse
import sys
from datetime import datetime
from pathlib import Path

TOOLS_DIR = Path(__file__).parent.parent
WORKSPACE = TOOLS_DIR.parent
MEMORY_DIR = WORKSPACE / "memory"

def log_error(context: str, error: Exception):
    """Log errors to stderr instead of silently ignoring them."""
    print(f"[WARN] {context}: {type(error).__name__}: {error}", file=sys.stderr)

def gather_daily_data(date=None):
    """Gather all data from tools for a specific date."""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    data = {
        'date': date,
        'decisions': [],
        'lessons': [],
        'context_points': [],
        'ideas_captured': [],
        'ideas_shipped': [],
        'comms': [],
        'goals_progress': [],
        'errors': []
    }
    
    # Learning Database
    try:
        db = TOOLS_DIR / "learning-database" / "data" / "learning.db"
        if db.exists():
            conn = sqlite3.connect(db)
            c = conn.cursor()
            c.execute('SELECT decision, context, tags FROM decisions WHERE timestamp LIKE ?', (f'{date}%',))
            data['decisions'] = [{'decision': r[0], 'context': r[1], 'tags': r[2]} for r in c.fetchall()]
            c.execute('SELECT lesson, confidence FROM lessons WHERE timestamp LIKE ?', (f'{date}%',))
            data['lessons'] = [{'lesson': r[0], 'confidence': r[1]} for r in c.fetchall()]
            conn.close()
    except Exception as e:
        log_error("Learning database", e)
    
    # Context Manager
    try:
        db = TOOLS_DIR / "context-manager" / "data" / "context.db"
        if db.exists():
            conn = sqlite3.connect(db)
            c = conn.cursor()
            c.execute('SELECT content, category, importance FROM key_points WHERE session_id = ?', (date,))
            data['context_points'] = [{'content': r[0], 'category': r[1], 'importance': r[2]} for r in c.fetchall()]
            conn.close()
    except Exception as e:
        log_error("Context manager", e)
    
    # Inspiration
    try:
        db = TOOLS_DIR / "inspiration" / "data" / "ideas.db"
        if db.exists():
            conn = sqlite3.connect(db)
            c = conn.cursor()
            c.execute('SELECT title, tags FROM ideas WHERE captured_at LIKE ?', (f'{date}%',))
            data['ideas_captured'] = [{'title': r[0], 'tags': r[1]} for r in c.fetchall()]
            c.execute('SELECT title, shipped_url FROM ideas WHERE shipped_at LIKE ?', (f'{date}%',))
            data['ideas_shipped'] = [{'title': r[0], 'url': r[1]} for r in c.fetchall()]
            conn.close()
    except Exception as e:
        log_error("Inspiration database", e)
    
    # Communication Analytics
    try:
        db = TOOLS_DIR / "communication-analytics" / "data" / "comms.db"
        if db.exists():
            conn = sqlite3.connect(db)
            c = conn.cursor()
            c.execute('SELECT summary, message_type, response_quality FROM messages WHERE timestamp LIKE ?', (f'{date}%',))
            data['comms'] = [{'summary': r[0], 'type': r[1], 'quality': r[2]} for r in c.fetchall()]
            conn.close()
    except Exception as e:
        log_error("Communication analytics", e)
    
    # Error Logger
    try:
        db = TOOLS_DIR / "error-logger" / "data" / "errors.db"
        if db.exists():
            conn = sqlite3.connect(db)
            c = conn.cursor()
            c.execute('SELECT error, context, severity FROM errors WHERE timestamp LIKE ?', (f'{date}%',))
            data['errors'] = [{'error': r[0], 'context': r[1], 'severity': r[2]} for r in c.fetchall()]
            conn.close()
    except Exception as e:
        log_error("Error logger database", e)
    
    return data

def generate_digest(date=None):
    """Generate a daily digest."""
    data = gather_daily_data(date)
    
    lines = []
    lines.append(f"# Daily Digest - {data['date']}")
    lines.append("")
    
    # Summary stats
    total_items = (len(data['decisions']) + len(data['lessons']) + 
                   len(data['context_points']) + len(data['ideas_captured']))
    lines.append(f"**{total_items} items tracked today**")
    lines.append("")
    
    # Decisions
    if data['decisions']:
        lines.append(f"## Decisions Made ({len(data['decisions'])})")
        for d in data['decisions']:
            lines.append(f"- {d['decision']}")
            if d['context']:
                lines.append(f"  - Context: {d['context'][:60]}...")
        lines.append("")
    
    # Lessons
    if data['lessons']:
        lines.append(f"## Lessons Learned ({len(data['lessons'])})")
        for l in data['lessons']:
            lines.append(f"- ({l['confidence']}%) {l['lesson']}")
        lines.append("")
    
    # Key Points
    if data['context_points']:
        lines.append(f"## Key Points ({len(data['context_points'])})")
        sorted_points = sorted(data['context_points'], key=lambda x: -x['importance'])
        for p in sorted_points[:10]:
            lines.append(f"- [{p['category']}] {'*' * p['importance']} {p['content'][:60]}...")
        lines.append("")
    
    # Ideas
    if data['ideas_captured']:
        lines.append(f"## Ideas Captured ({len(data['ideas_captured'])})")
        for i in data['ideas_captured']:
            lines.append(f"- {i['title']}")
        lines.append("")
    
    if data['ideas_shipped']:
        lines.append(f"## Shipped! ({len(data['ideas_shipped'])})")
        for i in data['ideas_shipped']:
            lines.append(f"- {i['title']}: {i['url'] or 'No URL'}")
        lines.append("")
    
    # Comms
    if data['comms']:
        avg_quality = sum(c['quality'] or 0 for c in data['comms']) / len(data['comms'])
        lines.append(f"## Communications ({len(data['comms'])}, avg quality: {avg_quality:.1f}/5)")
        for c in data['comms'][:5]:
            quality_str = f"[{c['quality']}/5]" if c['quality'] else ""
            lines.append(f"- {quality_str} {c['summary'][:50]}...")
        lines.append("")
    
    # Errors
    if data['errors']:
        lines.append(f"## Errors/Issues ({len(data['errors'])})")
        for e in data['errors']:
            lines.append(f"- [{e['severity']}] {e['error']}")
        lines.append("")
    
    digest = '\n'.join(lines)
    print(digest)
    return digest

def save_digest(date=None):
    """Save digest to memory file."""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    digest = generate_digest(date)
    
    memory_file = MEMORY_DIR / f"{date}.md"
    
    # Append to existing file or create new
    mode = 'a' if memory_file.exists() else 'w'
    with open(memory_file, mode, encoding='utf-8') as f:
        if mode == 'a':
            f.write(f"\n\n---\n\n## Auto-Generated Digest\n\n")
        f.write(digest)
    
    print(f"\n[SAVED] Digest written to {memory_file}")

def main():
    parser = argparse.ArgumentParser(description='Daily Digest Generator')
    parser.add_argument('command', nargs='?', default='generate',
                       choices=['generate', 'save', 'email'])
    parser.add_argument('--date', '-d', help='Date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    if args.command == 'generate':
        generate_digest(args.date)
    elif args.command == 'save':
        save_digest(args.date)
    elif args.command == 'email':
        digest = generate_digest(args.date)
        print("\n--- EMAIL FORMAT ---\n")
        print(f"Subject: AgentForge Daily Digest - {args.date or datetime.now().strftime('%Y-%m-%d')}")
        print("\n" + digest)

if __name__ == '__main__':
    main()
