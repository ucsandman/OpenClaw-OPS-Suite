#!/usr/bin/env python3
"""
Secret Rotation Tracker - Track API keys, tokens, credentials and remind to rotate.
"""

import sys
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import argparse

# Fix Windows Unicode encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = Path(__file__).parent / "secrets_tracker.db"

# Default rotation policies (days)
ROTATION_POLICIES = {
    'api_key': 90,
    'oauth_token': 365,
    'password': 90,
    'ssh_key': 365,
    'database_url': 180,
    'webhook_secret': 90,
    'encryption_key': 365,
    'other': 90
}

def init_db():
    """Initialize database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS secrets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            secret_type TEXT NOT NULL,
            service TEXT,
            location TEXT,
            created_date TEXT,
            last_rotated TEXT,
            rotation_days INTEGER,
            notes TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS rotation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            secret_id INTEGER,
            rotated_date TEXT,
            notes TEXT,
            FOREIGN KEY (secret_id) REFERENCES secrets(id)
        )
    ''')
    conn.commit()
    conn.close()

def add_secret(name: str, secret_type: str, service: str = None, location: str = None,
               created_date: str = None, rotation_days: int = None, notes: str = None):
    """Add a secret to track."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if rotation_days is None:
        rotation_days = ROTATION_POLICIES.get(secret_type, 90)
    
    if created_date is None:
        created_date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        c.execute('''
            INSERT INTO secrets (name, secret_type, service, location, created_date, 
                                last_rotated, rotation_days, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, secret_type, service, location, created_date, created_date, rotation_days, notes))
        conn.commit()
        print(f"[OK] Added secret: {name} ({secret_type}) - rotate every {rotation_days} days")
    except sqlite3.IntegrityError:
        print(f"[X] Secret '{name}' already exists. Use 'update' to modify.")
    finally:
        conn.close()

def rotate_secret(name: str, notes: str = None):
    """Mark a secret as rotated."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT id FROM secrets WHERE name = ?', (name,))
    row = c.fetchone()
    
    if not row:
        print(f"[X] Secret '{name}' not found")
        conn.close()
        return
    
    secret_id = row[0]
    now = datetime.now().strftime('%Y-%m-%d')
    
    c.execute('UPDATE secrets SET last_rotated = ? WHERE id = ?', (now, secret_id))
    c.execute('INSERT INTO rotation_history (secret_id, rotated_date, notes) VALUES (?, ?, ?)',
              (secret_id, now, notes))
    
    conn.commit()
    conn.close()
    print(f"[OK] Rotated: {name} on {now}")

def check_due(days_warning: int = 14):
    """Check which secrets are due for rotation."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT name, secret_type, service, last_rotated, rotation_days
        FROM secrets WHERE is_active = 1
    ''')
    
    overdue = []
    upcoming = []
    healthy = []
    
    for row in c.fetchall():
        name, secret_type, service, last_rotated, rotation_days = row
        
        if last_rotated:
            last_date = datetime.strptime(last_rotated, '%Y-%m-%d')
            due_date = last_date + timedelta(days=rotation_days)
            days_until = (due_date - datetime.now()).days
            
            info = {
                'name': name,
                'type': secret_type,
                'service': service,
                'last_rotated': last_rotated,
                'due_date': due_date.strftime('%Y-%m-%d'),
                'days_until': days_until
            }
            
            if days_until < 0:
                overdue.append(info)
            elif days_until <= days_warning:
                upcoming.append(info)
            else:
                healthy.append(info)
    
    conn.close()
    
    return {
        'overdue': sorted(overdue, key=lambda x: x['days_until']),
        'upcoming': sorted(upcoming, key=lambda x: x['days_until']),
        'healthy': sorted(healthy, key=lambda x: x['days_until'])
    }

def list_secrets(show_all: bool = False):
    """List all tracked secrets."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if show_all:
        c.execute('SELECT name, secret_type, service, location, last_rotated, rotation_days, is_active FROM secrets')
    else:
        c.execute('SELECT name, secret_type, service, location, last_rotated, rotation_days, is_active FROM secrets WHERE is_active = 1')
    
    rows = c.fetchall()
    conn.close()
    return rows

def deactivate_secret(name: str):
    """Mark a secret as inactive (no longer in use)."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE secrets SET is_active = 0 WHERE name = ?', (name,))
    conn.commit()
    conn.close()
    print(f"[OK] Deactivated: {name}")

def get_rotation_history(name: str):
    """Get rotation history for a secret."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT rh.rotated_date, rh.notes 
        FROM rotation_history rh
        JOIN secrets s ON s.id = rh.secret_id
        WHERE s.name = ?
        ORDER BY rh.rotated_date DESC
    ''', (name,))
    
    rows = c.fetchall()
    conn.close()
    return rows

def main():
    parser = argparse.ArgumentParser(description='Secret Rotation Tracker')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a secret to track')
    add_parser.add_argument('name', help='Secret name/identifier')
    add_parser.add_argument('--type', '-t', required=True, 
                           choices=['api_key', 'oauth_token', 'password', 'ssh_key', 
                                   'database_url', 'webhook_secret', 'encryption_key', 'other'])
    add_parser.add_argument('--service', '-s', help='Service name (e.g., OpenAI, GitHub)')
    add_parser.add_argument('--location', '-l', help='Where the secret is stored')
    add_parser.add_argument('--created', '-c', help='Created date (YYYY-MM-DD)')
    add_parser.add_argument('--days', '-d', type=int, help='Rotation period in days')
    add_parser.add_argument('--notes', '-n', help='Notes')
    
    # Rotate command
    rotate_parser = subparsers.add_parser('rotate', help='Mark a secret as rotated')
    rotate_parser.add_argument('name', help='Secret name')
    rotate_parser.add_argument('--notes', '-n', help='Rotation notes')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check rotation status')
    check_parser.add_argument('--warning', '-w', type=int, default=14, help='Warning threshold (days)')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List tracked secrets')
    list_parser.add_argument('--all', '-a', action='store_true', help='Include inactive')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show rotation history')
    history_parser.add_argument('name', help='Secret name')
    
    # Deactivate command
    deact_parser = subparsers.add_parser('deactivate', help='Mark secret as inactive')
    deact_parser.add_argument('name', help='Secret name')
    
    args = parser.parse_args()
    
    if args.command == 'add':
        add_secret(
            args.name,
            args.type,
            service=args.service,
            location=args.location,
            created_date=args.created,
            rotation_days=args.days,
            notes=args.notes
        )
    
    elif args.command == 'rotate':
        rotate_secret(args.name, args.notes)
    
    elif args.command == 'check':
        status = check_due(args.warning)
        
        if status['overdue']:
            print("\n[!!] OVERDUE:")
            for s in status['overdue']:
                print(f"   {s['name']} ({s['service'] or s['type']}) - {abs(s['days_until'])} days overdue!")
        
        if status['upcoming']:
            print(f"\n[!]  Due within {args.warning} days:")
            for s in status['upcoming']:
                print(f"   {s['name']} ({s['service'] or s['type']}) - {s['days_until']} days")
        
        if not status['overdue'] and not status['upcoming']:
            print("\n[OK] All secrets are healthy!")
        
        print(f"\n[#] Summary: {len(status['overdue'])} overdue, {len(status['upcoming'])} upcoming, {len(status['healthy'])} healthy")
    
    elif args.command == 'list':
        secrets = list_secrets(args.all)
        if not secrets:
            print("No secrets tracked yet. Use 'add' to start tracking.")
            return
        
        print(f"\n{'Name':<25} {'Type':<15} {'Service':<15} {'Last Rotated':<12} {'Days':<5}")
        print("-" * 75)
        for s in secrets:
            name, stype, service, location, last_rot, days, active = s
            status = "" if active else " (inactive)"
            print(f"{name:<25} {stype:<15} {(service or '-'):<15} {(last_rot or '-'):<12} {days:<5}{status}")
    
    elif args.command == 'history':
        history = get_rotation_history(args.name)
        if not history:
            print(f"No rotation history for '{args.name}'")
            return
        
        print(f"\nRotation history for '{args.name}':")
        for date, notes in history:
            print(f"  {date}: {notes or '(no notes)'}")
    
    elif args.command == 'deactivate':
        deactivate_secret(args.name)
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
