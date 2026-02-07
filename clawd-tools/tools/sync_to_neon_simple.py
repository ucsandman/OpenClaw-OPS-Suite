#!/usr/bin/env python3
"""
Simple, working Neon sync script
Based on successful test_simple_sync.py
"""

import sqlite3
import psycopg2
import os
from pathlib import Path
from datetime import datetime

def load_database_url():
    secrets_file = Path(__file__).parent.parent / 'secrets' / 'neon_moltfire_dash.env'
    for line in secrets_file.read_text().splitlines():
        if line.startswith('DATABASE_URL='):
            return line.split('=', 1)[1]

# Tables that we know work
SIMPLE_SYNC_CONFIG = {
    'tools/token-capture/data/tokens.db': ['token_snapshots'],
    'tools/goal-tracker/data/goals.db': ['goals'],
    'tools/relationship-tracker/relationships.db': ['contacts', 'interactions'],
}

def sync_single_table(database_url, sqlite_path, table_name):
    """Sync one table safely"""
    if not Path(sqlite_path).exists():
        print(f"  [SKIP] {sqlite_path} not found")
        return 0
    
    try:
        # Get SQLite data
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        # Limit data to prevent huge transactions
        sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_count = sqlite_cursor.fetchone()[0]
        
        if total_count > 500:
            print(f"  [INFO] {table_name} has {total_count} rows, limiting to recent 500")
            try:
                sqlite_cursor.execute(f"SELECT * FROM {table_name} ORDER BY timestamp DESC LIMIT 500")
            except:
                sqlite_cursor.execute(f"SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT 500")
        else:
            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        
        rows = sqlite_cursor.fetchall()
        if not rows:
            sqlite_conn.close()
            print(f"  [OK] {table_name}: 0 rows")
            return 0
        
        columns = [desc[0] for desc in sqlite_cursor.description]
        data = [dict(row) for row in rows]
        sqlite_conn.close()
        
        # Sync to Neon
        pg_conn = psycopg2.connect(database_url, connect_timeout=10)
        pg_conn.autocommit = False
        pg_cursor = pg_conn.cursor()
        
        # Clear and insert
        pg_cursor.execute(f"DELETE FROM {table_name}")
        
        placeholders = ', '.join(['%s'] * len(columns))
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        for row in data:
            values = [row.get(col) for col in columns]
            pg_cursor.execute(query, values)
        
        pg_conn.commit()
        pg_cursor.close()
        pg_conn.close()
        
        print(f"  [OK] {table_name}: {len(data)} rows synced")
        return len(data)
        
    except Exception as e:
        print(f"  [ERROR] {table_name}: {e}")
        return 0

def main():
    print(f"=== Simple Neon Sync Started: {datetime.now().strftime('%H:%M:%S')} ===")
    
    database_url = load_database_url()
    total_synced = 0
    
    for sqlite_path, tables in SIMPLE_SYNC_CONFIG.items():
        print(f"Syncing {sqlite_path}...")
        for table in tables:
            count = sync_single_table(database_url, sqlite_path, table)
            total_synced += count
    
    print(f"\n=== Sync Complete: {total_synced} total rows synced ===")

if __name__ == '__main__':
    main()