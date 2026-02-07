#!/usr/bin/env python3
"""
Session Isolation Enforcer - Ensure sensitive data stays in appropriate contexts.
Prevents MEMORY.md and personal files from leaking to group chats.
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
import argparse

# Fix Windows Unicode encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

CONFIG_FILE = Path(__file__).parent / "session_config.json"
VIOLATIONS_LOG = Path(__file__).parent / "isolation_violations.json"

# Session types and their allowed data access
SESSION_TYPES = {
    'main': {
        'description': 'Direct 1:1 chat with Wes',
        'allowed_files': ['*'],  # Everything allowed
        'allowed_classifications': ['SECRET', 'CONFIDENTIAL', 'INTERNAL', 'PUBLIC'],
        'can_write_memory': True
    },
    'group_chat': {
        'description': 'Group conversations (Discord, etc)',
        'allowed_files': ['AGENTS.md', 'SOUL.md', 'TOOLS.md', 'docs/*', 'skills/*'],
        'blocked_files': [
            'MEMORY.md', 'memory/*', 'USER.md', 'secrets/*',
            '*.env', '*.env.*', '.env*',  # All env file variations
            'credentials.json', 'oauth.json', '*.key', '*.pem',
            '*.bak', '*.backup', 'id_rsa*', 'id_ed25519*'
        ],
        'allowed_classifications': ['INTERNAL', 'PUBLIC'],
        'can_write_memory': False
    },
    'public': {
        'description': 'Public posts/content',
        'allowed_files': ['docs/*', 'README.md'],
        'blocked_files': ['*'],  # Block everything by default
        'allowed_classifications': ['PUBLIC'],
        'can_write_memory': False
    },
    'sub_agent': {
        'description': 'Spawned sub-agent sessions',
        'allowed_files': ['AGENTS.md', 'TOOLS.md', 'tools/*', 'projects/*'],
        'blocked_files': [
            'MEMORY.md', 'USER.md', 'secrets/*',
            '*.env', '*.env.*', '.env*',
            'credentials.json', 'oauth.json'
        ],
        'allowed_classifications': ['INTERNAL', 'PUBLIC'],
        'can_write_memory': True  # Can write to daily files
    }
}

def load_config():
    """Load session config."""
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {
        'session_types': SESSION_TYPES,
        'current_session': 'main',
        'enforcement_mode': 'block'  # 'warn', 'block', 'log_only' - SECURITY: default to block
    }

def save_config(config):
    """Save config."""
    CONFIG_FILE.write_text(json.dumps(config, indent=2))

def log_violation(violation):
    """Log a security violation."""
    violations = []
    if VIOLATIONS_LOG.exists():
        violations = json.loads(VIOLATIONS_LOG.read_text())
    
    violation['timestamp'] = datetime.now().isoformat()
    violations.append(violation)
    
    # Keep last 500 violations
    violations = violations[-500:]
    VIOLATIONS_LOG.write_text(json.dumps(violations, indent=2))

def detect_session_type(env_hints: dict = None) -> str:
    """
    Detect current session type from environment hints.
    """
    if env_hints is None:
        env_hints = {}
    
    # Check for channel info
    channel = env_hints.get('channel', os.environ.get('CLAWDBOT_CHANNEL', ''))
    session_key = env_hints.get('session_key', os.environ.get('SESSION_KEY', ''))
    
    # Detect based on session key pattern
    if 'agent:main:main' in session_key:
        return 'main'
    elif ':discord:' in session_key or ':slack:' in session_key:
        # Could be DM or group - check further
        if env_hints.get('is_dm', False):
            return 'main'  # Treat DMs as main for now
        return 'group_chat'
    elif 'sub-agent' in session_key or 'spawn' in session_key:
        return 'sub_agent'
    
    # SECURITY: Default to most restrictive mode when session type is unclear
    # This prevents accidental data leakage in ambiguous contexts
    return 'public'

def can_access_file(filepath: str, session_type: str = None) -> dict:
    """
    Check if current session can access a file.
    Returns dict with 'allowed', 'reason', 'session_type'.
    """
    config = load_config()
    
    if session_type is None:
        session_type = config.get('current_session', 'main')
    
    type_config = config['session_types'].get(session_type, SESSION_TYPES.get(session_type))
    if not type_config:
        # SECURITY: Deny access for unknown session types (fail-closed)
        return {'allowed': False, 'reason': 'Unknown session type - access denied for security', 'session_type': session_type}
    
    filepath = str(Path(filepath))
    filename = Path(filepath).name
    
    # Check blocked files first
    blocked = type_config.get('blocked_files', [])
    for pattern in blocked:
        if pattern == '*':
            # Check if in allowed list
            allowed = type_config.get('allowed_files', [])
            if not any(_matches(filepath, a) for a in allowed):
                return {
                    'allowed': False,
                    'reason': f'File blocked in {session_type} session (not in allowlist)',
                    'session_type': session_type
                }
        elif _matches(filepath, pattern) or _matches(filename, pattern):
            return {
                'allowed': False,
                'reason': f'File matches blocked pattern: {pattern}',
                'session_type': session_type
            }
    
    # Check allowed files
    allowed = type_config.get('allowed_files', ['*'])
    if '*' in allowed:
        return {'allowed': True, 'reason': 'All files allowed', 'session_type': session_type}
    
    for pattern in allowed:
        if _matches(filepath, pattern) or _matches(filename, pattern):
            return {'allowed': True, 'reason': f'Matches allowed pattern: {pattern}', 'session_type': session_type}
    
    # Not explicitly allowed
    return {
        'allowed': False,
        'reason': f'File not in allowed list for {session_type}',
        'session_type': session_type
    }

def _matches(path: str, pattern: str) -> bool:
    """Simple glob-like matching."""
    import fnmatch
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(Path(path).name, pattern)

def check_file_access(filepath: str, session_type: str = None, action: str = 'read'):
    """
    Check and potentially block file access.
    Call this before reading sensitive files.
    """
    config = load_config()
    mode = config.get('enforcement_mode', 'warn')
    
    result = can_access_file(filepath, session_type)
    
    if not result['allowed']:
        violation = {
            'file': filepath,
            'session_type': result['session_type'],
            'action': action,
            'reason': result['reason'],
            'blocked': mode == 'block'
        }
        log_violation(violation)
        
        if mode == 'block':
            raise PermissionError(f"[*] BLOCKED: {result['reason']}")
        elif mode == 'warn':
            print(f"[!]  WARNING: {result['reason']}")
            print(f"   File: {filepath}")
            print(f"   Session: {result['session_type']}")
    
    return result

def set_session_type(session_type: str):
    """Set current session type."""
    config = load_config()
    if session_type not in SESSION_TYPES:
        raise ValueError(f"Unknown session type: {session_type}")
    
    config['current_session'] = session_type
    save_config(config)
    print(f"[OK] Session type set to: {session_type}")

def set_enforcement_mode(mode: str):
    """Set enforcement mode."""
    config = load_config()
    if mode not in ('warn', 'block', 'log_only'):
        raise ValueError(f"Invalid mode: {mode}")
    
    config['enforcement_mode'] = mode
    save_config(config)
    print(f"[OK] Enforcement mode set to: {mode}")

def get_violations(limit: int = 20):
    """Get recent violations."""
    if not VIOLATIONS_LOG.exists():
        return []
    violations = json.loads(VIOLATIONS_LOG.read_text())
    return violations[-limit:]

def verify_isolation():
    """
    Run isolation verification checks.
    Returns list of issues found.
    """
    issues = []
    config = load_config()
    current = config.get('current_session', 'main')
    
    # Check if MEMORY.md loaded in wrong context
    if current != 'main':
        memory_path = Path('MEMORY.md')
        if memory_path.exists():
            result = can_access_file('MEMORY.md', current)
            if not result['allowed']:
                issues.append({
                    'severity': 'HIGH',
                    'issue': 'MEMORY.md should not be loaded in this session type',
                    'session_type': current
                })
    
    # Check USER.md
    if current in ('group_chat', 'public'):
        user_path = Path('USER.md')
        if user_path.exists():
            result = can_access_file('USER.md', current)
            if not result['allowed']:
                issues.append({
                    'severity': 'HIGH', 
                    'issue': 'USER.md should not be loaded in group/public sessions',
                    'session_type': current
                })
    
    return issues

def main():
    parser = argparse.ArgumentParser(description='Session Isolation Enforcer')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check file access')
    check_parser.add_argument('file', help='File to check')
    check_parser.add_argument('--session', '-s', choices=list(SESSION_TYPES.keys()))
    
    # Set session command
    session_parser = subparsers.add_parser('session', help='Set session type')
    session_parser.add_argument('type', choices=list(SESSION_TYPES.keys()))
    
    # Mode command
    mode_parser = subparsers.add_parser('mode', help='Set enforcement mode')
    mode_parser.add_argument('mode', choices=['warn', 'block', 'log_only'])
    
    # Violations command
    violations_parser = subparsers.add_parser('violations', help='Show violations')
    violations_parser.add_argument('--limit', '-l', type=int, default=20)
    
    # Verify command
    subparsers.add_parser('verify', help='Verify current isolation')
    
    # Status command
    subparsers.add_parser('status', help='Show current status')
    
    # Types command
    subparsers.add_parser('types', help='Show session types')
    
    args = parser.parse_args()
    
    if args.command == 'check':
        result = can_access_file(args.file, args.session)
        if result['allowed']:
            print(f"[OK] Access allowed: {args.file}")
        else:
            print(f"[*] Access denied: {args.file}")
        print(f"   Reason: {result['reason']}")
        print(f"   Session: {result['session_type']}")
    
    elif args.command == 'session':
        set_session_type(args.type)
    
    elif args.command == 'mode':
        set_enforcement_mode(args.mode)
    
    elif args.command == 'violations':
        violations = get_violations(args.limit)
        if not violations:
            print("No violations recorded.")
            return
        
        print(f"\nRecent violations ({len(violations)}):\n")
        for v in violations:
            blocked = "BLOCKED" if v.get('blocked') else "WARNING"
            print(f"[{blocked}] {v['timestamp'][:16]}")
            print(f"   File: {v['file']}")
            print(f"   Session: {v['session_type']}")
            print(f"   Reason: {v['reason']}")
            print()
    
    elif args.command == 'verify':
        issues = verify_isolation()
        if not issues:
            print("[OK] Isolation verified - no issues found")
        else:
            print(f"[!]  Found {len(issues)} isolation issues:")
            for i in issues:
                print(f"   [{i['severity']}] {i['issue']}")
    
    elif args.command == 'status':
        config = load_config()
        print(f"\n[#] Session Isolation Status")
        print(f"   Current session: {config.get('current_session', 'main')}")
        print(f"   Enforcement mode: {config.get('enforcement_mode', 'warn')}")
        
        violations = get_violations(5)
        print(f"   Recent violations: {len(violations)}")
    
    elif args.command == 'types':
        print("\n[#] Session Types:\n")
        for name, info in SESSION_TYPES.items():
            print(f"  {name}")
            print(f"    {info['description']}")
            print(f"    Write memory: {'Yes' if info['can_write_memory'] else 'No'}")
            print(f"    Blocked: {info.get('blocked_files', [])}")
            print()
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
