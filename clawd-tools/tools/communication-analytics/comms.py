#!/usr/bin/env python3
"""
AgentForge Communication Analytics
Track which message styles work best, learn from patterns.

Usage:
    python comms.py log "message summary" --type <type> --response <quality>
    python comms.py patterns
    python comms.py best --type <type>
    python comms.py stats
"""

import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "comms.db"

def init_db():
    """Initialize the communications database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        summary TEXT NOT NULL,
        message_type TEXT,
        platform TEXT,
        audience TEXT,
        tone TEXT,
        length TEXT,
        response_quality INTEGER,
        engagement_score INTEGER DEFAULT 0,
        led_to_action INTEGER DEFAULT 0,
        notes TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS patterns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern_name TEXT UNIQUE NOT NULL,
        description TEXT,
        success_rate REAL DEFAULT 0,
        sample_size INTEGER DEFAULT 0,
        best_for TEXT,
        avoid_when TEXT
    )''')
    
    conn.commit()
    conn.close()

def log_message(summary, msg_type=None, platform=None, audience=None, 
                tone=None, length=None, response=None, engagement=0, action=0, notes=None):
    """Log a communication and its outcome."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO messages 
                 (timestamp, summary, message_type, platform, audience, tone, 
                  length, response_quality, engagement_score, led_to_action, notes)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (datetime.now().isoformat(), summary, msg_type, platform, audience,
               tone, length, response, engagement, action, notes))
    
    msg_id = c.lastrowid
    conn.commit()
    conn.close()
    
    quality_emoji = {1: '[X]', 2: '[~]', 3: '[OK]', 4: '[+]', 5: '[++]'}
    print(f"\n[LOGGED] Message #{msg_id}")
    print(f"  {summary[:50]}...")
    if response:
        print(f"  Response quality: {quality_emoji.get(response, '[?]')} ({response}/5)")
    
    return msg_id

def analyze_patterns():
    """Analyze communication patterns."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print(f"\n{'='*60}")
    print("COMMUNICATION PATTERNS ANALYSIS")
    print(f"{'='*60}")
    
    # By type
    c.execute('''SELECT message_type, 
                        COUNT(*) as count,
                        AVG(response_quality) as avg_response,
                        SUM(led_to_action) as actions
                 FROM messages 
                 WHERE message_type IS NOT NULL
                 GROUP BY message_type
                 ORDER BY avg_response DESC''')
    by_type = c.fetchall()
    
    if by_type:
        print(f"\n[BY MESSAGE TYPE]")
        for t in by_type:
            if t[2]:
                print(f"  {t[0]}: {t[2]:.1f}/5 avg response ({t[1]} samples, {t[3]} actions)")
    
    # By tone
    c.execute('''SELECT tone, 
                        COUNT(*) as count,
                        AVG(response_quality) as avg_response
                 FROM messages 
                 WHERE tone IS NOT NULL AND response_quality IS NOT NULL
                 GROUP BY tone
                 ORDER BY avg_response DESC''')
    by_tone = c.fetchall()
    
    if by_tone:
        print(f"\n[BY TONE]")
        for t in by_tone:
            print(f"  {t[0]}: {t[2]:.1f}/5 ({t[1]} samples)")
    
    # By length
    c.execute('''SELECT length, 
                        COUNT(*) as count,
                        AVG(response_quality) as avg_response
                 FROM messages 
                 WHERE length IS NOT NULL AND response_quality IS NOT NULL
                 GROUP BY length
                 ORDER BY avg_response DESC''')
    by_length = c.fetchall()
    
    if by_length:
        print(f"\n[BY LENGTH]")
        for l in by_length:
            print(f"  {l[0]}: {l[2]:.1f}/5 ({l[1]} samples)")
    
    # By platform
    c.execute('''SELECT platform, 
                        COUNT(*) as count,
                        AVG(response_quality) as avg_response
                 FROM messages 
                 WHERE platform IS NOT NULL AND response_quality IS NOT NULL
                 GROUP BY platform
                 ORDER BY avg_response DESC''')
    by_platform = c.fetchall()
    
    if by_platform:
        print(f"\n[BY PLATFORM]")
        for p in by_platform:
            print(f"  {p[0]}: {p[2]:.1f}/5 ({p[1]} samples)")
    
    conn.close()

def get_best(msg_type=None, platform=None):
    """Get best performing message patterns."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    query = '''SELECT summary, tone, length, response_quality, notes
               FROM messages WHERE response_quality >= 4'''
    params = []
    
    if msg_type:
        query += ' AND message_type = ?'
        params.append(msg_type)
    if platform:
        query += ' AND platform = ?'
        params.append(platform)
    
    query += ' ORDER BY response_quality DESC, engagement_score DESC LIMIT 10'
    
    c.execute(query, params)
    best = c.fetchall()
    conn.close()
    
    if not best:
        print("No high-performing messages found matching criteria.")
        return
    
    print(f"\n{'='*60}")
    print("BEST PERFORMING MESSAGES")
    print(f"{'='*60}")
    
    for b in best:
        quality = '[++]' if b[3] == 5 else '[+]'
        print(f"\n  {quality} {b[0][:50]}...")
        details = []
        if b[1]:
            details.append(f"tone={b[1]}")
        if b[2]:
            details.append(f"length={b[2]}")
        if details:
            print(f"      {', '.join(details)}")
        if b[4]:
            print(f"      Note: {b[4][:40]}...")

def get_stats():
    """Get communication statistics."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM messages')
    total = c.fetchone()[0]
    
    c.execute('SELECT AVG(response_quality) FROM messages WHERE response_quality IS NOT NULL')
    avg_response = c.fetchone()[0] or 0
    
    c.execute('SELECT SUM(led_to_action) FROM messages')
    total_actions = c.fetchone()[0] or 0
    
    c.execute('SELECT COUNT(*) FROM messages WHERE response_quality >= 4')
    high_quality = c.fetchone()[0]
    
    conn.close()
    
    print(f"\n{'='*40}")
    print("COMMUNICATION STATS")
    print(f"{'='*40}")
    print(f"  Total logged: {total}")
    print(f"  Avg response quality: {avg_response:.1f}/5")
    print(f"  High quality (4+): {high_quality} ({100*high_quality/total:.0f}%)" if total > 0 else "")
    print(f"  Led to action: {total_actions}")
    print(f"\n  Database: {DB_PATH}")

def main():
    parser = argparse.ArgumentParser(description='AgentForge Communication Analytics')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Log
    log_parser = subparsers.add_parser('log', help='Log a communication')
    log_parser.add_argument('summary', help='Message summary')
    log_parser.add_argument('--type', '-t', help='Message type (request/update/pitch/question/response)')
    log_parser.add_argument('--platform', '-p', help='Platform (telegram/moltbook/linkedin/email)')
    log_parser.add_argument('--audience', '-a', help='Audience type')
    log_parser.add_argument('--tone', help='Tone (casual/professional/enthusiastic/direct)')
    log_parser.add_argument('--length', '-l', help='Length (short/medium/long)')
    log_parser.add_argument('--response', '-r', type=int, choices=[1,2,3,4,5], help='Response quality 1-5')
    log_parser.add_argument('--engagement', '-e', type=int, default=0, help='Engagement score')
    log_parser.add_argument('--action', type=int, default=0, help='Led to action (0/1)')
    log_parser.add_argument('--notes', '-n', help='Notes')
    
    # Patterns
    subparsers.add_parser('patterns', help='Analyze patterns')
    
    # Best
    best_parser = subparsers.add_parser('best', help='Show best performers')
    best_parser.add_argument('--type', '-t', help='Filter by type')
    best_parser.add_argument('--platform', '-p', help='Filter by platform')
    
    # Stats
    subparsers.add_parser('stats', help='Show statistics')
    
    # Init
    subparsers.add_parser('init', help='Initialize database')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_db()
        print("Communications database initialized.")
    elif args.command == 'log':
        log_message(args.summary, args.type, args.platform, args.audience,
                   args.tone, args.length, args.response, args.engagement, 
                   args.action, args.notes)
    elif args.command == 'patterns':
        analyze_patterns()
    elif args.command == 'best':
        get_best(args.type, args.platform)
    elif args.command == 'stats':
        get_stats()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
