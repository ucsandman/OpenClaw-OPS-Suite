"""
Sync local SQLite data to Neon Postgres
Run this periodically to keep the cloud dashboard in sync
"""

import sqlite3
import psycopg2
from psycopg2 import sql as pgsql
from datetime import datetime
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
    raise ValueError("DATABASE_URL not found in environment or secrets file")

DATABASE_URL = load_database_url()

# Mapping of local SQLite DBs to tables
SYNC_CONFIG = {
    'tools/learning-database/data/learning.db': {
        'decisions': 'decisions',
        'lessons': 'lessons',
        'patterns': 'patterns',
        'outcomes': 'outcomes'
    },
    'tools/inspiration/data/ideas.db': {
        'ideas': 'ideas',
        'idea_updates': 'idea_updates'
    },
    'tools/goal-tracker/data/goals.db': {
        'goals': 'goals',
        'milestones': 'milestones',
        'goal_updates': 'goal_updates'
    },
    'tools/relationship-tracker/relationships.db': {
        'contacts': 'contacts',
        'interactions': 'interactions'
    },
    'tools/workflow-orchestrator/data/workflows.db': {
        'workflows': 'workflows',
        'executions': 'executions',
        'scheduled_jobs': 'scheduled_jobs'
    },
    'tools/token-capture/data/tokens.db': {
        'token_snapshots': 'token_snapshots',
        'daily_totals': 'daily_totals'
    },
    'tools/memory-health/data/memory_health.db': {
        'health_snapshots': 'health_snapshots',
        'entities': 'entities',
        'topics': 'topics'
    }
}

def get_sqlite_data(db_path, table):
    """Get data from a SQLite table (limited to prevent massive transactions)"""
    if not os.path.exists(db_path):
        print(f"  [SKIP] {db_path} not found")
        return [], []
    
    # SECURITY: Validate table name against allowlist
    valid_tables = set()
    for tables in SYNC_CONFIG.values():
        valid_tables.update(tables.keys())
    
    if table not in valid_tables:
        print(f"  [ERROR] Invalid table name: {table}")
        return [], []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Limit to recent data to prevent massive transactions
        # For tables with timestamps, get last 1000 rows
        # For others, get all but warn if large
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        total_rows = cursor.fetchone()[0]
        
        if total_rows > 1000:
            print(f"  [INFO] {table} has {total_rows} rows, limiting to recent 1000")
            # Try timestamp-based limit first
            try:
                cursor.execute(f"SELECT * FROM {table} ORDER BY timestamp DESC LIMIT 1000")
            except:
                # Fallback to rowid limit
                cursor.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 1000")
        else:
            cursor.execute(f"SELECT * FROM {table}")
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        data = [dict(row) for row in rows]
        conn.close()
        return columns, data
    except Exception as e:
        print(f"  [ERROR] Reading {table}: {e}")
        conn.close()
        return [], []

def sync_table(pg_cursor, table_name, columns, data):
    """Sync data to Postgres table (upsert by id)"""
    if not data:
        print(f"  [SKIP] {table_name}: no data")
        return 0
    
    # SECURITY: Validate table name against allowlist
    valid_tables = set()
    for tables in SYNC_CONFIG.values():
        valid_tables.update(tables.values())
    
    if table_name not in valid_tables:
        print(f"  [ERROR] Invalid table name: {table_name}")
        return 0
    
    # SECURITY: Use psycopg2.sql for safe identifier formatting
    table_id = pgsql.Identifier(table_name)
    col_ids = [pgsql.Identifier(c) for c in columns]
    
    print(f"  [INFO] Syncing {len(data)} rows to {table_name}...")
    
    # Clear existing data and insert fresh
    pg_cursor.execute(pgsql.SQL("DELETE FROM {}").format(table_id))
    
    # Build insert statement with safe identifiers
    insert_query = pgsql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        table_id,
        pgsql.SQL(', ').join(col_ids),
        pgsql.SQL(', ').join([pgsql.Placeholder()] * len(columns))
    )
    
    inserted = 0
    for i, row in enumerate(data):
        values = [row.get(col) for col in columns]
        try:
            pg_cursor.execute(insert_query, values)
            inserted += 1
            # Progress indicator for large tables
            if (i + 1) % 100 == 0:
                print(f"    Progress: {i + 1}/{len(data)}")
        except Exception as e:
            print(f"  [ERROR] Row {i + 1} in {table_name}: {e}")
            # Continue with other rows instead of stopping
    
    return inserted

def test_connection():
    """Test Neon connection quickly"""
    print("Testing Neon connection...")
    try:
        pg_conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
        pg_cursor = pg_conn.cursor()
        pg_cursor.execute("SELECT 1")
        result = pg_cursor.fetchone()
        pg_cursor.close()
        pg_conn.close()
        print("[OK] Connection test successful")
        return True
    except Exception as e:
        print(f"[FAIL] Connection test failed: {e}")
        return False

def main():
    print(f"=== Neon Sync Started: {datetime.now().isoformat()} ===\n")
    
    # Test connection first
    if not test_connection():
        print("[ABORT] Cannot connect to Neon")
        return

    # Connect to Neon with aggressive timeouts
    try:
        print("[INFO] Connecting to Neon...")
        pg_conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        # SECURITY: Disable autocommit - use explicit transactions for atomicity
        pg_conn.autocommit = False
        pg_cursor = pg_conn.cursor()
        # Set aggressive timeouts to prevent hangs
        pg_cursor.execute("SET statement_timeout = '30s'")
        pg_cursor.execute("SET idle_in_transaction_session_timeout = '30s'")
        print("[OK] Connected to Neon\n")
    except Exception as e:
        print(f"[FAIL] Neon connection failed: {e}")
        return

    total_synced = 0
    sync_success = True
    error_msg = None

    try:
        for db_path, tables in SYNC_CONFIG.items():
            print(f"Syncing {db_path}...")

            for sqlite_table, pg_table in tables.items():
                columns, data = get_sqlite_data(db_path, sqlite_table)
                if columns and data:
                    count = sync_table(pg_cursor, pg_table, columns, data)
                    total_synced += count
                    print(f"  [OK] {pg_table}: {count} rows")
                elif columns and not data:
                    print(f"  [OK] {pg_table}: 0 rows (empty)")

        # Log the sync
        pg_cursor.execute("""
            INSERT INTO sync_log (table_name, records_synced, status)
            VALUES ('full_sync', %s, 'success')
        """, (total_synced,))

        # COMMIT the transaction only if all operations succeed
        pg_conn.commit()
        print(f"\n=== Sync Complete: {total_synced} total rows synced ===")

    except Exception as e:
        # ROLLBACK on any error - prevents partial/inconsistent state
        sync_success = False
        error_msg = str(e)
        print(f"\n[FAIL] Sync error: {e}")
        print("[ROLLBACK] Rolling back all changes...")
        try:
            pg_conn.rollback()
            # Log the failed sync
            pg_conn.autocommit = True  # Allow logging even after rollback
            pg_cursor.execute("""
                INSERT INTO sync_log (table_name, records_synced, status, error)
                VALUES ('full_sync', %s, 'failed', %s)
            """, (total_synced, error_msg))
        except Exception as log_err:
            print(f"[WARN] Could not log failure: {log_err}")
        print("[ROLLBACK] Complete - no data was modified")

    finally:
        pg_cursor.close()
        pg_conn.close()

if __name__ == '__main__':
    main()
