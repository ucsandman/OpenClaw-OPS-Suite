#!/usr/bin/env python3
"""
AgentForge Project Health Monitor
Track project status, detect stalled projects, dependencies.

Usage:
    python monitor.py scan             # Scan all projects
    python monitor.py status <project>  # Check specific project
    python monitor.py stalled          # Show stalled projects
    python monitor.py update <project> --status active|stalled|completed
"""

import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

DB_PATH = Path(__file__).parent / "data" / "projects.db"
WORKSPACE = Path(__file__).parent.parent.parent
PROJECTS_DIR = WORKSPACE / "projects"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        path TEXT,
        status TEXT DEFAULT 'active',
        last_commit TEXT,
        last_activity TEXT,
        priority INTEGER DEFAULT 5,
        notes TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS project_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        files_changed INTEGER,
        status TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )''')
    
    conn.commit()
    conn.close()

def scan_projects():
    """Scan all projects and update their status."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if not PROJECTS_DIR.exists():
        print("Projects directory not found.")
        return
    
    projects = []
    for p in PROJECTS_DIR.iterdir():
        if p.is_dir() and not p.name.startswith('.'):
            # Get last modified time
            try:
                latest = max(f.stat().st_mtime for f in p.rglob('*') if f.is_file())
                last_activity = datetime.fromtimestamp(latest)
            except:
                last_activity = None
            
            # Check if in database
            c.execute('SELECT id, last_activity FROM projects WHERE name = ?', (p.name,))
            existing = c.fetchone()
            
            if existing:
                c.execute('UPDATE projects SET last_activity = ?, path = ? WHERE id = ?',
                          (last_activity.isoformat() if last_activity else None, str(p), existing[0]))
            else:
                c.execute('''INSERT INTO projects (name, path, last_activity)
                             VALUES (?, ?, ?)''',
                          (p.name, str(p), last_activity.isoformat() if last_activity else None))
            
            # Determine health
            days_inactive = (datetime.now() - last_activity).days if last_activity else 999
            health = 'active' if days_inactive < 7 else 'stale' if days_inactive < 30 else 'stalled'
            
            projects.append({
                'name': p.name,
                'last_activity': last_activity,
                'days_inactive': days_inactive,
                'health': health
            })
    
    conn.commit()
    conn.close()
    
    # Display results
    print(f"\n{'='*60}")
    print(f"PROJECT SCAN ({len(projects)} projects)")
    print(f"{'='*60}")
    
    # Sort by activity
    projects.sort(key=lambda x: x['days_inactive'])
    
    health_emoji = {'active': '[OK]', 'stale': '[!]', 'stalled': '[X]'}
    
    for p in projects:
        emoji = health_emoji.get(p['health'], '[?]')
        activity_str = f"{p['days_inactive']}d ago" if p['last_activity'] else "unknown"
        print(f"  {emoji} {p['name']:<25} {activity_str}")

def check_project(name):
    """Check specific project status."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT * FROM projects WHERE name LIKE ?', (f'%{name}%',))
    project = c.fetchone()
    
    if not project:
        print(f"Project '{name}' not found. Run 'scan' first.")
        conn.close()
        return
    
    print(f"\n{'='*60}")
    print(f"PROJECT: {project[1]}")
    print(f"{'='*60}")
    print(f"Status: {project[3]}")
    print(f"Path: {project[2]}")
    print(f"Last activity: {project[5][:10] if project[5] else 'Unknown'}")
    print(f"Priority: {project[6]}/10")
    
    # Check for README
    project_path = Path(project[2])
    readme = project_path / "README.md"
    if readme.exists():
        with open(readme, encoding='utf-8', errors='ignore') as f:
            desc = f.read(200).split('\n')[0].replace('#', '').strip()
        print(f"Description: {desc[:50]}...")
    
    # Count files
    if project_path.exists():
        file_count = sum(1 for _ in project_path.rglob('*') if _.is_file())
        print(f"Files: {file_count}")
    
    conn.close()

def show_stalled():
    """Show stalled projects."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Projects with no activity in 14+ days
    cutoff = (datetime.now() - timedelta(days=14)).isoformat()
    c.execute('''SELECT name, last_activity, status FROM projects 
                 WHERE last_activity < ? OR last_activity IS NULL
                 ORDER BY last_activity''', (cutoff,))
    stalled = c.fetchall()
    conn.close()
    
    if not stalled:
        print("No stalled projects! Everything is active.")
        return
    
    print(f"\n{'='*60}")
    print(f"STALLED PROJECTS ({len(stalled)})")
    print(f"{'='*60}")
    
    for p in stalled:
        if p[1]:
            days = (datetime.now() - datetime.fromisoformat(p[1])).days
            print(f"\n  [X] {p[0]}")
            print(f"      Inactive for {days} days")
        else:
            print(f"\n  [?] {p[0]}")
            print(f"      No activity data")

def update_project(name, status=None, priority=None, notes=None):
    """Update project status."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT id FROM projects WHERE name LIKE ?', (f'%{name}%',))
    project = c.fetchone()
    
    if not project:
        print(f"Project '{name}' not found.")
        conn.close()
        return
    
    if status:
        c.execute('UPDATE projects SET status = ? WHERE id = ?', (status, project[0]))
        print(f"[>] {name} status -> {status}")
    
    if priority:
        c.execute('UPDATE projects SET priority = ? WHERE id = ?', (priority, project[0]))
        print(f"[>] {name} priority -> {priority}")
    
    if notes:
        c.execute('UPDATE projects SET notes = ? WHERE id = ?', (notes, project[0]))
    
    conn.commit()
    conn.close()

def main():
    parser = argparse.ArgumentParser(description='Project Health Monitor')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Scan
    subparsers.add_parser('scan', help='Scan all projects')
    
    # Status
    status_parser = subparsers.add_parser('status', help='Check project')
    status_parser.add_argument('project')
    
    # Stalled
    subparsers.add_parser('stalled', help='Show stalled projects')
    
    # Update
    update_parser = subparsers.add_parser('update', help='Update project')
    update_parser.add_argument('project')
    update_parser.add_argument('--status', '-s', choices=['active', 'stalled', 'completed', 'paused'])
    update_parser.add_argument('--priority', '-p', type=int)
    update_parser.add_argument('--notes', '-n')
    
    # Init
    subparsers.add_parser('init', help='Initialize database')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_db()
        print("Project monitor database initialized.")
    elif args.command == 'scan':
        scan_projects()
    elif args.command == 'status':
        check_project(args.project)
    elif args.command == 'stalled':
        show_stalled()
    elif args.command == 'update':
        update_project(args.project, args.status, args.priority, args.notes)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
