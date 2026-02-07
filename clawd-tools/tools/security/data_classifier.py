#!/usr/bin/env python3
"""
Data Classification - Tag files and content as sensitive/internal/public.
Enforces handling rules based on classification.
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime
import argparse
import fnmatch

# Fix Windows Unicode encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

CLASSIFICATION_FILE = Path(__file__).parent / "classifications.json"

# Classification levels (highest to lowest sensitivity)
LEVELS = {
    'SECRET': {
        'level': 4,
        'color': '[RED]',
        'description': 'Highly sensitive - API keys, passwords, credentials',
        'rules': ['never_share', 'encrypt_at_rest', 'no_logs']
    },
    'CONFIDENTIAL': {
        'level': 3,
        'color': '[ORANGE]',
        'description': 'Personal/private - memory files, personal notes',
        'rules': ['no_group_chats', 'no_public_posts', 'audit_access']
    },
    'INTERNAL': {
        'level': 2,
        'color': '[YELLOW]',
        'description': 'Internal use - code, configs, project files',
        'rules': ['sanitize_before_share', 'check_for_secrets']
    },
    'PUBLIC': {
        'level': 1,
        'color': '[GREEN]',
        'description': 'Safe to share - public docs, open source',
        'rules': []
    }
}

# Default classifications by pattern
DEFAULT_PATTERNS = {
    'SECRET': [
        'secrets/*',
        '*.env',
        '.env*',
        '**/oauth*.json',
        '**/credentials*.json',
        '**/api_key*',
        '**/*_secret*',
    ],
    'CONFIDENTIAL': [
        'MEMORY.md',
        'memory/*.md',
        'USER.md',
        'SOUL.md',
        '**/relationships*',
        '**/personal/*',
        '**/*private*',
    ],
    'INTERNAL': [
        'AGENTS.md',
        'TOOLS.md',
        'HEARTBEAT.md',
        'tools/**',
        'projects/*',
        '*.py',
        '*.js',
        '*.ts',
    ],
    'PUBLIC': [
        'README.md',
        'LICENSE*',
        'docs/*',
        '*.txt',
    ]
}

def load_classifications():
    """Load custom classifications."""
    if CLASSIFICATION_FILE.exists():
        return json.loads(CLASSIFICATION_FILE.read_text())
    return {'files': {}, 'patterns': DEFAULT_PATTERNS}

def save_classifications(data):
    """Save classifications."""
    CLASSIFICATION_FILE.write_text(json.dumps(data, indent=2))

def classify_file(filepath: str, level: str = None) -> str:
    """
    Get or set classification for a file.
    Returns the classification level.
    """
    data = load_classifications()
    filepath = str(Path(filepath).resolve())
    
    if level:
        # Set classification
        if level not in LEVELS:
            raise ValueError(f"Invalid level: {level}. Use: {list(LEVELS.keys())}")
        data['files'][filepath] = {
            'level': level,
            'set_date': datetime.now().isoformat(),
            'auto': False
        }
        save_classifications(data)
        return level
    
    # Get classification
    if filepath in data['files']:
        return data['files'][filepath]['level']
    
    # Check patterns
    for level_name, patterns in data.get('patterns', DEFAULT_PATTERNS).items():
        for pattern in patterns:
            if fnmatch.fnmatch(filepath, pattern) or fnmatch.fnmatch(Path(filepath).name, pattern):
                return level_name
    
    # Default to INTERNAL
    return 'INTERNAL'

def check_content(content: str) -> dict:
    """
    Analyze content to suggest classification.
    """
    indicators = {
        'SECRET': 0,
        'CONFIDENTIAL': 0,
        'INTERNAL': 0,
        'PUBLIC': 0
    }
    
    # Secret indicators
    secret_patterns = [
        r'api[_-]?key', r'password', r'secret', r'token',
        r'sk-[a-zA-Z0-9]+', r'Bearer ', r'credential'
    ]
    for pattern in secret_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            indicators['SECRET'] += 2
    
    # Confidential indicators
    conf_patterns = [
        r'personal', r'private', r'memory', r'diary',
        r'@[a-zA-Z]+\.(com|org|net)', r'phone', r'address'
    ]
    for pattern in conf_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            indicators['CONFIDENTIAL'] += 1
    
    # Internal indicators
    internal_patterns = [
        r'TODO', r'FIXME', r'internal', r'def ', r'function',
        r'import ', r'require\('
    ]
    for pattern in internal_patterns:
        if re.search(pattern, content):
            indicators['INTERNAL'] += 1
    
    # Public indicators
    public_patterns = [
        r'MIT License', r'Apache License', r'public domain',
        r'documentation', r'README'
    ]
    for pattern in public_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            indicators['PUBLIC'] += 1
    
    # Determine suggested level
    max_level = max(indicators.items(), key=lambda x: x[1])
    
    return {
        'suggested': max_level[0] if max_level[1] > 0 else 'INTERNAL',
        'confidence': min(max_level[1] * 20, 100),
        'indicators': indicators
    }

def can_share(filepath: str, context: str) -> dict:
    """
    Check if a file can be shared in a given context.
    Contexts: 'public', 'group_chat', 'direct_message', 'internal'
    """
    level = classify_file(filepath)
    level_info = LEVELS[level]
    rules = level_info['rules']
    
    allowed = True
    warnings = []
    
    if context == 'public':
        if level in ('SECRET', 'CONFIDENTIAL', 'INTERNAL'):
            allowed = False
            warnings.append(f"Cannot share {level} files publicly")
    
    elif context == 'group_chat':
        if 'no_group_chats' in rules:
            allowed = False
            warnings.append(f"Cannot share {level} files in group chats")
        if level == 'SECRET':
            allowed = False
            warnings.append("SECRET files cannot be shared")
    
    elif context == 'direct_message':
        if level == 'SECRET':
            allowed = False
            warnings.append("SECRET files should not be shared even in DMs")
        if 'sanitize_before_share' in rules:
            warnings.append("Should sanitize before sharing")
    
    return {
        'allowed': allowed,
        'level': level,
        'level_info': level_info,
        'warnings': warnings
    }

def list_by_level(level: str = None, directory: str = '.'):
    """List files by classification level."""
    data = load_classifications()
    results = {}
    
    for f in Path(directory).rglob('*'):
        if f.is_file():
            file_level = classify_file(str(f))
            if level is None or file_level == level:
                if file_level not in results:
                    results[file_level] = []
                results[file_level].append(str(f.relative_to(directory)))
    
    return results

def add_pattern(level: str, pattern: str):
    """Add a classification pattern."""
    data = load_classifications()
    if 'patterns' not in data:
        data['patterns'] = DEFAULT_PATTERNS.copy()
    
    if level not in data['patterns']:
        data['patterns'][level] = []
    
    if pattern not in data['patterns'][level]:
        data['patterns'][level].append(pattern)
        save_classifications(data)
        print(f"[OK] Added pattern '{pattern}' to {level}")
    else:
        print(f"Pattern already exists in {level}")

def main():
    parser = argparse.ArgumentParser(description='Data Classification Tool')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Classify command
    classify_parser = subparsers.add_parser('classify', help='Get/set file classification')
    classify_parser.add_argument('file', help='File path')
    classify_parser.add_argument('--level', '-l', choices=list(LEVELS.keys()), help='Set level')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check if can share')
    check_parser.add_argument('file', help='File path')
    check_parser.add_argument('--context', '-c', required=True,
                             choices=['public', 'group_chat', 'direct_message', 'internal'])
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze content classification')
    analyze_parser.add_argument('file', help='File to analyze')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List files by classification')
    list_parser.add_argument('--level', '-l', choices=list(LEVELS.keys()))
    list_parser.add_argument('--dir', '-d', default='.', help='Directory to scan')
    
    # Pattern command
    pattern_parser = subparsers.add_parser('pattern', help='Add classification pattern')
    pattern_parser.add_argument('level', choices=list(LEVELS.keys()))
    pattern_parser.add_argument('pattern', help='Glob pattern')
    
    # Levels command
    subparsers.add_parser('levels', help='Show classification levels')
    
    args = parser.parse_args()
    
    if args.command == 'classify':
        level = classify_file(args.file, args.level)
        info = LEVELS[level]
        print(f"{info['color']} {args.file}: {level}")
        print(f"   {info['description']}")
        if info['rules']:
            print(f"   Rules: {', '.join(info['rules'])}")
    
    elif args.command == 'check':
        result = can_share(args.file, args.context)
        if result['allowed']:
            print(f"[OK] Can share '{args.file}' in {args.context}")
        else:
            print(f"[*] Cannot share '{args.file}' in {args.context}")
        
        for w in result['warnings']:
            print(f"   [!]  {w}")
    
    elif args.command == 'analyze':
        content = Path(args.file).read_text()
        result = check_content(content)
        print(f"\nAnalysis of '{args.file}':")
        print(f"  Suggested: {result['suggested']} (confidence: {result['confidence']}%)")
        print(f"  Indicators: {result['indicators']}")
    
    elif args.command == 'list':
        results = list_by_level(args.level, args.dir)
        for level, files in sorted(results.items(), key=lambda x: LEVELS[x[0]]['level'], reverse=True):
            info = LEVELS[level]
            print(f"\n{info['color']} {level} ({len(files)} files):")
            for f in files[:10]:
                print(f"   {f}")
            if len(files) > 10:
                print(f"   ... and {len(files) - 10} more")
    
    elif args.command == 'pattern':
        add_pattern(args.level, args.pattern)
    
    elif args.command == 'levels':
        print("\n[#] Classification Levels:\n")
        for name, info in sorted(LEVELS.items(), key=lambda x: x[1]['level'], reverse=True):
            print(f"{info['color']} {name}")
            print(f"   {info['description']}")
            if info['rules']:
                print(f"   Rules: {', '.join(info['rules'])}")
            print()
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
