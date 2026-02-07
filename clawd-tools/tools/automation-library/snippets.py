#!/usr/bin/env python3
"""
AgentForge Automation Library
Store reusable code snippets, workflows, commands.

Usage:
    python snippets.py add "name" --code "command or snippet" --tags git,deploy
    python snippets.py search "query"
    python snippets.py get "name"
    python snippets.py list [--tag git]
    python snippets.py run "name"  # Copy to clipboard / show
"""

import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "snippets.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS snippets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        code TEXT NOT NULL,
        language TEXT,
        tags TEXT,
        use_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        last_used TEXT
    )''')
    
    conn.commit()
    conn.close()

def add_snippet(name, code, description=None, language=None, tags=None):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        c.execute('''INSERT INTO snippets (name, description, code, language, tags, created_at)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (name, description, code, language, ','.join(tags) if tags else None,
                   datetime.now().isoformat()))
        print(f"[+] Snippet saved: {name}")
        if tags:
            print(f"    Tags: {', '.join(tags)}")
    except sqlite3.IntegrityError:
        # Update existing
        c.execute('''UPDATE snippets SET code = ?, description = ?, tags = ?
                     WHERE name = ?''',
                  (code, description, ','.join(tags) if tags else None, name))
        print(f"[>] Snippet updated: {name}")
    
    conn.commit()
    conn.close()

def get_snippet(name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT name, code, description, language, tags FROM snippets WHERE name LIKE ?', (f'%{name}%',))
    snippet = c.fetchone()
    
    if not snippet:
        print(f"Snippet '{name}' not found.")
        conn.close()
        return None
    
    # Update use count
    c.execute('UPDATE snippets SET use_count = use_count + 1, last_used = ? WHERE name = ?',
              (datetime.now().isoformat(), snippet[0]))
    conn.commit()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"SNIPPET: {snippet[0]}")
    print(f"{'='*60}")
    if snippet[2]:
        print(f"Description: {snippet[2]}")
    if snippet[4]:
        print(f"Tags: {snippet[4]}")
    print(f"\n--- CODE ---")
    print(snippet[1])
    print(f"--- END ---\n")
    
    return snippet[1]

def search_snippets(query):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT name, description, tags FROM snippets 
                 WHERE name LIKE ? OR description LIKE ? OR tags LIKE ? OR code LIKE ?''',
              (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
    results = c.fetchall()
    conn.close()
    
    if not results:
        print(f"No snippets found for '{query}'")
        return
    
    print(f"\n{'='*60}")
    print(f"SEARCH: '{query}' ({len(results)} results)")
    print(f"{'='*60}")
    
    for r in results:
        print(f"\n  > {r[0]}")
        if r[1]:
            print(f"    {r[1][:50]}...")
        if r[2]:
            print(f"    Tags: {r[2]}")

def list_snippets(tag=None):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if tag:
        c.execute('SELECT name, description, use_count, tags FROM snippets WHERE tags LIKE ? ORDER BY use_count DESC',
                  (f'%{tag}%',))
    else:
        c.execute('SELECT name, description, use_count, tags FROM snippets ORDER BY use_count DESC')
    
    snippets = c.fetchall()
    conn.close()
    
    if not snippets:
        print("No snippets saved yet.")
        return
    
    print(f"\n{'='*60}")
    print("AUTOMATION LIBRARY")
    print(f"{'='*60}")
    
    for s in snippets:
        print(f"\n  > {s[0]} (used {s[2]}x)")
        if s[1]:
            print(f"    {s[1][:50]}...")
        if s[3]:
            print(f"    Tags: {s[3]}")

def main():
    parser = argparse.ArgumentParser(description='Automation Library')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add
    add_parser = subparsers.add_parser('add', help='Add snippet')
    add_parser.add_argument('name', help='Snippet name')
    add_parser.add_argument('--code', '-c', required=True, help='Code/command')
    add_parser.add_argument('--desc', '-d', help='Description')
    add_parser.add_argument('--lang', '-l', help='Language')
    add_parser.add_argument('--tags', '-t', help='Comma-separated tags')
    
    # Get
    get_parser = subparsers.add_parser('get', help='Get snippet')
    get_parser.add_argument('name')
    
    # Search
    search_parser = subparsers.add_parser('search', help='Search snippets')
    search_parser.add_argument('query')
    
    # List
    list_parser = subparsers.add_parser('list', help='List snippets')
    list_parser.add_argument('--tag', '-t', help='Filter by tag')
    
    # Run (alias for get)
    run_parser = subparsers.add_parser('run', help='Get and show snippet')
    run_parser.add_argument('name')
    
    # Init
    subparsers.add_parser('init', help='Initialize database')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_db()
        print("Snippets database initialized.")
    elif args.command == 'add':
        tags = args.tags.split(',') if args.tags else None
        add_snippet(args.name, args.code, args.desc, args.lang, tags)
    elif args.command == 'get' or args.command == 'run':
        get_snippet(args.name)
    elif args.command == 'search':
        search_snippets(args.query)
    elif args.command == 'list':
        list_snippets(args.tag)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
