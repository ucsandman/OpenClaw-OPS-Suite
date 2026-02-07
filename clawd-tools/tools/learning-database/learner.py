#!/usr/bin/env python3
"""
Learning Database
Track decisions, outcomes, and patterns to get smarter over time.

Part of the AgentForge Toolkit by Practical Systems.

Usage:
    python learner.py log "decision" --context "situation" --tags tag1,tag2
    python learner.py outcome <id> --result success|failure|mixed --notes "what happened"
    python learner.py patterns --tag <tag>
    python learner.py lessons
    python learner.py search "query"
    python learner.py stats
"""

import argparse
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path


def get_db_path():
    """Get database path from env or default."""
    if os.environ.get("AGENTFORGE_DATA"):
        return Path(os.environ["AGENTFORGE_DATA"]) / "learning.db"
    return Path(__file__).parent / "data" / "learning.db"


DB_PATH = get_db_path()

def init_db():
    """Initialize the learning database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Decisions table - what I decided and why
    c.execute('''CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        decision TEXT NOT NULL,
        context TEXT,
        reasoning TEXT,
        tags TEXT,
        outcome_id INTEGER,
        FOREIGN KEY (outcome_id) REFERENCES outcomes(id)
    )''')
    
    # Outcomes table - what actually happened
    c.execute('''CREATE TABLE IF NOT EXISTS outcomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        result TEXT NOT NULL,
        notes TEXT,
        impact_score INTEGER DEFAULT 0,
        FOREIGN KEY (decision_id) REFERENCES decisions(id)
    )''')
    
    # Lessons table - distilled learnings
    c.execute('''CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        lesson TEXT NOT NULL,
        source_decisions TEXT,
        confidence INTEGER DEFAULT 50,
        times_validated INTEGER DEFAULT 0,
        times_contradicted INTEGER DEFAULT 0,
        tags TEXT
    )''')
    
    # Patterns table - recurring situations
    c.execute('''CREATE TABLE IF NOT EXISTS patterns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern_name TEXT NOT NULL,
        description TEXT,
        best_approach TEXT,
        success_rate REAL DEFAULT 0,
        sample_size INTEGER DEFAULT 0,
        tags TEXT
    )''')
    
    conn.commit()
    conn.close()
    print("Learning database initialized.")

def log_decision(decision, context=None, reasoning=None, tags=None):
    """Log a decision I made."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO decisions (timestamp, decision, context, reasoning, tags)
                 VALUES (?, ?, ?, ?, ?)''',
              (datetime.now().isoformat(), decision, context, reasoning, 
               ','.join(tags) if tags else None))
    
    decision_id = c.lastrowid
    conn.commit()
    conn.close()
    
    print(f"[LOGGED] Decision #{decision_id}: {decision[:60]}...")
    if context:
        print(f"  Context: {context[:60]}...")
    if tags:
        print(f"  Tags: {', '.join(tags)}")
    return decision_id

def record_outcome(decision_id, result, notes=None, impact_score=0):
    """Record the outcome of a decision."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO outcomes (decision_id, timestamp, result, notes, impact_score)
                 VALUES (?, ?, ?, ?, ?)''',
              (decision_id, datetime.now().isoformat(), result, notes, impact_score))
    
    outcome_id = c.lastrowid
    
    # Link outcome to decision
    c.execute('UPDATE decisions SET outcome_id = ? WHERE id = ?', (outcome_id, decision_id))
    
    conn.commit()
    conn.close()
    
    emoji = {"success": "[OK]", "failure": "[X]", "mixed": "[~]"}.get(result, "[?]")
    print(f"{emoji} Outcome recorded for decision #{decision_id}: {result}")
    if notes:
        print(f"  Notes: {notes[:80]}...")
    
    return outcome_id

def add_lesson(lesson, source_decisions=None, confidence=50, tags=None):
    """Add a distilled lesson learned."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO lessons (timestamp, lesson, source_decisions, confidence, tags)
                 VALUES (?, ?, ?, ?, ?)''',
              (datetime.now().isoformat(), lesson, 
               ','.join(map(str, source_decisions)) if source_decisions else None,
               confidence,
               ','.join(tags) if tags else None))
    
    lesson_id = c.lastrowid
    conn.commit()
    conn.close()
    
    print(f"[LESSON #{lesson_id}] {lesson}")
    print(f"  Confidence: {confidence}%")
    return lesson_id

def get_lessons(tag=None, min_confidence=0):
    """Get all lessons, optionally filtered."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if tag:
        c.execute('''SELECT id, lesson, confidence, times_validated, times_contradicted, tags 
                     FROM lessons WHERE tags LIKE ? AND confidence >= ?
                     ORDER BY confidence DESC''', (f'%{tag}%', min_confidence))
    else:
        c.execute('''SELECT id, lesson, confidence, times_validated, times_contradicted, tags 
                     FROM lessons WHERE confidence >= ?
                     ORDER BY confidence DESC''', (min_confidence,))
    
    lessons = c.fetchall()
    conn.close()
    
    if not lessons:
        print("No lessons found.")
        return []
    
    print(f"\n{'='*60}")
    print("LESSONS LEARNED")
    print(f"{'='*60}")
    
    for l in lessons:
        conf_bar = "[" + "#" * (l[2]//10) + "-" * (10 - l[2]//10) + "]"
        print(f"\n#{l[0]} {conf_bar} {l[2]}%")
        print(f"  {l[1]}")
        if l[5]:
            print(f"  Tags: {l[5]}")
        print(f"  Validated: {l[3]}x | Contradicted: {l[4]}x")
    
    return lessons

def analyze_patterns(tag=None):
    """Analyze decision patterns and success rates."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get decisions with outcomes
    if tag:
        c.execute('''SELECT d.id, d.decision, d.context, d.tags, o.result, o.notes
                     FROM decisions d
                     LEFT JOIN outcomes o ON d.outcome_id = o.id
                     WHERE d.tags LIKE ?
                     ORDER BY d.timestamp DESC''', (f'%{tag}%',))
    else:
        c.execute('''SELECT d.id, d.decision, d.context, d.tags, o.result, o.notes
                     FROM decisions d
                     LEFT JOIN outcomes o ON d.outcome_id = o.id
                     ORDER BY d.timestamp DESC''')
    
    decisions = c.fetchall()
    conn.close()
    
    if not decisions:
        print("No decisions recorded yet.")
        return
    
    # Calculate stats
    total = len(decisions)
    with_outcome = sum(1 for d in decisions if d[4])
    successes = sum(1 for d in decisions if d[4] == 'success')
    failures = sum(1 for d in decisions if d[4] == 'failure')
    mixed = sum(1 for d in decisions if d[4] == 'mixed')
    
    print(f"\n{'='*60}")
    print("DECISION PATTERNS ANALYSIS")
    print(f"{'='*60}")
    print(f"\nTotal decisions: {total}")
    print(f"With outcomes: {with_outcome}")
    if with_outcome > 0:
        print(f"\nSuccess rate: {successes}/{with_outcome} ({100*successes/with_outcome:.1f}%)")
        print(f"  [OK] Success: {successes}")
        print(f"  [X] Failure: {failures}")
        print(f"  [~] Mixed: {mixed}")
    
    # Tag analysis
    tag_stats = {}
    for d in decisions:
        if d[3]:
            for t in d[3].split(','):
                t = t.strip()
                if t not in tag_stats:
                    tag_stats[t] = {'total': 0, 'success': 0, 'failure': 0}
                tag_stats[t]['total'] += 1
                if d[4] == 'success':
                    tag_stats[t]['success'] += 1
                elif d[4] == 'failure':
                    tag_stats[t]['failure'] += 1
    
    if tag_stats:
        print(f"\n{'='*40}")
        print("SUCCESS RATES BY TAG")
        print(f"{'='*40}")
        for t, stats in sorted(tag_stats.items(), key=lambda x: -x[1]['success']/(x[1]['total'] or 1)):
            if stats['total'] > 0:
                rate = 100 * stats['success'] / stats['total']
                print(f"  {t}: {rate:.0f}% ({stats['success']}/{stats['total']})")

def search_decisions(query):
    """Search through decisions and lessons."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT id, decision, context, tags, timestamp 
                 FROM decisions 
                 WHERE decision LIKE ? OR context LIKE ?
                 ORDER BY timestamp DESC LIMIT 20''', 
              (f'%{query}%', f'%{query}%'))
    
    decisions = c.fetchall()
    
    c.execute('''SELECT id, lesson, confidence, tags 
                 FROM lessons 
                 WHERE lesson LIKE ?
                 ORDER BY confidence DESC LIMIT 10''',
              (f'%{query}%',))
    
    lessons = c.fetchall()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"SEARCH RESULTS: '{query}'")
    print(f"{'='*60}")
    
    if decisions:
        print(f"\n[DECISIONS] ({len(decisions)} found)")
        for d in decisions:
            print(f"  #{d[0]}: {d[1][:50]}...")
            if d[2]:
                print(f"       Context: {d[2][:40]}...")
    
    if lessons:
        print(f"\n[LESSONS] ({len(lessons)} found)")
        for l in lessons:
            print(f"  #{l[0]} ({l[2]}%): {l[1][:60]}...")

def get_stats():
    """Get overall learning statistics."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM decisions')
    total_decisions = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM outcomes')
    total_outcomes = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM lessons')
    total_lessons = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM outcomes WHERE result = "success"')
    successes = c.fetchone()[0]
    
    conn.close()
    
    print(f"\n{'='*40}")
    print("LEARNING DATABASE STATS")
    print(f"{'='*40}")
    print(f"  Decisions logged: {total_decisions}")
    print(f"  Outcomes recorded: {total_outcomes}")
    print(f"  Lessons distilled: {total_lessons}")
    if total_outcomes > 0:
        print(f"  Overall success rate: {100*successes/total_outcomes:.1f}%")
    print(f"\n  Database: {DB_PATH}")

def main():
    parser = argparse.ArgumentParser(description='Learning Database - Track decisions and outcomes')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Log decision
    log_parser = subparsers.add_parser('log', help='Log a decision')
    log_parser.add_argument('decision', help='The decision made')
    log_parser.add_argument('--context', '-c', help='Context/situation')
    log_parser.add_argument('--reasoning', '-r', help='Why this decision')
    log_parser.add_argument('--tags', '-t', help='Comma-separated tags')
    
    # Record outcome
    outcome_parser = subparsers.add_parser('outcome', help='Record an outcome')
    outcome_parser.add_argument('decision_id', type=int, help='Decision ID')
    outcome_parser.add_argument('--result', '-r', required=True, 
                                choices=['success', 'failure', 'mixed'])
    outcome_parser.add_argument('--notes', '-n', help='What happened')
    outcome_parser.add_argument('--impact', '-i', type=int, default=0, 
                                help='Impact score (-10 to 10)')
    
    # Add lesson
    lesson_parser = subparsers.add_parser('lesson', help='Add a lesson learned')
    lesson_parser.add_argument('lesson', help='The lesson')
    lesson_parser.add_argument('--sources', '-s', help='Source decision IDs (comma-sep)')
    lesson_parser.add_argument('--confidence', '-c', type=int, default=50)
    lesson_parser.add_argument('--tags', '-t', help='Comma-separated tags')
    
    # View lessons
    lessons_parser = subparsers.add_parser('lessons', help='View lessons')
    lessons_parser.add_argument('--tag', '-t', help='Filter by tag')
    lessons_parser.add_argument('--min-confidence', '-c', type=int, default=0)
    
    # Analyze patterns
    patterns_parser = subparsers.add_parser('patterns', help='Analyze patterns')
    patterns_parser.add_argument('--tag', '-t', help='Filter by tag')
    
    # Search
    search_parser = subparsers.add_parser('search', help='Search decisions/lessons')
    search_parser.add_argument('query', help='Search query')
    
    # Stats
    subparsers.add_parser('stats', help='Show statistics')
    
    # Init
    subparsers.add_parser('init', help='Initialize database')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_db()
    elif args.command == 'log':
        tags = args.tags.split(',') if args.tags else None
        log_decision(args.decision, args.context, args.reasoning, tags)
    elif args.command == 'outcome':
        record_outcome(args.decision_id, args.result, args.notes, args.impact)
    elif args.command == 'lesson':
        sources = [int(x) for x in args.sources.split(',')] if args.sources else None
        tags = args.tags.split(',') if args.tags else None
        add_lesson(args.lesson, sources, args.confidence, tags)
    elif args.command == 'lessons':
        get_lessons(args.tag, args.min_confidence)
    elif args.command == 'patterns':
        analyze_patterns(args.tag)
    elif args.command == 'search':
        search_decisions(args.query)
    elif args.command == 'stats':
        get_stats()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
