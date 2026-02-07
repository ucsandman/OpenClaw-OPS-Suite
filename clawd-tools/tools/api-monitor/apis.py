#!/usr/bin/env python3
"""
AgentForge API/Service Monitor
Track external services, rate limits, costs, reliability.

Usage:
    python apis.py add "service name" --endpoint "url" --limit "100/day"
    python apis.py use "service" --calls 1 --cost 0.01
    python apis.py status
    python apis.py costs [--period day|week|month]
"""

import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "apis.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        endpoint TEXT,
        rate_limit TEXT,
        cost_per_call REAL DEFAULT 0,
        notes TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        calls INTEGER DEFAULT 1,
        cost REAL DEFAULT 0,
        success INTEGER DEFAULT 1,
        notes TEXT,
        FOREIGN KEY (service_id) REFERENCES services(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        incident_type TEXT,
        description TEXT,
        resolved INTEGER DEFAULT 0,
        FOREIGN KEY (service_id) REFERENCES services(id)
    )''')
    
    conn.commit()
    conn.close()

def add_service(name, endpoint=None, rate_limit=None, cost_per_call=0):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        c.execute('''INSERT INTO services (name, endpoint, rate_limit, cost_per_call)
                     VALUES (?, ?, ?, ?)''',
                  (name, endpoint, rate_limit, cost_per_call))
        print(f"[+] Service added: {name}")
        if rate_limit:
            print(f"    Rate limit: {rate_limit}")
        if cost_per_call > 0:
            print(f"    Cost: ${cost_per_call}/call")
    except sqlite3.IntegrityError:
        print(f"Service '{name}' already exists.")
    
    conn.commit()
    conn.close()

def log_usage(name, calls=1, cost=0, success=True, notes=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT id, cost_per_call FROM services WHERE name LIKE ?', (f'%{name}%',))
    service = c.fetchone()
    
    if not service:
        # Auto-create service
        c.execute('INSERT INTO services (name) VALUES (?)', (name,))
        service_id = c.lastrowid
        print(f"[+] Auto-created service: {name}")
    else:
        service_id = service[0]
        if cost == 0 and service[1]:
            cost = service[1] * calls
    
    c.execute('''INSERT INTO usage (service_id, timestamp, calls, cost, success, notes)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (service_id, datetime.now().isoformat(), calls, cost, 1 if success else 0, notes))
    
    conn.commit()
    conn.close()
    
    cost_str = f" (${cost:.4f})" if cost > 0 else ""
    status = "[OK]" if success else "[X]"
    print(f"{status} {name}: {calls} call(s){cost_str}")

def show_status():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print(f"\n{'='*60}")
    print("API/SERVICE STATUS")
    print(f"{'='*60}")
    
    # Get all services with usage stats
    c.execute('''SELECT s.name, s.rate_limit, s.cost_per_call,
                        COUNT(u.id) as total_calls,
                        SUM(u.cost) as total_cost,
                        SUM(CASE WHEN u.success = 0 THEN 1 ELSE 0 END) as failures
                 FROM services s
                 LEFT JOIN usage u ON s.id = u.service_id
                 GROUP BY s.id
                 ORDER BY total_calls DESC''')
    
    services = c.fetchall()
    
    if not services:
        print("No services tracked yet.")
        conn.close()
        return
    
    for s in services:
        calls = s[3] or 0
        cost = s[4] or 0
        failures = s[5] or 0
        reliability = 100 * (calls - failures) / calls if calls > 0 else 100
        
        status = "[OK]" if reliability >= 95 else "[!]" if reliability >= 80 else "[X]"
        
        print(f"\n  {status} {s[0]}")
        print(f"      Calls: {calls} | Cost: ${cost:.2f} | Reliability: {reliability:.0f}%")
        if s[1]:
            print(f"      Rate limit: {s[1]}")
    
    # Today's usage
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute('''SELECT SUM(calls), SUM(cost) FROM usage WHERE timestamp LIKE ?''', (f'{today}%',))
    today_stats = c.fetchone()
    
    if today_stats[0]:
        print(f"\n[TODAY]")
        print(f"  Calls: {today_stats[0]} | Cost: ${today_stats[1]:.4f}")
    
    conn.close()

def show_costs(period='day'):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if period == 'day':
        cutoff = datetime.now() - timedelta(days=1)
        period_name = "Last 24 Hours"
    elif period == 'week':
        cutoff = datetime.now() - timedelta(days=7)
        period_name = "Last 7 Days"
    else:
        cutoff = datetime.now() - timedelta(days=30)
        period_name = "Last 30 Days"
    
    c.execute('''SELECT s.name, SUM(u.calls), SUM(u.cost)
                 FROM services s
                 JOIN usage u ON s.id = u.service_id
                 WHERE u.timestamp > ?
                 GROUP BY s.id
                 ORDER BY SUM(u.cost) DESC''', (cutoff.isoformat(),))
    
    costs = c.fetchall()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"API COSTS - {period_name}")
    print(f"{'='*60}")
    
    if not costs:
        print("No usage in this period.")
        return
    
    total_cost = 0
    for cost in costs:
        total_cost += cost[2] or 0
        print(f"\n  {cost[0]}")
        print(f"      Calls: {cost[1]} | Cost: ${cost[2]:.4f}")
    
    print(f"\n{'='*40}")
    print(f"  TOTAL: ${total_cost:.4f}")

def log_incident(name, incident_type, description):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT id FROM services WHERE name LIKE ?', (f'%{name}%',))
    service = c.fetchone()
    
    if not service:
        print(f"Service '{name}' not found.")
        conn.close()
        return
    
    c.execute('''INSERT INTO incidents (service_id, timestamp, incident_type, description)
                 VALUES (?, ?, ?, ?)''',
              (service[0], datetime.now().isoformat(), incident_type, description))
    
    conn.commit()
    conn.close()
    
    print(f"[!] Incident logged for {name}: {incident_type}")

def main():
    parser = argparse.ArgumentParser(description='API/Service Monitor')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add
    add_parser = subparsers.add_parser('add', help='Add service')
    add_parser.add_argument('name')
    add_parser.add_argument('--endpoint', '-e')
    add_parser.add_argument('--limit', '-l', help='Rate limit (e.g., 100/day)')
    add_parser.add_argument('--cost', '-c', type=float, default=0)
    
    # Use
    use_parser = subparsers.add_parser('use', help='Log API usage')
    use_parser.add_argument('name')
    use_parser.add_argument('--calls', '-n', type=int, default=1)
    use_parser.add_argument('--cost', '-c', type=float, default=0)
    use_parser.add_argument('--fail', '-f', action='store_true')
    use_parser.add_argument('--notes')
    
    # Status
    subparsers.add_parser('status', help='Show status')
    
    # Costs
    costs_parser = subparsers.add_parser('costs', help='Show costs')
    costs_parser.add_argument('--period', '-p', choices=['day', 'week', 'month'], default='day')
    
    # Incident
    incident_parser = subparsers.add_parser('incident', help='Log incident')
    incident_parser.add_argument('name')
    incident_parser.add_argument('--type', '-t', required=True)
    incident_parser.add_argument('--desc', '-d', required=True)
    
    # Init
    subparsers.add_parser('init', help='Initialize database')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_db()
        print("API monitor database initialized.")
    elif args.command == 'add':
        add_service(args.name, args.endpoint, args.limit, args.cost)
    elif args.command == 'use':
        log_usage(args.name, args.calls, args.cost, not args.fail, args.notes)
    elif args.command == 'status':
        show_status()
    elif args.command == 'costs':
        show_costs(args.period)
    elif args.command == 'incident':
        log_incident(args.name, args.type, args.desc)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
