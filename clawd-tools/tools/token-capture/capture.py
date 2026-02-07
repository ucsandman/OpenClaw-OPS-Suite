#!/usr/bin/env python3
"""
Token Usage Capture Tool
Captures real token usage from Clawdbot session_status and stores in SQLite.
Run via heartbeat for continuous tracking.
"""

import sqlite3
import json
import re
import sys
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "tokens.db"

def init_db():
    """Initialize the database with required tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS token_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            tokens_in INTEGER,
            tokens_out INTEGER,
            context_used INTEGER,
            context_max INTEGER,
            context_pct REAL,
            hourly_pct_left REAL,
            weekly_pct_left REAL,
            compactions INTEGER,
            model TEXT,
            session_key TEXT,
            raw_status TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_totals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            total_tokens_in INTEGER DEFAULT 0,
            total_tokens_out INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            peak_context_pct REAL DEFAULT 0,
            snapshots_count INTEGER DEFAULT 0,
            estimated_cost_usd REAL DEFAULT 0
        )
    ''')
    
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp 
        ON token_snapshots(timestamp)
    ''')
    
    conn.commit()
    conn.close()
    print(f"[OK] Database initialized: {DB_PATH}")

def parse_status(status_text):
    """Parse the session_status output into structured data."""
    data = {
        'timestamp': datetime.now().isoformat(),
        'tokens_in': 0,
        'tokens_out': 0,
        'context_used': 0,
        'context_max': 0,
        'context_pct': 0,
        'hourly_pct_left': 0,
        'weekly_pct_left': 0,
        'compactions': 0,
        'model': '',
        'session_key': '',
        'raw_status': status_text
    }
    
    # Parse tokens: "🧮 Tokens: 10 in / 885 out"
    tokens_match = re.search(r'Tokens:\s*(\d+)\s*in\s*/\s*(\d+)\s*out', status_text)
    if tokens_match:
        data['tokens_in'] = int(tokens_match.group(1))
        data['tokens_out'] = int(tokens_match.group(2))
    
    # Parse context: "📚 Context: 87k/200k (44%)"
    context_match = re.search(r'Context:\s*(\d+)k/(\d+)k\s*\((\d+)%\)', status_text)
    if context_match:
        data['context_used'] = int(context_match.group(1)) * 1000
        data['context_max'] = int(context_match.group(2)) * 1000
        data['context_pct'] = float(context_match.group(3))
    
    # Parse usage: "📊 Usage: 5h 72% left ⏱3h 19m · Week 18% left"
    hourly_match = re.search(r'(\d+)%\s*left.*?Week\s*(\d+)%\s*left', status_text)
    if hourly_match:
        data['hourly_pct_left'] = float(hourly_match.group(1))
        data['weekly_pct_left'] = float(hourly_match.group(2))
    
    # Parse compactions: "🧹 Compactions: 4"
    compact_match = re.search(r'Compactions:\s*(\d+)', status_text)
    if compact_match:
        data['compactions'] = int(compact_match.group(1))
    
    # Parse model: "🧠 Model: anthropic/claude-opus-4-5"
    model_match = re.search(r'Model:\s*(\S+)', status_text)
    if model_match:
        data['model'] = model_match.group(1)
    
    # Parse session: "🧵 Session: agent:main:main"
    session_match = re.search(r'Session:\s*(\S+)', status_text)
    if session_match:
        data['session_key'] = session_match.group(1)
    
    return data

def store_snapshot(data):
    """Store a token snapshot in the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO token_snapshots 
        (timestamp, tokens_in, tokens_out, context_used, context_max, context_pct,
         hourly_pct_left, weekly_pct_left, compactions, model, session_key, raw_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['timestamp'],
        data['tokens_in'],
        data['tokens_out'],
        data['context_used'],
        data['context_max'],
        data['context_pct'],
        data['hourly_pct_left'],
        data['weekly_pct_left'],
        data['compactions'],
        data['model'],
        data['session_key'],
        data['raw_status']
    ))
    
    # Update daily totals
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute('''
        INSERT INTO daily_totals (date, total_tokens_in, total_tokens_out, total_tokens, peak_context_pct, snapshots_count)
        VALUES (?, ?, ?, ?, ?, 1)
        ON CONFLICT(date) DO UPDATE SET
            total_tokens_in = total_tokens_in + excluded.total_tokens_in,
            total_tokens_out = total_tokens_out + excluded.total_tokens_out,
            total_tokens = total_tokens + excluded.total_tokens_in + excluded.total_tokens_out,
            peak_context_pct = MAX(peak_context_pct, excluded.peak_context_pct),
            snapshots_count = snapshots_count + 1
    ''', (today, data['tokens_in'], data['tokens_out'], data['tokens_in'] + data['tokens_out'], data['context_pct']))
    
    conn.commit()
    conn.close()
    
    print(f"[OK] Snapshot stored: {data['tokens_in']} in / {data['tokens_out']} out, context {data['context_pct']}%")

def get_latest():
    """Get the latest snapshot."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM token_snapshots ORDER BY timestamp DESC LIMIT 1')
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0],
            'timestamp': row[1],
            'tokens_in': row[2],
            'tokens_out': row[3],
            'context_used': row[4],
            'context_max': row[5],
            'context_pct': row[6],
            'hourly_pct_left': row[7],
            'weekly_pct_left': row[8],
            'compactions': row[9],
            'model': row[10],
            'session_key': row[11]
        }
    return None

def get_today_stats():
    """Get today's aggregated stats."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute('SELECT * FROM daily_totals WHERE date = ?', (today,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            'date': row[1],
            'total_tokens_in': row[2],
            'total_tokens_out': row[3],
            'total_tokens': row[4],
            'peak_context_pct': row[5],
            'snapshots_count': row[6],
            'estimated_cost_usd': row[7]
        }
    return None

def get_history(days=7):
    """Get daily totals for the past N days."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT * FROM daily_totals 
        ORDER BY date DESC 
        LIMIT ?
    ''', (days,))
    rows = c.fetchall()
    conn.close()
    
    return [{
        'date': row[1],
        'total_tokens_in': row[2],
        'total_tokens_out': row[3],
        'total_tokens': row[4],
        'peak_context_pct': row[5],
        'snapshots_count': row[6],
        'estimated_cost_usd': row[7]
    } for row in rows]

def main():
    if len(sys.argv) < 2:
        print("Usage: capture.py <command> [args]")
        print("Commands:")
        print("  init              - Initialize database")
        print("  capture <status>  - Capture status text (pipe from session_status)")
        print("  latest            - Show latest snapshot")
        print("  today             - Show today's stats")
        print("  history [days]    - Show daily history")
        print("  json              - Output latest + today as JSON (for API)")
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'init':
        init_db()
    
    elif cmd == 'capture':
        init_db()  # Ensure DB exists
        if len(sys.argv) > 2:
            status_text = ' '.join(sys.argv[2:])
        else:
            status_text = sys.stdin.read()
        
        data = parse_status(status_text)
        store_snapshot(data)
    
    elif cmd == 'latest':
        latest = get_latest()
        if latest:
            print(json.dumps(latest, indent=2))
        else:
            print("No snapshots found")
    
    elif cmd == 'today':
        today = get_today_stats()
        if today:
            print(json.dumps(today, indent=2))
        else:
            print("No data for today")
    
    elif cmd == 'history':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        history = get_history(days)
        print(json.dumps(history, indent=2))
    
    elif cmd == 'json':
        init_db()
        result = {
            'latest': get_latest(),
            'today': get_today_stats(),
            'history': get_history(7)
        }
        print(json.dumps(result))
    
    else:
        print(f"Unknown command: {cmd}")

if __name__ == '__main__':
    main()
