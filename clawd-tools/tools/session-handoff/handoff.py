#!/usr/bin/env python3
"""
AgentForge Session Handoff Tool
Generate context summaries for future-me at session end.

Usage:
    python handoff.py generate          # Generate handoff summary
    python handoff.py save              # Save to memory file
    python handoff.py view [date]       # View past handoff
    python handoff.py quick             # Quick status for new session
"""

import sqlite3
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

TOOLS_DIR = Path(__file__).parent.parent
WORKSPACE = TOOLS_DIR.parent
MEMORY_DIR = WORKSPACE / "memory"
DB_PATH = Path(__file__).parent / "data" / "handoffs.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS handoffs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        session_date TEXT NOT NULL,
        summary TEXT NOT NULL,
        key_decisions TEXT,
        open_tasks TEXT,
        mood_notes TEXT,
        next_priorities TEXT
    )''')
    conn.commit()
    conn.close()

def gather_context():
    """Gather context from all tools."""
    context = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': datetime.now().strftime('%H:%M'),
        'key_points': [],
        'threads': [],
        'decisions': [],
        'lessons': [],
        'ideas': [],
        'comms': [],
        'followups': []
    }
    
    # Context Manager
    try:
        db = TOOLS_DIR / "context-manager" / "data" / "context.db"
        if db.exists():
            conn = sqlite3.connect(db)
            c = conn.cursor()
            today = datetime.now().strftime('%Y-%m-%d')
            c.execute('SELECT content, category, importance FROM key_points WHERE session_id = ? ORDER BY importance DESC', (today,))
            context['key_points'] = [{'content': r[0], 'category': r[1], 'importance': r[2]} for r in c.fetchall()]
            c.execute('SELECT name, summary FROM threads WHERE status = "active"')
            context['threads'] = [{'name': r[0], 'summary': r[1]} for r in c.fetchall()]
            conn.close()
    except: pass
    
    # Learning Database
    try:
        db = TOOLS_DIR / "learning-database" / "data" / "learning.db"
        if db.exists():
            conn = sqlite3.connect(db)
            c = conn.cursor()
            today = datetime.now().strftime('%Y-%m-%d')
            c.execute('SELECT decision, context FROM decisions WHERE timestamp LIKE ? ORDER BY id DESC LIMIT 5', (f'{today}%',))
            context['decisions'] = [{'decision': r[0], 'context': r[1]} for r in c.fetchall()]
            c.execute('SELECT lesson, confidence FROM lessons ORDER BY id DESC LIMIT 3')
            context['lessons'] = [{'lesson': r[0], 'confidence': r[1]} for r in c.fetchall()]
            conn.close()
    except: pass
    
    # Inspiration
    try:
        db = TOOLS_DIR / "inspiration" / "data" / "ideas.db"
        if db.exists():
            conn = sqlite3.connect(db)
            c = conn.cursor()
            c.execute('SELECT title, score FROM ideas WHERE status = "pending" ORDER BY score DESC LIMIT 3')
            context['ideas'] = [{'title': r[0], 'score': r[1]} for r in c.fetchall()]
            conn.close()
    except: pass
    
    # Relationship Tracker
    try:
        db = TOOLS_DIR / "relationship-tracker" / "relationships.db"
        if db.exists():
            conn = sqlite3.connect(db)
            c = conn.cursor()
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            c.execute('SELECT name, platform, follow_up_date FROM contacts WHERE follow_up_date <= ? ORDER BY follow_up_date', (tomorrow,))
            context['followups'] = [{'name': r[0], 'platform': r[1], 'date': r[2]} for r in c.fetchall()]
            conn.close()
    except: pass
    
    return context

def generate_handoff():
    """Generate a handoff summary."""
    context = gather_context()
    
    lines = []
    lines.append(f"# Session Handoff - {context['date']} {context['time']}")
    lines.append("")
    lines.append("## Quick Status for Future Me")
    lines.append("")
    
    # Key points
    if context['key_points']:
        lines.append("### Key Points Today")
        for p in context['key_points'][:5]:
            stars = '*' * min(p['importance'], 5)
            lines.append(f"- [{p['category']}] {stars} {p['content']}")
        lines.append("")
    
    # Active threads
    if context['threads']:
        lines.append("### Active Threads")
        for t in context['threads']:
            lines.append(f"- **{t['name']}**: {t['summary'] or 'No summary yet'}")
        lines.append("")
    
    # Decisions made
    if context['decisions']:
        lines.append("### Decisions Made Today")
        for d in context['decisions']:
            lines.append(f"- {d['decision']}")
        lines.append("")
    
    # Recent lessons
    if context['lessons']:
        lines.append("### Recent Lessons")
        for l in context['lessons']:
            lines.append(f"- ({l['confidence']}%) {l['lesson']}")
        lines.append("")
    
    # Follow-ups due
    if context['followups']:
        lines.append("### Follow-ups Due")
        for f in context['followups']:
            lines.append(f"- {f['name']} ({f['platform']}) - {f['date']}")
        lines.append("")
    
    # Top ideas
    if context['ideas']:
        lines.append("### Top Ideas to Build")
        for i in context['ideas']:
            score = f"[{i['score']}]" if i['score'] else "[unscored]"
            lines.append(f"- {score} {i['title']}")
        lines.append("")
    
    summary = '\n'.join(lines)
    print(summary)
    return summary

def save_handoff():
    """Save handoff to database and memory file."""
    init_db()
    context = gather_context()
    summary = generate_handoff()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO handoffs (timestamp, session_date, summary, key_decisions, open_tasks)
                 VALUES (?, ?, ?, ?, ?)''',
              (datetime.now().isoformat(), context['date'], summary,
               json.dumps(context['decisions']), json.dumps(context['threads'])))
    conn.commit()
    conn.close()
    
    # Also append to daily memory file
    memory_file = MEMORY_DIR / f"{context['date']}.md"
    if memory_file.exists():
        with open(memory_file, 'a', encoding='utf-8') as f:
            f.write(f"\n\n## Session Handoff ({context['time']})\n")
            f.write(summary)
    
    print(f"\n[SAVED] Handoff saved to database and {memory_file.name}")

def quick_status():
    """Quick status for starting a new session."""
    context = gather_context()
    
    print("\n" + "="*50)
    print("QUICK STATUS - New Session")
    print("="*50)
    
    if context['key_points']:
        print(f"\nKey points from today: {len(context['key_points'])}")
        for p in context['key_points'][:3]:
            print(f"  - {p['content'][:50]}...")
    
    if context['threads']:
        print(f"\nActive threads: {len(context['threads'])}")
        for t in context['threads'][:3]:
            print(f"  - {t['name']}")
    
    if context['followups']:
        print(f"\nFollow-ups due: {len(context['followups'])}")
        for f in context['followups']:
            print(f"  - {f['name']} ({f['date']})")
    
    print("\n" + "="*50)

def main():
    parser = argparse.ArgumentParser(description='Session Handoff Tool')
    parser.add_argument('command', nargs='?', default='generate',
                       choices=['generate', 'save', 'quick', 'view'])
    parser.add_argument('--date', '-d', help='Date for view command')
    
    args = parser.parse_args()
    
    if args.command == 'generate':
        generate_handoff()
    elif args.command == 'save':
        save_handoff()
    elif args.command == 'quick':
        quick_status()
    elif args.command == 'view':
        # View past handoff
        init_db()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if args.date:
            c.execute('SELECT summary FROM handoffs WHERE session_date = ? ORDER BY timestamp DESC LIMIT 1', (args.date,))
        else:
            c.execute('SELECT summary FROM handoffs ORDER BY timestamp DESC LIMIT 1')
        result = c.fetchone()
        conn.close()
        if result:
            print(result[0])
        else:
            print("No handoff found.")

if __name__ == '__main__':
    main()
