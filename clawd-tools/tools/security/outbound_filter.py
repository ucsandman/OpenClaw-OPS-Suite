#!/usr/bin/env python3
"""
Outbound Filter - Scan content for sensitive data before external transmission.
Catches API keys, file paths, personal info, secrets before they leak.

Part of the AgentForge Toolkit by Practical Systems.
"""

import sys
import re
import json
from pathlib import Path
from datetime import datetime
import argparse

# Fix Windows Unicode encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Sensitive patterns to detect
PATTERNS = {
    'api_key': [
        r'sk-[a-zA-Z0-9]{20,}',  # OpenAI
        r'sk_live_[a-zA-Z0-9]+',  # Stripe live
        r'sk_test_[a-zA-Z0-9]+',  # Stripe test
        r'ghp_[a-zA-Z0-9]{36}',  # GitHub PAT
        r'gho_[a-zA-Z0-9]{36}',  # GitHub OAuth
        r'xoxb-[a-zA-Z0-9-]+',  # Slack bot
        r'xoxp-[a-zA-Z0-9-]+',  # Slack user
        r'Bearer\s+[a-zA-Z0-9_\-\.=]+',  # Bearer tokens (including JWT with =)
        r'api[_-]?key["\s:=]+[a-zA-Z0-9_\-]{16,}',  # Generic API key
        r'ANTHROPIC[_-]?API[_-]?KEY',  # Anthropic
        r'moltbook_sk_[a-zA-Z0-9_\-]+',  # Moltbook
        r'AKIA[0-9A-Z]{16}',  # AWS Access Key ID
        r'AIza[0-9A-Za-z\-_]{35}',  # Google Cloud API Key
        r'[MN][A-Za-z\d]{23,}\.[A-Za-z\d_-]{6}\.[A-Za-z\d_-]{27}',  # Discord Token
        r'npm_[A-Za-z0-9]{36}',  # npm Token
        r'SK[a-f0-9]{32}',  # Twilio API Key
        r'SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}',  # SendGrid API Key
        r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*',  # JWT Token
    ],
    'file_path': [
        r'C:\\Users\\[a-zA-Z0-9_]+\\[^\s"\']+',  # Windows paths
        r'/Users/[a-zA-Z0-9_]+/[^\s"\']+',  # Mac paths
        r'/home/[a-zA-Z0-9_]+/[^\s"\']+',  # Linux paths
        r'\\\\[a-zA-Z0-9]+\\[^\s"\']+',  # UNC paths
    ],
    'database_url': [
        r'postgres://[^\s"\']+',
        r'postgresql://[^\s"\']+',
        r'mysql://[^\s"\']+',
        r'mongodb://[^\s"\']+',
        r'redis://[^\s"\']+',
    ],
    'personal_info': [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN with dashes
        r'\b\d{9}\b',  # SSN without dashes (9 digits)
        r'\b\d{16}\b',  # Credit card 16 digits
        r'\b\d{15}\b',  # Credit card 15 digits (Amex)
        r'\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b',  # Credit card with spaces/dashes
        r'\b\d{4}[\s-]\d{6}[\s-]\d{5}\b',  # Amex with spaces/dashes
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # Phone number (US)
        r'\+\d{1,3}[-.\s]?\d{1,14}\b',  # International phone
    ],
    'internal_reference': [
        r'MEMORY\.md',  # Memory file references
        r'memory/\d{4}-\d{2}-\d{2}\.md',  # Daily memory files
        r'secrets/',  # Secrets folder
        r'\.env',  # Env files
        r'oauth\.json',  # OAuth credentials
    ],
    'ip_address': [
        r'\b(?:192\.168|10\.|172\.(?:1[6-9]|2[0-9]|3[01]))\.\d{1,3}\.\d{1,3}\b',  # Private IPs
    ]
}

# Severity levels
SEVERITY = {
    'api_key': 'CRITICAL',
    'database_url': 'CRITICAL',
    'file_path': 'HIGH',
    'personal_info': 'HIGH',
    'internal_reference': 'MEDIUM',
    'ip_address': 'LOW'
}

# Allowlist - patterns that look sensitive but are OK
# SECURITY: DO NOT allowlist URLs - secrets can be embedded in query strings!
ALLOWLIST = [
    r'example\.com',
    r'placeholder',
    r'your-api-key-here',
    r'xxx+',  # Redacted/placeholder patterns
    r'\*{3,}',  # Masked patterns like ****
]

FINDINGS_LOG = Path(__file__).parent / "outbound_findings.json"

def load_findings():
    """Load historical findings."""
    if FINDINGS_LOG.exists():
        return json.loads(FINDINGS_LOG.read_text())
    return []

def save_finding(finding):
    """Save a finding to history."""
    findings = load_findings()
    findings.append(finding)
    # Keep last 1000 findings
    findings = findings[-1000:]
    FINDINGS_LOG.write_text(json.dumps(findings, indent=2))

def is_allowlisted(text: str, match: str) -> bool:
    """Check if a match is allowlisted."""
    for pattern in ALLOWLIST:
        if re.search(pattern, match, re.IGNORECASE):
            return True
    return False

def scan(content: str, context: str = None) -> dict:
    """
    Scan content for sensitive data.
    
    Returns:
        dict with 'safe', 'findings', and 'redacted' keys
    """
    findings = []
    redacted = content
    
    for category, patterns in PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                matched_text = match.group()
                
                # Skip allowlisted
                if is_allowlisted(content, matched_text):
                    continue
                
                finding = {
                    'category': category,
                    'severity': SEVERITY.get(category, 'MEDIUM'),
                    'pattern': pattern,
                    'match': matched_text[:50] + ('...' if len(matched_text) > 50 else ''),
                    'position': match.start(),
                    'context': context,
                    'timestamp': datetime.now().isoformat()
                }
                findings.append(finding)
                
                # Redact in output
                redacted = redacted.replace(matched_text, f'[REDACTED-{category.upper()}]')
    
    # Determine if safe to send
    critical_findings = [f for f in findings if f['severity'] == 'CRITICAL']
    high_findings = [f for f in findings if f['severity'] == 'HIGH']
    
    safe = len(critical_findings) == 0 and len(high_findings) == 0
    
    result = {
        'safe': safe,
        'findings': findings,
        'redacted': redacted,
        'summary': {
            'total': len(findings),
            'critical': len(critical_findings),
            'high': len(high_findings),
            'medium': len([f for f in findings if f['severity'] == 'MEDIUM']),
            'low': len([f for f in findings if f['severity'] == 'LOW'])
        }
    }
    
    # Log findings
    if findings:
        for f in findings:
            save_finding(f)
    
    return result

def check_before_send(content: str, destination: str = None) -> bool:
    """
    Quick check before sending content externally.
    Returns True if safe, False if blocked.
    Prints warnings.
    """
    result = scan(content, context=destination)
    
    if not result['safe']:
        print(f"\n[!!] OUTBOUND BLOCKED - Sensitive data detected!")
        print(f"   Destination: {destination or 'unknown'}")
        print(f"   Findings: {result['summary']}")
        for f in result['findings']:
            if f['severity'] in ('CRITICAL', 'HIGH'):
                print(f"   [!]  [{f['severity']}] {f['category']}: {f['match']}")
        return False
    
    if result['findings']:
        print(f"[!]  Low-risk items detected (allowed): {result['summary']}")
    
    return True

def get_findings_report(days: int = 7):
    """Get a report of recent findings."""
    findings = load_findings()
    
    # Filter by date
    cutoff = datetime.now().timestamp() - (days * 86400)
    recent = [f for f in findings if datetime.fromisoformat(f['timestamp']).timestamp() > cutoff]
    
    # Aggregate
    by_category = {}
    by_severity = {}
    
    for f in recent:
        cat = f['category']
        sev = f['severity']
        by_category[cat] = by_category.get(cat, 0) + 1
        by_severity[sev] = by_severity.get(sev, 0) + 1
    
    return {
        'total': len(recent),
        'by_category': by_category,
        'by_severity': by_severity,
        'period_days': days
    }

def main():
    parser = argparse.ArgumentParser(description='Outbound Filter - Scan for sensitive data')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan text for sensitive data')
    scan_parser.add_argument('text', nargs='?', help='Text to scan (or use --file)')
    scan_parser.add_argument('--file', '-f', help='File to scan')
    scan_parser.add_argument('--context', '-c', help='Context/destination')
    
    # Check command (quick safe/unsafe)
    check_parser = subparsers.add_parser('check', help='Quick safety check')
    check_parser.add_argument('text', help='Text to check')
    check_parser.add_argument('--dest', '-d', help='Destination')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Show findings report')
    report_parser.add_argument('--days', '-d', type=int, default=7)
    
    # Test command
    subparsers.add_parser('test', help='Run test patterns')
    
    args = parser.parse_args()
    
    if args.command == 'scan':
        if args.file:
            content = Path(args.file).read_text()
        elif args.text:
            content = args.text
        else:
            print("Provide text or --file")
            return
        
        result = scan(content, args.context)
        
        print(f"\n{'[OK] SAFE' if result['safe'] else '[!!] UNSAFE'}")
        print(f"Summary: {result['summary']}")
        
        if result['findings']:
            print("\nFindings:")
            for f in result['findings']:
                print(f"  [{f['severity']}] {f['category']}: {f['match']}")
    
    elif args.command == 'check':
        safe = check_before_send(args.text, args.dest)
        exit(0 if safe else 1)
    
    elif args.command == 'report':
        report = get_findings_report(args.days)
        print(f"\n[#] Outbound Filter Report (last {report['period_days']} days)")
        print(f"   Total findings: {report['total']}")
        print(f"\n   By Severity:")
        for sev, count in report['by_severity'].items():
            print(f"      {sev}: {count}")
        print(f"\n   By Category:")
        for cat, count in report['by_category'].items():
            print(f"      {cat}: {count}")
    
    elif args.command == 'test':
        test_strings = [
            "My API key is sk-1234567890abcdefghijklmnop",
            "Check C:\\Users\\sandm\\clawd\\secrets\\api.key",
            "Database: postgres://user:pass@localhost/db",
            "Call me at 123-45-6789",
            "This is safe text with no secrets",
            "Visit https://example.com for more info",
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        ]
        
        print("Running test patterns:\n")
        for test in test_strings:
            result = scan(test)
            status = "[OK] SAFE" if result['safe'] else "[!!] BLOCKED"
            print(f"{status}: {test[:50]}...")
            if result['findings']:
                for f in result['findings']:
                    print(f"   → [{f['severity']}] {f['category']}")
            print()
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
