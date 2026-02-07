#!/usr/bin/env python3
"""
AgentForge Goal Tracker
Track longer-term goals with milestones and progress.

Usage:
    python goals.py add "goal" --category work --target "2026-03-01"
    python goals.py milestone <goal_id> "milestone description"
    python goals.py progress <goal_id> <percent>
    python goals.py list [--active|--completed]
    python goals.py view <goal_id>
    python goals.py check  # Quick check on all goals
"""

import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "goals.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT,
        created_at TEXT NOT NULL,
        target_date TEXT,
        progress INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        completed_at TEXT,
        notes TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS milestones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        completed_at TEXT,
        status TEXT DEFAULT 'pending',
        FOREIGN KEY (goal_id) REFERENCES goals(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS goal_updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        update_type TEXT,
        content TEXT,
        FOREIGN KEY (goal_id) REFERENCES goals(id)
    )''')
    
    conn.commit()
    conn.close()

def add_goal(title, description=None, category=None, target_date=None):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO goals (title, description, category, created_at, target_date)
                 VALUES (?, ?, ?, ?, ?)''',
              (title, description, category, datetime.now().isoformat(), target_date))
    
    goal_id = c.lastrowid
    conn.commit()
    conn.close()
    
    print(f"\n[GOAL #{goal_id}] {title}")
    if category:
        print(f"  Category: {category}")
    if target_date:
        print(f"  Target: {target_date}")
    print(f"\n  Add milestones: python goals.py milestone {goal_id} \"milestone\"")
    
    return goal_id

def add_milestone(goal_id, title):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT title FROM goals WHERE id = ?', (goal_id,))
    goal = c.fetchone()
    if not goal:
        print(f"Goal #{goal_id} not found.")
        conn.close()
        return
    
    c.execute('''INSERT INTO milestones (goal_id, title, created_at)
                 VALUES (?, ?, ?)''',
              (goal_id, title, datetime.now().isoformat()))
    
    milestone_id = c.lastrowid
    conn.commit()
    conn.close()
    
    print(f"[+] Milestone added to '{goal[0]}'")
    print(f"    {title}")
    
    return milestone_id

def complete_milestone(milestone_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''UPDATE milestones SET status = 'completed', completed_at = ?
                 WHERE id = ?''', (datetime.now().isoformat(), milestone_id))
    
    # Get goal and update progress
    c.execute('SELECT goal_id FROM milestones WHERE id = ?', (milestone_id,))
    result = c.fetchone()
    if result:
        goal_id = result[0]
        c.execute('SELECT COUNT(*) FROM milestones WHERE goal_id = ?', (goal_id,))
        total = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM milestones WHERE goal_id = ? AND status = "completed"', (goal_id,))
        completed = c.fetchone()[0]
        progress = int(100 * completed / total) if total > 0 else 0
        c.execute('UPDATE goals SET progress = ? WHERE id = ?', (progress, goal_id))
    
    conn.commit()
    conn.close()
    print(f"[OK] Milestone #{milestone_id} completed!")

def update_progress(goal_id, progress):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('UPDATE goals SET progress = ? WHERE id = ?', (min(100, max(0, progress)), goal_id))
    
    if progress >= 100:
        c.execute('UPDATE goals SET status = "completed", completed_at = ? WHERE id = ?',
                  (datetime.now().isoformat(), goal_id))
        print(f"[OK] Goal #{goal_id} COMPLETED!")
    else:
        print(f"[>] Goal #{goal_id} progress: {progress}%")
    
    conn.commit()
    conn.close()

def list_goals(status_filter=None):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if status_filter:
        c.execute('SELECT id, title, category, progress, target_date, status FROM goals WHERE status = ? ORDER BY target_date', (status_filter,))
    else:
        c.execute('SELECT id, title, category, progress, target_date, status FROM goals ORDER BY status, target_date')
    
    goals = c.fetchall()
    conn.close()
    
    if not goals:
        print("No goals found.")
        return
    
    print(f"\n{'='*60}")
    print("GOALS")
    print(f"{'='*60}")
    
    for g in goals:
        status_emoji = {'active': '[>]', 'completed': '[OK]', 'abandoned': '[X]'}.get(g[5], '[?]')
        bar_len = 20
        filled = int(bar_len * g[3] / 100)
        bar = '#' * filled + '-' * (bar_len - filled)
        
        print(f"\n  #{g[0]} {status_emoji} {g[1]}")
        print(f"      [{bar}] {g[3]}%")
        if g[2]:
            print(f"      Category: {g[2]}")
        if g[4]:
            print(f"      Target: {g[4]}")

def view_goal(goal_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT * FROM goals WHERE id = ?', (goal_id,))
    goal = c.fetchone()
    
    if not goal:
        print(f"Goal #{goal_id} not found.")
        conn.close()
        return
    
    print(f"\n{'='*60}")
    print(f"GOAL #{goal[0]}: {goal[1]}")
    print(f"{'='*60}")
    print(f"Status: {goal[7]} | Progress: {goal[6]}%")
    print(f"Category: {goal[3] or 'None'}")
    print(f"Created: {goal[4][:10]}")
    if goal[5]:
        print(f"Target: {goal[5]}")
    if goal[2]:
        print(f"\nDescription: {goal[2]}")
    
    # Milestones
    c.execute('SELECT id, title, status, completed_at FROM milestones WHERE goal_id = ? ORDER BY id', (goal_id,))
    milestones = c.fetchall()
    
    if milestones:
        print(f"\nMilestones ({len([m for m in milestones if m[2] == 'completed'])}/{len(milestones)} completed):")
        for m in milestones:
            emoji = '[OK]' if m[2] == 'completed' else '[ ]'
            print(f"  {emoji} {m[1]}")
    
    conn.close()

def check_goals():
    """Quick health check on all active goals."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT id, title, progress, target_date FROM goals WHERE status = "active" ORDER BY target_date')
    goals = c.fetchall()
    conn.close()
    
    print(f"\n{'='*50}")
    print("GOAL CHECK")
    print(f"{'='*50}")
    
    if not goals:
        print("No active goals. Add some!")
        return
    
    today = datetime.now().date()
    
    for g in goals:
        status = "On track"
        emoji = "[>]"
        
        if g[3]:  # Has target date
            target = datetime.strptime(g[3], '%Y-%m-%d').date()
            days_left = (target - today).days
            
            if days_left < 0:
                status = f"OVERDUE by {-days_left} days!"
                emoji = "[!]"
            elif days_left < 7:
                status = f"Due in {days_left} days"
                emoji = "[!]"
            else:
                status = f"{days_left} days left"
        
        bar_len = 15
        filled = int(bar_len * g[2] / 100)
        bar = '#' * filled + '-' * (bar_len - filled)
        
        print(f"\n  {emoji} {g[1]}")
        print(f"      [{bar}] {g[2]}% - {status}")

def main():
    parser = argparse.ArgumentParser(description='Goal Tracker')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add
    add_parser = subparsers.add_parser('add', help='Add a goal')
    add_parser.add_argument('title', help='Goal title')
    add_parser.add_argument('--desc', '-d', help='Description')
    add_parser.add_argument('--category', '-c', help='Category')
    add_parser.add_argument('--target', '-t', help='Target date (YYYY-MM-DD)')
    
    # Milestone
    ms_parser = subparsers.add_parser('milestone', help='Add milestone')
    ms_parser.add_argument('goal_id', type=int)
    ms_parser.add_argument('title', help='Milestone title')
    
    # Complete milestone
    comp_parser = subparsers.add_parser('complete', help='Complete milestone')
    comp_parser.add_argument('milestone_id', type=int)
    
    # Progress
    prog_parser = subparsers.add_parser('progress', help='Update progress')
    prog_parser.add_argument('goal_id', type=int)
    prog_parser.add_argument('percent', type=int)
    
    # List
    list_parser = subparsers.add_parser('list', help='List goals')
    list_parser.add_argument('--active', action='store_true')
    list_parser.add_argument('--completed', action='store_true')
    
    # View
    view_parser = subparsers.add_parser('view', help='View goal')
    view_parser.add_argument('goal_id', type=int)
    
    # Check
    subparsers.add_parser('check', help='Check all goals')
    
    # Init
    subparsers.add_parser('init', help='Initialize database')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_db()
        print("Goals database initialized.")
    elif args.command == 'add':
        add_goal(args.title, args.desc, args.category, args.target)
    elif args.command == 'milestone':
        add_milestone(args.goal_id, args.title)
    elif args.command == 'complete':
        complete_milestone(args.milestone_id)
    elif args.command == 'progress':
        update_progress(args.goal_id, args.percent)
    elif args.command == 'list':
        status = 'active' if args.active else ('completed' if args.completed else None)
        list_goals(status)
    elif args.command == 'view':
        view_goal(args.goal_id)
    elif args.command == 'check':
        check_goals()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
