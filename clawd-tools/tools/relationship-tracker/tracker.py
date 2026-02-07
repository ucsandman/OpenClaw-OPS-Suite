#!/usr/bin/env python3
"""
Relationship Tracker - AgentForge's Mini-CRM
Track contacts, interactions, and follow-ups across platforms.

Usage:
    python tracker.py add <name> --platform moltbook --handle @user
    python tracker.py list [--hot] [--due] [--platform moltbook]
    python tracker.py log <contact_id> --type comment --summary "Discussed bounties"
    python tracker.py followup <contact_id> --date 2026-02-10
    python tracker.py view <contact_id>
    python tracker.py search <query>
    python tracker.py due  # Show contacts needing follow-up
"""

import sqlite3
import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "relationships.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

def get_db():
    """Get database connection, creating if needed."""
    db_exists = DB_PATH.exists()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    if not db_exists:
        with open(SCHEMA_PATH) as f:
            conn.executescript(f.read())
        print(f"[OK] Created database at {DB_PATH}")
    
    return conn

def add_contact(args):
    """Add a new contact."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO contacts (name, platform, handle, platform_id, temperature, 
                            opportunity_type, notes, first_contact, last_contact)
        VALUES (?, ?, ?, ?, ?, ?, ?, date('now'), date('now'))
    """, (args.name, args.platform, args.handle, args.platform_id,
          args.temperature, args.opportunity, args.notes))
    
    contact_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"[OK] Added contact #{contact_id}: {args.name} ({args.platform})")
    return contact_id

def list_contacts(args):
    """List contacts with optional filters."""
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM contacts WHERE 1=1"
    params = []
    
    if args.hot:
        query += " AND temperature = 'hot'"
    if args.platform:
        query += " AND platform = ?"
        params.append(args.platform)
    if args.status:
        query += " AND status = ?"
        params.append(args.status)
    
    query += " ORDER BY last_contact DESC"

    if args.limit:
        query += " LIMIT ?"
        params.append(args.limit)

    cursor.execute(query, params)
    contacts = cursor.fetchall()
    conn.close()
    
    if not contacts:
        print("No contacts found.")
        return
    
    print(f"\n{'ID':<4} {'Name':<20} {'Platform':<10} {'Handle':<18} {'Temp':<6} {'Last Contact':<12} {'Next F/U':<12}")
    print("-" * 95)
    
    for c in contacts:
        next_fu = c['next_followup'] or '-'
        last = c['last_contact'] or '-'
        temp_emoji = {'hot': '[HOT]', 'warm': '[WARM]', 'cold': '[COLD]'}.get(c['temperature'], '•')
        print(f"{c['id']:<4} {c['name']:<20} {c['platform']:<10} {(c['handle'] or '-'):<18} {temp_emoji:<6} {last:<12} {next_fu:<12}")
    
    print(f"\nTotal: {len(contacts)} contacts")

def log_interaction(args):
    """Log an interaction with a contact."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Verify contact exists
    cursor.execute("SELECT name FROM contacts WHERE id = ?", (args.contact_id,))
    contact = cursor.fetchone()
    if not contact:
        print(f"[X] Contact #{args.contact_id} not found")
        return
    
    # Add interaction
    cursor.execute("""
        INSERT INTO interactions (contact_id, type, direction, platform, platform_ref, summary, sentiment)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (args.contact_id, args.type, args.direction, args.platform, args.ref, args.summary, args.sentiment))
    
    # Update contact's last_contact
    cursor.execute("""
        UPDATE contacts SET last_contact = date('now'), updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (args.contact_id,))
    
    conn.commit()
    conn.close()
    
    print(f"[OK] Logged {args.direction} {args.type} with {contact['name']}")

def set_followup(args):
    """Set follow-up date for a contact."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Parse date
    if args.date == 'tomorrow':
        date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    elif args.date.startswith('+'):
        days = int(args.date[1:])
        date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
    else:
        date = args.date
    
    cursor.execute("""
        UPDATE contacts SET next_followup = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (date, args.contact_id))
    
    if cursor.rowcount == 0:
        print(f"[X] Contact #{args.contact_id} not found")
    else:
        conn.commit()
        print(f"[OK] Set follow-up for #{args.contact_id} to {date}")
    
    conn.close()

def set_temperature(args):
    """Update contact temperature."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE contacts SET temperature = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (args.temp, args.contact_id))
    
    if cursor.rowcount == 0:
        print(f"[X] Contact #{args.contact_id} not found")
    else:
        conn.commit()
        print(f"[OK] Set #{args.contact_id} temperature to {args.temp}")
    
    conn.close()

def view_contact(args):
    """View detailed contact info."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM contacts WHERE id = ?", (args.contact_id,))
    contact = cursor.fetchone()
    
    if not contact:
        print(f"[X] Contact #{args.contact_id} not found")
        return
    
    temp_emoji = {'hot': '[HOT]', 'warm': '[WARM]', 'cold': '[COLD]'}.get(contact['temperature'], '•')
    
    print(f"\n{'='*50}")
    print(f"  {contact['name']} {temp_emoji}")
    print(f"{'='*50}")
    print(f"  Platform:     {contact['platform']} / {contact['handle'] or '-'}")
    print(f"  Status:       {contact['status']}")
    print(f"  Temperature:  {contact['temperature']}")
    print(f"  First Contact: {contact['first_contact'] or '-'}")
    print(f"  Last Contact:  {contact['last_contact'] or '-'}")
    print(f"  Next Follow-up: {contact['next_followup'] or 'Not set'}")
    print(f"  Opportunity:  {contact['opportunity_type'] or '-'} ({contact['opportunity_value'] or '-'})")
    print(f"  Tags:         {contact['tags'] or '-'}")
    print(f"\n  Notes: {contact['notes'] or 'None'}")
    
    # Get recent interactions
    cursor.execute("""
        SELECT * FROM interactions WHERE contact_id = ?
        ORDER BY date DESC LIMIT 5
    """, (args.contact_id,))
    interactions = cursor.fetchall()
    
    if interactions:
        print(f"\n  Recent Interactions:")
        print(f"  {'-'*45}")
        for i in interactions:
            direction = '->' if i['direction'] == 'outbound' else '<-'
            print(f"  {i['date'][:10]} {direction} {i['type']}: {i['summary'] or '(no summary)'}")
    
    conn.close()

def show_due(args):
    """Show contacts due for follow-up."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM contacts 
        WHERE next_followup IS NOT NULL 
        AND next_followup <= date('now', '+3 days')
        ORDER BY next_followup ASC
    """)
    contacts = cursor.fetchall()
    conn.close()
    
    if not contacts:
        print("[OK] No follow-ups due in the next 3 days")
        return
    
    print(f"\n[CAL] Follow-ups Due:")
    print("-" * 60)
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    for c in contacts:
        overdue = c['next_followup'] < today
        marker = "[!] OVERDUE" if overdue else ""
        temp_emoji = {'hot': '[HOT]', 'warm': '[WARM]', 'cold': '[COLD]'}.get(c['temperature'], '•')
        print(f"  #{c['id']} {c['name']} ({c['platform']}) {temp_emoji} - {c['next_followup']} {marker}")
        if c['notes']:
            print(f"      -> {c['notes'][:60]}...")
    
    print(f"\nTotal: {len(contacts)} due")

def search_contacts(args):
    """Search contacts by name, handle, or notes."""
    conn = get_db()
    cursor = conn.cursor()
    
    query = f"%{args.query}%"
    cursor.execute("""
        SELECT * FROM contacts 
        WHERE name LIKE ? OR handle LIKE ? OR notes LIKE ? OR tags LIKE ?
        ORDER BY last_contact DESC
    """, (query, query, query, query))
    
    contacts = cursor.fetchall()
    conn.close()
    
    if not contacts:
        print(f"No contacts matching '{args.query}'")
        return
    
    print(f"\nSearch results for '{args.query}':")
    for c in contacts:
        temp_emoji = {'hot': '[HOT]', 'warm': '[WARM]', 'cold': '[COLD]'}.get(c['temperature'], '•')
        print(f"  #{c['id']} {c['name']} ({c['platform']}) {temp_emoji}")

def update_notes(args):
    """Update contact notes."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE contacts SET notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (args.notes, args.contact_id))
    
    if cursor.rowcount == 0:
        print(f"[X] Contact #{args.contact_id} not found")
    else:
        conn.commit()
        print(f"[OK] Updated notes for #{args.contact_id}")
    
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="AgentForge's Relationship Tracker")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add contact
    add_parser = subparsers.add_parser('add', help='Add a new contact')
    add_parser.add_argument('name', help='Contact name')
    add_parser.add_argument('--platform', '-p', default='moltbook', help='Platform (moltbook, twitter, email)')
    add_parser.add_argument('--handle', help='@handle or email')
    add_parser.add_argument('--platform-id', help='Platform-specific ID')
    add_parser.add_argument('--temperature', '-t', default='warm', choices=['hot', 'warm', 'cold'])
    add_parser.add_argument('--opportunity', '-o', help='Opportunity type')
    add_parser.add_argument('--notes', '-n', help='Initial notes')
    
    # List contacts
    list_parser = subparsers.add_parser('list', help='List contacts')
    list_parser.add_argument('--hot', action='store_true', help='Show only hot contacts')
    list_parser.add_argument('--platform', '-p', help='Filter by platform')
    list_parser.add_argument('--status', '-s', help='Filter by status')
    list_parser.add_argument('--limit', '-l', type=int, help='Limit results')
    
    # Log interaction
    log_parser = subparsers.add_parser('log', help='Log an interaction')
    log_parser.add_argument('contact_id', type=int, help='Contact ID')
    log_parser.add_argument('--type', '-t', required=True, help='Interaction type (comment, reply, dm, email)')
    log_parser.add_argument('--direction', '-d', default='outbound', choices=['inbound', 'outbound'])
    log_parser.add_argument('--summary', '-s', help='Interaction summary')
    log_parser.add_argument('--platform', '-p', help='Platform')
    log_parser.add_argument('--ref', help='Platform reference (post_id, etc.)')
    log_parser.add_argument('--sentiment', choices=['positive', 'neutral', 'negative'])
    
    # Set follow-up
    fu_parser = subparsers.add_parser('followup', help='Set follow-up date')
    fu_parser.add_argument('contact_id', type=int, help='Contact ID')
    fu_parser.add_argument('--date', '-d', required=True, help='Date (YYYY-MM-DD, tomorrow, or +N days)')
    
    # Set temperature
    temp_parser = subparsers.add_parser('temp', help='Set contact temperature')
    temp_parser.add_argument('contact_id', type=int, help='Contact ID')
    temp_parser.add_argument('temp', choices=['hot', 'warm', 'cold'], help='Temperature')
    
    # View contact
    view_parser = subparsers.add_parser('view', help='View contact details')
    view_parser.add_argument('contact_id', type=int, help='Contact ID')
    
    # Show due follow-ups
    subparsers.add_parser('due', help='Show due follow-ups')
    
    # Search
    search_parser = subparsers.add_parser('search', help='Search contacts')
    search_parser.add_argument('query', help='Search query')
    
    # Update notes
    notes_parser = subparsers.add_parser('notes', help='Update contact notes')
    notes_parser.add_argument('contact_id', type=int, help='Contact ID')
    notes_parser.add_argument('notes', help='New notes')
    
    args = parser.parse_args()
    
    if args.command == 'add':
        add_contact(args)
    elif args.command == 'list':
        list_contacts(args)
    elif args.command == 'log':
        log_interaction(args)
    elif args.command == 'followup':
        set_followup(args)
    elif args.command == 'temp':
        set_temperature(args)
    elif args.command == 'view':
        view_contact(args)
    elif args.command == 'due':
        show_due(args)
    elif args.command == 'search':
        search_contacts(args)
    elif args.command == 'notes':
        update_notes(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
