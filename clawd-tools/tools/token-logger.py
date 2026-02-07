"""
Real Token Usage Logger
Logs actual token usage to Neon for dashboard tracking
"""

import psycopg2
from datetime import datetime
import sys
import os
from pathlib import Path

def load_database_url():
    """Load DATABASE_URL from secrets file or environment."""
    # Try environment variable first
    if os.environ.get('DATABASE_URL'):
        return os.environ['DATABASE_URL']
    # Try secrets file
    secrets_file = Path(__file__).parent.parent / 'secrets' / 'neon_moltfire_dash.env'
    if secrets_file.exists():
        for line in secrets_file.read_text().splitlines():
            if line.startswith('DATABASE_URL='):
                return line.split('=', 1)[1]
    raise ValueError("DATABASE_URL not found in environment or secrets file. "
                     "Set DATABASE_URL env var or create secrets/neon_moltfire_dash.env")

DATABASE_URL = load_database_url()

def log_tokens(operation, tokens_in=0, tokens_out=0, model="unknown", session_id="main", cost_estimate=0.0):
    """
    Log token usage to Neon database
    
    Args:
        operation (str): Description of what operation used tokens
        tokens_in (int): Input tokens used
        tokens_out (int): Output tokens generated
        model (str): Model used (opus, sonnet, haiku)
        session_id (str): Session identifier
        cost_estimate (float): Estimated cost in USD
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO token_usage (timestamp, operation, tokens_in, tokens_out, model, session_id, cost_estimate)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (timestamp, operation, tokens_in, tokens_out, model, session_id, cost_estimate))
        
        total_tokens = tokens_in + tokens_out
        print(f"[LOGGED] {operation}: {total_tokens:,} tokens ({model}) - ${cost_estimate:.3f}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to log tokens: {e}")
        return False

def estimate_cost(tokens_in, tokens_out, model="opus"):
    """
    Estimate cost based on token usage and model
    Rough estimates per 1k tokens:
    - Opus: $15 input, $75 output
    - Sonnet: $3 input, $15 output  
    - Haiku: $0.25 input, $1.25 output
    """
    rates = {
        "opus": {"input": 0.015, "output": 0.075},
        "sonnet": {"input": 0.003, "output": 0.015},
        "haiku": {"input": 0.00025, "output": 0.00125}
    }
    
    if model not in rates:
        model = "opus"  # Default to most expensive
    
    cost = (tokens_in / 1000) * rates[model]["input"] + (tokens_out / 1000) * rates[model]["output"]
    return cost

def log_operation(operation, tokens_in, tokens_out, model="opus"):
    """Convenience function with cost calculation"""
    cost = estimate_cost(tokens_in, tokens_out, model)
    return log_tokens(operation, tokens_in, tokens_out, model, cost_estimate=cost)

def get_daily_usage():
    """Get today's token usage"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        today = datetime.now().date().isoformat()
        
        cursor.execute("""
            SELECT 
                SUM(tokens_in) as total_in,
                SUM(tokens_out) as total_out,
                SUM(cost_estimate) as total_cost,
                COUNT(*) as operations
            FROM token_usage 
            WHERE timestamp::date = %s
        """, (today,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return {
            "tokens_in": result[0] or 0,
            "tokens_out": result[1] or 0,
            "total_cost": result[2] or 0.0,
            "operations": result[3] or 0
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to get daily usage: {e}")
        return {"tokens_in": 0, "tokens_out": 0, "total_cost": 0.0, "operations": 0}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python token-logger.py log 'operation' tokens_in tokens_out [model]")
        print("  python token-logger.py status")
        print("  python token-logger.py test")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "log":
        if len(sys.argv) < 5:
            print("Usage: python token-logger.py log 'operation' tokens_in tokens_out [model]")
            sys.exit(1)
        
        operation = sys.argv[2]
        tokens_in = int(sys.argv[3])
        tokens_out = int(sys.argv[4])
        model = sys.argv[5] if len(sys.argv) > 5 else "opus"
        
        log_operation(operation, tokens_in, tokens_out, model)
    
    elif action == "status":
        usage = get_daily_usage()
        total = usage["tokens_in"] + usage["tokens_out"]
        print(f"Today's Usage: {total:,} tokens (${usage['total_cost']:.2f}) - {usage['operations']} operations")
        
        budget = 18000
        pct = (total / budget) * 100 if budget > 0 else 0
        print(f"Budget: {pct:.1f}% of {budget:,} daily limit")
        
        if pct > 75:
            print("[!] WARNING: High token usage!")
        elif pct > 100:
            print("[!!] CRITICAL: Over budget!")
    
    elif action == "test":
        print("Testing token logger...")
        success = log_operation("Test operation", 1000, 500, "sonnet")
        if success:
            print("[OK] Token logging is working!")
        else:
            print("[FAIL] Token logging failed!")