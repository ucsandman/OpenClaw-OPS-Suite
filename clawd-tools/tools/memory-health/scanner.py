#!/usr/bin/env python3
"""
Memory Health Scanner
Analyzes memory files for health metrics: staleness, duplicates, gaps, and more.
"""

import sqlite3
import json
import re
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent / "data" / "memory_health.db"
MEMORY_DIR = Path(__file__).parent.parent.parent / "memory"
MEMORY_MD = Path(__file__).parent.parent.parent / "MEMORY.md"

def init_db():
    """Initialize the database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS health_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            total_files INTEGER,
            total_lines INTEGER,
            total_size_kb REAL,
            memory_md_lines INTEGER,
            memory_md_size_kb REAL,
            oldest_daily_file TEXT,
            newest_daily_file TEXT,
            days_with_notes INTEGER,
            avg_lines_per_day REAL,
            potential_duplicates INTEGER,
            stale_facts_count INTEGER,
            last_consolidation TEXT,
            health_score INTEGER
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS memory_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            source_file TEXT,
            line_number INTEGER,
            content TEXT,
            content_hash TEXT,
            category TEXT,
            age_days INTEGER,
            is_stale INTEGER DEFAULT 0,
            is_duplicate INTEGER DEFAULT 0
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS retrieval_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            query TEXT,
            results_count INTEGER,
            snippets_used INTEGER,
            relevance_score REAL,
            session_key TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"[OK] Database initialized: {DB_PATH}")

def scan_memory_files():
    """Scan all memory files and extract metrics."""
    stats = {
        'total_files': 0,
        'total_lines': 0,
        'total_size_kb': 0,
        'memory_md_lines': 0,
        'memory_md_size_kb': 0,
        'oldest_daily': None,
        'newest_daily': None,
        'daily_files': [],
        'all_content': []
    }
    
    # Scan MEMORY.md
    if MEMORY_MD.exists():
        content = MEMORY_MD.read_text(encoding='utf-8', errors='ignore')
        stats['memory_md_lines'] = len(content.splitlines())
        stats['memory_md_size_kb'] = len(content.encode('utf-8')) / 1024
        stats['total_files'] += 1
        stats['total_lines'] += stats['memory_md_lines']
        stats['total_size_kb'] += stats['memory_md_size_kb']
        stats['all_content'].append(('MEMORY.md', content))
    
    # Scan daily memory files
    if MEMORY_DIR.exists():
        for f in MEMORY_DIR.glob('*.md'):
            if f.name.startswith('20'):  # Daily files like 2026-02-04.md
                stats['daily_files'].append(f.name)
                content = f.read_text(encoding='utf-8', errors='ignore')
                lines = len(content.splitlines())
                size_kb = len(content.encode('utf-8')) / 1024
                
                stats['total_files'] += 1
                stats['total_lines'] += lines
                stats['total_size_kb'] += size_kb
                stats['all_content'].append((f.name, content))
    
    # Find oldest and newest daily files
    if stats['daily_files']:
        stats['daily_files'].sort()
        stats['oldest_daily'] = stats['daily_files'][0]
        stats['newest_daily'] = stats['daily_files'][-1]
    
    return stats

def extract_facts(content, source_file):
    """Extract individual facts/statements from content."""
    facts = []
    lines = content.splitlines()
    
    for i, line in enumerate(lines):
        line = line.strip()
        # Skip empty lines, headers, and very short lines
        if not line or line.startswith('#') or len(line) < 20:
            continue
        # Skip code blocks
        if line.startswith('```') or line.startswith('   '):
            continue
            
        facts.append({
            'source_file': source_file,
            'line_number': i + 1,
            'content': line[:500],  # Truncate long lines
            'content_hash': hashlib.md5(line.lower().encode()).hexdigest()[:16]
        })
    
    return facts

def detect_duplicates(facts):
    """Find potential duplicate content across memory files."""
    hash_map = defaultdict(list)
    
    for fact in facts:
        hash_map[fact['content_hash']].append(fact)
    
    duplicates = []
    for hash_val, items in hash_map.items():
        if len(items) > 1:
            duplicates.append({
                'hash': hash_val,
                'count': len(items),
                'locations': [(f['source_file'], f['line_number']) for f in items],
                'sample': items[0]['content'][:100]
            })
    
    return duplicates

def detect_stale_facts(facts, stale_days=30):
    """Identify facts that might be outdated."""
    stale = []
    today = datetime.now()
    
    # Patterns that suggest time-sensitive info
    time_patterns = [
        r'\b(today|tomorrow|yesterday|this week|next week)\b',
        r'\b(currently|now|at the moment|right now)\b',
        r'\b(will|going to|planning to|about to)\b',
        r'\b\d{4}-\d{2}-\d{2}\b',  # Dates
    ]
    
    for fact in facts:
        # Check if from an old daily file
        if fact['source_file'].startswith('20'):
            try:
                file_date = datetime.strptime(fact['source_file'][:10], '%Y-%m-%d')
                age = (today - file_date).days
                if age > stale_days:
                    # Check if content has time-sensitive language
                    for pattern in time_patterns:
                        if re.search(pattern, fact['content'], re.IGNORECASE):
                            stale.append({
                                'source': fact['source_file'],
                                'line': fact['line_number'],
                                'age_days': age,
                                'content': fact['content'][:100],
                                'reason': 'Time-sensitive language in old file'
                            })
                            break
            except ValueError:
                pass
    
    return stale

def calculate_health_score(stats, duplicates, stale):
    """Calculate overall memory health score (0-100)."""
    score = 100
    
    # Penalize for too many duplicates
    dup_ratio = len(duplicates) / max(1, stats['total_lines'] / 50)
    score -= min(20, int(dup_ratio * 10))
    
    # Penalize for stale content
    stale_ratio = len(stale) / max(1, stats['total_lines'] / 20)
    score -= min(20, int(stale_ratio * 10))
    
    # Penalize if MEMORY.md is too large (>500 lines)
    if stats['memory_md_lines'] > 500:
        score -= min(15, (stats['memory_md_lines'] - 500) // 100)
    
    # Penalize if no recent daily files
    if stats['newest_daily']:
        try:
            newest = datetime.strptime(stats['newest_daily'][:10], '%Y-%m-%d')
            days_since = (datetime.now() - newest).days
            if days_since > 3:
                score -= min(15, days_since * 2)
        except ValueError:
            pass
    
    # Bonus for consistent daily notes
    if len(stats['daily_files']) >= 7:
        score += 5
    
    return max(0, min(100, score))

def store_health_snapshot(stats, duplicates, stale, health_score):
    """Store health metrics in database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO health_snapshots 
        (timestamp, total_files, total_lines, total_size_kb, memory_md_lines, memory_md_size_kb,
         oldest_daily_file, newest_daily_file, days_with_notes, avg_lines_per_day,
         potential_duplicates, stale_facts_count, health_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(),
        stats['total_files'],
        stats['total_lines'],
        round(stats['total_size_kb'], 2),
        stats['memory_md_lines'],
        round(stats['memory_md_size_kb'], 2),
        stats['oldest_daily'],
        stats['newest_daily'],
        len(stats['daily_files']),
        round(stats['total_lines'] / max(1, len(stats['daily_files'])), 1),
        len(duplicates),
        len(stale),
        health_score
    ))
    
    conn.commit()
    conn.close()

def log_retrieval(query, results_count, snippets_used, relevance_score=None, session_key=None):
    """Log a memory retrieval operation."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO retrieval_log (timestamp, query, results_count, snippets_used, relevance_score, session_key)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.now().isoformat(), query, results_count, snippets_used, relevance_score, session_key))
    
    conn.commit()
    conn.close()

def get_retrieval_stats():
    """Get retrieval statistics."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT 
            COUNT(*) as total_queries,
            AVG(results_count) as avg_results,
            AVG(snippets_used) as avg_snippets,
            AVG(relevance_score) as avg_relevance
        FROM retrieval_log
        WHERE timestamp > datetime('now', '-7 days')
    ''')
    
    row = c.fetchone()
    conn.close()
    
    return {
        'total_queries': row[0] or 0,
        'avg_results': round(row[1] or 0, 1),
        'avg_snippets': round(row[2] or 0, 1),
        'avg_relevance': round(row[3] or 0, 2) if row[3] else None
    }

def run_full_scan():
    """Run a complete memory health scan."""
    init_db()
    
    print("Scanning memory files...")
    stats = scan_memory_files()
    
    print("Extracting facts...")
    all_facts = []
    for source, content in stats['all_content']:
        all_facts.extend(extract_facts(content, source))
    
    print("Detecting duplicates...")
    duplicates = detect_duplicates(all_facts)
    
    print("Detecting stale content...")
    stale = detect_stale_facts(all_facts)
    
    print("Calculating health score...")
    health_score = calculate_health_score(stats, duplicates, stale)
    
    print("Storing snapshot...")
    store_health_snapshot(stats, duplicates, stale, health_score)
    
    return {
        'health_score': health_score,
        'total_files': stats['total_files'],
        'total_lines': stats['total_lines'],
        'total_size_kb': round(stats['total_size_kb'], 2),
        'memory_md_lines': stats['memory_md_lines'],
        'daily_files': len(stats['daily_files']),
        'oldest_daily': stats['oldest_daily'],
        'newest_daily': stats['newest_daily'],
        'duplicates': len(duplicates),
        'duplicate_details': duplicates[:5],  # Top 5
        'stale_count': len(stale),
        'stale_details': stale[:5],  # Top 5
        'timestamp': datetime.now().isoformat()
    }

def get_latest_health():
    """Get the latest health snapshot."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM health_snapshots ORDER BY timestamp DESC LIMIT 1')
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            'timestamp': row[1],
            'total_files': row[2],
            'total_lines': row[3],
            'total_size_kb': row[4],
            'memory_md_lines': row[5],
            'memory_md_size_kb': row[6],
            'oldest_daily': row[7],
            'newest_daily': row[8],
            'days_with_notes': row[9],
            'avg_lines_per_day': row[10],
            'duplicates': row[11],
            'stale_count': row[12],
            'health_score': row[14]
        }
    return None

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: scanner.py <command>")
        print("Commands:")
        print("  scan     - Run full health scan")
        print("  latest   - Show latest health snapshot")
        print("  json     - Output latest as JSON (for API)")
        print("  retrieval - Show retrieval stats")
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'scan':
        result = run_full_scan()
        print(f"\n=== Memory Health Report ===")
        print(f"Health Score: {result['health_score']}/100")
        print(f"Total Files: {result['total_files']}")
        print(f"Total Lines: {result['total_lines']}")
        print(f"MEMORY.md: {result['memory_md_lines']} lines")
        print(f"Daily Files: {result['daily_files']} ({result['oldest_daily']} to {result['newest_daily']})")
        print(f"Potential Duplicates: {result['duplicates']}")
        print(f"Stale Facts: {result['stale_count']}")
        
        if result['duplicate_details']:
            print(f"\nTop Duplicates:")
            for d in result['duplicate_details'][:3]:
                print(f"  - '{d['sample']}...' ({d['count']}x)")
        
        if result['stale_details']:
            print(f"\nStale Content:")
            for s in result['stale_details'][:3]:
                print(f"  - {s['source']}:{s['line']} ({s['age_days']}d old)")
    
    elif cmd == 'latest':
        health = get_latest_health()
        if health:
            print(json.dumps(health, indent=2))
        else:
            print("No health data yet. Run 'scan' first.")
    
    elif cmd == 'json':
        init_db()
        health = get_latest_health()
        retrieval = get_retrieval_stats()
        print(json.dumps({
            'health': health,
            'retrieval': retrieval
        }))
    
    elif cmd == 'retrieval':
        init_db()
        stats = get_retrieval_stats()
        print(json.dumps(stats, indent=2))
    
    else:
        print(f"Unknown command: {cmd}")

if __name__ == '__main__':
    main()
