#!/usr/bin/env python3
"""
AgentForge Memory Search
Semantic and keyword search across all memory files.

Usage:
    python search.py "query"
    python search.py "query" --file MEMORY.md
    python search.py "query" --recent 7  # Last 7 days
    python search.py recent  # Show recent entries
    python search.py files  # List all memory files
"""

import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent.parent
MEMORY_DIR = WORKSPACE / "memory"

def get_memory_files():
    """Get all memory files."""
    files = []
    
    # Main memory file
    main = WORKSPACE / "MEMORY.md"
    if main.exists():
        files.append(main)
    
    # Daily memory files
    if MEMORY_DIR.exists():
        for f in sorted(MEMORY_DIR.glob("*.md"), reverse=True):
            files.append(f)
    
    # Other key files
    for name in ["SOUL.md", "USER.md", "AGENTS.md", "TOOLS.md", "HEARTBEAT.md"]:
        f = WORKSPACE / name
        if f.exists():
            files.append(f)
    
    return files

def search_files(query, files=None, recent_days=None, context_lines=2):
    """Search for query across memory files."""
    if files is None:
        files = get_memory_files()
    
    # Filter by recency if specified
    if recent_days:
        cutoff = datetime.now() - timedelta(days=recent_days)
        files = [f for f in files if is_recent(f, cutoff)]
    
    results = []
    query_lower = query.lower()
    query_words = query_lower.split()
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                
                # Check if any query word matches
                if any(word in line_lower for word in query_words):
                    # Get context
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    context = ''.join(lines[start:end])
                    
                    # Calculate relevance score
                    score = sum(1 for word in query_words if word in line_lower)
                    
                    results.append({
                        'file': filepath.name,
                        'path': str(filepath),
                        'line': i + 1,
                        'match': line.strip(),
                        'context': context.strip(),
                        'score': score
                    })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    # Sort by relevance
    results.sort(key=lambda x: -x['score'])
    
    return results

def is_recent(filepath, cutoff):
    """Check if a file is recent based on name or modification time."""
    # Check filename for date pattern (YYYY-MM-DD)
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filepath.name)
    if match:
        try:
            file_date = datetime.strptime(match.group(1), '%Y-%m-%d')
            return file_date >= cutoff
        except:
            pass
    
    # Fall back to modification time
    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
    return mtime >= cutoff

def safe_print(text):
    """Print text, handling encoding issues on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', 'replace').decode('ascii'))

def display_results(results, limit=20, show_context=True):
    """Display search results."""
    if not results:
        print("\nNo results found.")
        return
    
    print(f"\n{'='*60}")
    print(f"SEARCH RESULTS ({len(results)} matches)")
    print(f"{'='*60}")
    
    for i, r in enumerate(results[:limit]):
        safe_print(f"\n[{r['score']}] {r['file']}:{r['line']}")
        match_text = r['match'][:70] + ('...' if len(r['match']) > 70 else '')
        safe_print(f"  {match_text}")
        
        if show_context and len(r['context']) > len(r['match']):
            print(f"\n  Context:")
            for line in r['context'].split('\n')[:5]:
                if line.strip():
                    safe_print(f"    {line[:60]}...")
    
    if len(results) > limit:
        print(f"\n  ... and {len(results) - limit} more results")

def show_recent_entries(days=7):
    """Show recent memory entries."""
    files = get_memory_files()
    cutoff = datetime.now() - timedelta(days=days)
    recent = [f for f in files if is_recent(f, cutoff)]
    
    print(f"\n{'='*60}")
    print(f"RECENT MEMORY FILES (last {days} days)")
    print(f"{'='*60}")
    
    for f in recent:
        # Get first few non-header lines as preview
        try:
            with open(f, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            preview = ""
            for line in lines[1:10]:
                if line.strip() and not line.startswith('#'):
                    preview = line.strip()[:50]
                    break
            
            print(f"\n  > {f.name}")
            if preview:
                print(f"    {preview}...")
        except:
            print(f"\n  > {f.name}")

def list_files():
    """List all memory files."""
    files = get_memory_files()
    
    print(f"\n{'='*60}")
    print(f"MEMORY FILES ({len(files)})")
    print(f"{'='*60}")
    
    for f in files:
        size = f.stat().st_size
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        print(f"  {f.name:<30} {size:>8} bytes  {mtime.strftime('%Y-%m-%d')}")

def main():
    parser = argparse.ArgumentParser(description='AgentForge Memory Search')
    parser.add_argument('query', nargs='?', help='Search query')
    parser.add_argument('--file', '-f', help='Search specific file only')
    parser.add_argument('--recent', '-r', type=int, help='Only search recent N days')
    parser.add_argument('--limit', '-l', type=int, default=20, help='Max results')
    parser.add_argument('--no-context', action='store_true', help='Hide context')
    
    args = parser.parse_args()
    
    if args.query == 'recent':
        show_recent_entries()
    elif args.query == 'files':
        list_files()
    elif args.query:
        # Filter to specific file if requested
        files = None
        if args.file:
            target = WORKSPACE / args.file
            if target.exists():
                files = [target]
            else:
                # Try memory directory
                target = MEMORY_DIR / args.file
                if target.exists():
                    files = [target]
                else:
                    print(f"File not found: {args.file}")
                    return
        
        results = search_files(args.query, files, args.recent)
        display_results(results, args.limit, not args.no_context)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
