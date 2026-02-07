#!/usr/bin/env python3
"""
Token Usage Sync - Pulls real usage data and syncs to Neon
Uses Clawdbot's session status which has actual Anthropic rate limit info
"""

import subprocess
import json
import re
import psycopg2
from datetime import datetime
import os
from pathlib import Path

def load_database_url():
    """Load DATABASE_URL from secrets file or environment."""
    if os.environ.get('DATABASE_URL'):
        return os.environ['DATABASE_URL']
    secrets_file = Path(__file__).parent.parent / 'secrets' / 'neon_moltfire_dash.env'
    if secrets_file.exists():
        for line in secrets_file.read_text().splitlines():
            if line.startswith('DATABASE_URL='):
                return line.split('=', 1)[1]
    raise ValueError("DATABASE_URL not found in environment or secrets file")

DATABASE_URL = load_database_url()

def parse_usage_from_status(status_text):
    """Parse usage info from clawdbot session status output"""
    data = {
        'tokens_in': 0,
        'tokens_out': 0,
        'context_used': 0,
        'context_max': 200000,
        'hour_remaining_pct': 0,
        'week_remaining_pct': 0,
        'model': 'unknown'
    }
    
    # Parse tokens: "Tokens: 8 in / 207 out"
    tokens_match = re.search(r'Tokens:\s*(\d+)\s*in\s*/\s*(\d+)\s*out', status_text)
    if tokens_match:
        data['tokens_in'] = int(tokens_match.group(1))
        data['tokens_out'] = int(tokens_match.group(2))
    
    # Parse context: "Context: 155k/200k (77%)"
    context_match = re.search(r'Context:\s*([\d.]+)k/([\d.]+)k\s*\((\d+)%\)', status_text)
    if context_match:
        data['context_used'] = int(float(context_match.group(1)) * 1000)
        data['context_max'] = int(float(context_match.group(2)) * 1000)
    
    # Parse usage: "Usage: 5h 91% left"
    hour_match = re.search(r'Usage:.*?(\d+)%\s*left', status_text)
    if hour_match:
        data['hour_remaining_pct'] = int(hour_match.group(1))
    
    # Parse week: "Week 26% left"
    week_match = re.search(r'Week\s*(\d+)%\s*left', status_text)
    if week_match:
        data['week_remaining_pct'] = int(week_match.group(1))
    
    # Parse model: "Model: anthropic/claude-opus-4-5"
    model_match = re.search(r'Model:\s*(\S+)', status_text)
    if model_match:
        data['model'] = model_match.group(1)
    
    return data

def get_current_usage():
    """Get current usage from Clawdbot session_status"""
    # We'll use a simple approach - read from a temp file or direct call
    # For now, return estimated based on context
    return None

def sync_to_neon(data):
    """Sync usage data to Neon database"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Create table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS token_usage_realtime (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT NOW(),
            date DATE DEFAULT CURRENT_DATE,
            hour_remaining_pct INT,
            week_remaining_pct INT,
            context_used INT,
            context_max INT,
            model VARCHAR(100),
            tokens_in INT,
            tokens_out INT
        )
    """)
    
    # Insert new record
    cur.execute("""
        INSERT INTO token_usage_realtime 
        (hour_remaining_pct, week_remaining_pct, context_used, context_max, model, tokens_in, tokens_out)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        data['hour_remaining_pct'],
        data['week_remaining_pct'],
        data['context_used'],
        data['context_max'],
        data['model'],
        data['tokens_in'],
        data['tokens_out']
    ))
    
    conn.commit()
    cur.close()
    conn.close()
    print(f"Synced: {data['hour_remaining_pct']}% hour left, {data['week_remaining_pct']}% week left")

def update_dashboard_view():
    """Update the token_usage table with latest realtime data for dashboard"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Get latest realtime data
    cur.execute("""
        SELECT hour_remaining_pct, week_remaining_pct, context_used, model
        FROM token_usage_realtime 
        ORDER BY timestamp DESC LIMIT 1
    """)
    row = cur.fetchone()
    
    if row:
        hour_pct, week_pct, context, model = row
        # Calculate "used" as inverse of remaining
        hour_used = 100 - hour_pct
        week_used = 100 - week_pct
        
        # Clear old seeded data and insert real data
        today = datetime.now().date().isoformat()
        
        cur.execute("DELETE FROM token_usage WHERE timestamp::date = %s", (today,))
        cur.execute("""
            INSERT INTO token_usage (timestamp, model, tokens_in, tokens_out, operation, session_id, cost_estimate)
            VALUES (NOW(), %s, %s, %s, %s, %s, %s)
        """, (
            model,
            context,  # Use context as proxy for input
            0,
            f"Rate limit: {hour_pct}% hour, {week_pct}% week remaining",
            'realtime',
            0
        ))
        
        conn.commit()
        print(f"Dashboard updated: {hour_used}% hour used, {week_used}% week used")
    
    cur.close()
    conn.close()

def manual_update(hour_pct, week_pct, context_used=155000, model='anthropic/claude-opus-4-5'):
    """Manually update with known values"""
    data = {
        'hour_remaining_pct': hour_pct,
        'week_remaining_pct': week_pct,
        'context_used': context_used,
        'context_max': 200000,
        'model': model,
        'tokens_in': 0,
        'tokens_out': 0
    }
    sync_to_neon(data)
    update_dashboard_view()

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        # Manual mode: python token-sync.py <hour_pct> <week_pct>
        hour_pct = int(sys.argv[1])
        week_pct = int(sys.argv[2])
        manual_update(hour_pct, week_pct)
    else:
        print("Usage: python token-sync.py <hour_remaining_pct> <week_remaining_pct>")
        print("Example: python token-sync.py 91 26")
        print("\nThis will sync real rate limit data to the dashboard.")
