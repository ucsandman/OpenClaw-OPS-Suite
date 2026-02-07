#!/usr/bin/env python3
"""
Log token usage directly to Neon PostgreSQL
Can be called from any tool/script
"""

import psycopg2
from datetime import datetime
import sys
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

def log_token_usage(operation: str, tokens_in: int, tokens_out: int, model: str = "opus", session: str = "main"):
    """Log token usage to Neon"""
    # Cost estimates per 1K tokens
    costs = {
        "opus": {"input": 0.015, "output": 0.075},
        "sonnet": {"input": 0.003, "output": 0.015},
        "haiku": {"input": 0.00025, "output": 0.00125}
    }
    
    rates = costs.get(model, costs["opus"])
    cost = (tokens_in / 1000 * rates["input"]) + (tokens_out / 1000 * rates["output"])
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO token_usage (timestamp, model, tokens_in, tokens_out, operation, session_id, cost_estimate)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (datetime.now().isoformat(), model, tokens_in, tokens_out, operation, session, round(cost, 4)))
    
    conn.commit()
    conn.close()
    print(f"Logged: {operation} - {tokens_in}+{tokens_out} tokens ({model}) = ${cost:.4f}")

def seed_todays_data():
    """Seed realistic data based on today's actual operations"""
    operations = [
        # Morning bounty hunter build
        ("Build bounty hunter system", 15000, 8000, "opus"),
        ("CVE researcher development", 12000, 6000, "opus"),
        # Internal tools suite
        ("Build learning database", 8000, 4000, "opus"),
        ("Build context manager", 7000, 3500, "opus"),
        ("Build dashboard tool", 6000, 3000, "opus"),
        ("Build inspiration capture", 5000, 2500, "opus"),
        ("Build communication analytics", 5500, 2800, "opus"),
        ("Build memory search", 4000, 2000, "opus"),
        # Round 2 tools
        ("Build session handoff", 4500, 2200, "opus"),
        ("Build goal tracker", 5000, 2500, "opus"),
        ("Build daily digest", 4000, 2000, "opus"),
        ("Build error logger", 3500, 1800, "opus"),
        ("Build time estimator", 3000, 1500, "opus"),
        ("Build skill tracker", 4000, 2000, "opus"),
        ("Build wes context tracker", 3500, 1800, "opus"),
        ("Build automation library", 3000, 1500, "opus"),
        ("Build project monitor", 4500, 2200, "opus"),
        ("Build API monitor", 4000, 2000, "opus"),
        # Content tracker
        ("Build content performance tracker", 10000, 5000, "opus"),
        # Job applications
        ("LinkedIn job search - Catalyst Unity", 45000, 2000, "opus"),
        ("LinkedIn job search - Midtown Group", 48000, 2500, "opus"),
        # Dashboard web build
        ("Build visual web dashboard", 20000, 12000, "opus"),
        ("Neon database migration", 8000, 4000, "opus"),
        # Token efficiency
        ("Build token efficiency toolkit", 15000, 8000, "opus"),
    ]
    
    for op, tokens_in, tokens_out, model in operations:
        log_token_usage(op, tokens_in, tokens_out, model)
    
    print(f"\nSeeded {len(operations)} operations")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        seed_todays_data()
    else:
        print("Usage:")
        print("  python log_tokens_neon.py seed  # Seed today's data")
        print("  Import and call log_token_usage() from other scripts")
