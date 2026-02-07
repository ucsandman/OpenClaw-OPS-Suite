#!/usr/bin/env python3
"""
Context Manager for Token Efficiency
Handles automatic summarization and context cleanup.

Part of the AgentForge Toolkit by Practical Systems.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def get_default_memory_dir():
    """Get default memory directory, respecting AGENTFORGE_MEMORY env var."""
    return Path(os.environ.get("AGENTFORGE_MEMORY", "memory"))


class ContextManager:
    def __init__(self, memory_dir=None):
        self.memory_dir = Path(memory_dir) if memory_dir else get_default_memory_dir()
        self.memory_dir.mkdir(exist_ok=True)
        
        # Context size thresholds (in estimated tokens)
        self.WARN_THRESHOLD = 150000
        self.CRITICAL_THRESHOLD = 180000
        self.COMPRESS_THRESHOLD = 200000
    
    def estimate_tokens(self, text):
        """Rough estimation of tokens from text (~4 chars per token)."""
        if not text:
            return 0
        return len(text) // 4
    
    def analyze_context(self, session_text):
        """Analyze current context usage and provide recommendations."""
        tokens = self.estimate_tokens(session_text)
        max_context = 200000  # Assumed context limit
        
        status = {
            "estimated_tokens": tokens,
            "percentage": round((tokens / max_context) * 100, 1),
            "status": "ok",
            "recommendations": []
        }
        
        if tokens > self.COMPRESS_THRESHOLD:
            status["status"] = "critical"
            status["recommendations"].extend([
                "CRITICAL: Immediate context cleanup required",
                "Summarize and archive old conversation parts",
                "Consider splitting into new session"
            ])
        elif tokens > self.CRITICAL_THRESHOLD:
            status["status"] = "critical"
            status["recommendations"].extend([
                "WARNING: Context nearly full - cleanup recommended",
                "Archive non-essential parts to memory files",
                "Focus on essential information only"
            ])
        elif tokens > self.WARN_THRESHOLD:
            status["status"] = "warning"
            status["recommendations"].extend([
                "NOTICE: Consider summarizing older parts",
                "Archive completed tasks to memory",
                "Remove redundant information"
            ])
        
        return status
    
    def create_summary(self, session_text, focus_areas=None):
        """Create a concise summary of session content."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "key_achievements": [],
            "active_tasks": [],
            "important_decisions": [],
            "context_for_future": [],
            "token_savings": 0
        }
        
        # Pattern matching for common elements
        patterns = {
            "achievements": [
                r"completed.*?(?=\n|$)",
                r"successfully.*?(?=\n|$)",
                r"applied to.*?(?=\n|$)",
                r"built.*?(?=\n|$)",
                r"created.*?(?=\n|$)",
                r"fixed.*?(?=\n|$)"
            ],
            "tasks": [
                r"TODO:.*?(?=\n|$)",
                r"Next:.*?(?=\n|$)", 
                r"Want me to.*?(?=\n|$)",
                r"need to.*?(?=\n|$)"
            ],
            "decisions": [
                r"decided to.*?(?=\n|$)",
                r"chose.*?(?=\n|$)",
                r"will use.*?(?=\n|$)",
                r"going with.*?(?=\n|$)"
            ]
        }
        
        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, session_text, re.IGNORECASE | re.MULTILINE)
                target = {
                    "achievements": summary["key_achievements"],
                    "tasks": summary["active_tasks"],
                    "decisions": summary["important_decisions"]
                }.get(category, [])
                target.extend(matches[:10])  # Limit per pattern
        
        # Deduplicate
        for key in ["key_achievements", "active_tasks", "important_decisions"]:
            summary[key] = list(dict.fromkeys(summary[key]))[:10]
        
        # Calculate token savings
        original_tokens = self.estimate_tokens(session_text)
        summary_text = self.format_summary(summary)
        summary_tokens = self.estimate_tokens(summary_text)
        summary["token_savings"] = original_tokens - summary_tokens
        
        return summary
    
    def format_summary(self, summary_data):
        """Format summary data into readable text."""
        lines = [f"# Session Summary - {summary_data['timestamp']}", ""]
        
        if summary_data.get("key_achievements"):
            lines.append("## Key Achievements")
            for item in summary_data["key_achievements"][:10]:
                lines.append(f"- {item.strip()}")
            lines.append("")
        
        if summary_data.get("active_tasks"):
            lines.append("## Active Tasks")
            for item in summary_data["active_tasks"][:5]:
                lines.append(f"- {item.strip()}")
            lines.append("")
        
        if summary_data.get("important_decisions"):
            lines.append("## Important Decisions")
            for item in summary_data["important_decisions"][:5]:
                lines.append(f"- {item.strip()}")
            lines.append("")
        
        if summary_data.get("context_for_future"):
            lines.append("## Context for Future")
            for item in summary_data["context_for_future"]:
                lines.append(f"- {item.strip()}")
            lines.append("")
        
        lines.append(f"**Token Savings:** {summary_data.get('token_savings', 0):,} tokens")
        
        return '\n'.join(lines)
    
    def archive_to_memory(self, summary, filename=None):
        """Archive summary to memory files."""
        today = datetime.now().strftime("%Y-%m-%d")
        memory_file = self.memory_dir / (filename or f"{today}.md")
        
        summary_text = self.format_summary(summary)
        
        try:
            if memory_file.exists():
                with open(memory_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                content += f"\n\n---\n\n{summary_text}"
            else:
                content = f"# {today} - Daily Memory\n\n{summary_text}"
            
            with open(memory_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return str(memory_file)
        except Exception as e:
            print(f"Error archiving: {e}", file=sys.stderr)
            return None
    
    def suggest_cleanup(self, session_text):
        """Suggest specific parts of context to clean up."""
        suggestions = []
        lines = session_text.split('\n')
        
        # Find repeated patterns
        line_counts = {}
        for line in lines:
            if len(line.strip()) > 20:
                normalized = re.sub(r'\d+', 'NUM', line.lower().strip())
                line_counts[normalized] = line_counts.get(normalized, 0) + 1
        
        repeated = [(l, c) for l, c in line_counts.items() if c > 3]
        if repeated:
            suggestions.append({
                "type": "repetition",
                "description": f"Found {len(repeated)} patterns repeated >3 times",
                "action": "Summarize repetitive content",
                "estimated_savings": len(repeated) * 500
            })
        
        # Look for browser snapshots
        snapshots = len(re.findall(r'browser.*snapshot', session_text, re.IGNORECASE))
        if snapshots > 5:
            suggestions.append({
                "type": "browser_heavy",
                "description": f"Found {snapshots} browser snapshots in context",
                "action": "Archive browser automation details",
                "estimated_savings": snapshots * 20000
            })
        
        # Look for completed items (various markers)
        completed = len(re.findall(r'(\[x\]|completed|done|finished)', session_text, re.IGNORECASE))
        if completed > 10:
            suggestions.append({
                "type": "completed_tasks",
                "description": f"Found {completed} completed items",
                "action": "Archive completed tasks to daily memory",
                "estimated_savings": completed * 200
            })
        
        # Large code blocks
        code_blocks = len(re.findall(r'```[\s\S]*?```', session_text))
        if code_blocks > 5:
            suggestions.append({
                "type": "code_blocks",
                "description": f"Found {code_blocks} code blocks",
                "action": "Save code to files, reference by path",
                "estimated_savings": code_blocks * 1000
            })
        
        return suggestions
    
    def emergency_cleanup(self, session_text, keep_lines=500):
        """Emergency cleanup when context is critically full."""
        lines = session_text.split('\n')
        
        # Essential patterns to preserve from older content
        essential_patterns = [
            r'error:',
            r'failed:',
            r'TODO:',
            r'important:',
            r'warning:',
            r'critical:',
        ]
        
        essential_lines = []
        recent_lines = lines[-keep_lines:]
        
        for line in lines[:-keep_lines]:
            line_lower = line.lower()
            for pattern in essential_patterns:
                if re.search(pattern, line_lower):
                    essential_lines.append(line)
                    break
        
        cleaned_text = '\n'.join(essential_lines + recent_lines)
        
        # Create summary of removed content
        removed_text = '\n'.join(lines[:-keep_lines])
        summary = self.create_summary(removed_text)
        
        return {
            "cleaned_text": cleaned_text,
            "summary": summary,
            "lines_kept": len(essential_lines) + len(recent_lines),
            "lines_removed": len(lines) - len(essential_lines) - len(recent_lines),
            "tokens_saved": self.estimate_tokens(session_text) - self.estimate_tokens(cleaned_text)
        }


def main():
    parser = argparse.ArgumentParser(
        description="Context Manager - Automatic summarization and cleanup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze session.txt      Analyze context usage
  %(prog)s summarize session.txt    Create session summary
  %(prog)s cleanup session.txt      Get cleanup suggestions
  %(prog)s archive session.txt      Summarize and archive to memory
  %(prog)s emergency session.txt    Emergency cleanup (critical context)

Environment Variables:
  AGENTFORGE_MEMORY    Memory directory (default: ./memory)
        """
    )
    
    parser.add_argument("--memory-dir", "-m", metavar="DIR",
                        help="Memory directory for archives")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # analyze command
    ana_parser = subparsers.add_parser("analyze", help="Analyze context usage")
    ana_parser.add_argument("file", help="Text file to analyze")
    
    # summarize command
    sum_parser = subparsers.add_parser("summarize", help="Create session summary")
    sum_parser.add_argument("file", help="Text file to summarize")
    
    # cleanup command
    cln_parser = subparsers.add_parser("cleanup", help="Get cleanup suggestions")
    cln_parser.add_argument("file", help="Text file to analyze")
    
    # archive command
    arc_parser = subparsers.add_parser("archive", help="Summarize and archive to memory")
    arc_parser.add_argument("file", help="Text file to archive")
    arc_parser.add_argument("--output", "-o", help="Output filename (default: today's date)")
    
    # emergency command
    emg_parser = subparsers.add_parser("emergency", help="Emergency context cleanup")
    emg_parser.add_argument("file", help="Text file to clean")
    emg_parser.add_argument("--keep", "-k", type=int, default=500,
                           help="Lines to keep from end (default: 500)")
    
    # thresholds command
    subparsers.add_parser("thresholds", help="Show context thresholds")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    manager = ContextManager(memory_dir=args.memory_dir if hasattr(args, 'memory_dir') else None)
    
    # Helper to read file safely
    def read_file(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    
    if args.command == "analyze":
        text = read_file(args.file)
        status = manager.analyze_context(text)
        
        print(f"Context Analysis:")
        print(f"  Estimated tokens: {status['estimated_tokens']:,}")
        print(f"  Usage: {status['percentage']}%")
        print(f"  Status: {status['status'].upper()}")
        
        if status['recommendations']:
            print("\nRecommendations:")
            for rec in status['recommendations']:
                print(f"  - {rec}")
    
    elif args.command == "summarize":
        text = read_file(args.file)
        summary = manager.create_summary(text)
        summary_text = manager.format_summary(summary)
        
        print(summary_text)
        print(f"\nToken savings: {summary['token_savings']:,} tokens")
    
    elif args.command == "cleanup":
        text = read_file(args.file)
        suggestions = manager.suggest_cleanup(text)
        
        if not suggestions:
            print("No cleanup suggestions - context looks efficient.")
            sys.exit(0)
        
        print("Cleanup Suggestions:\n")
        total_savings = 0
        
        for i, s in enumerate(suggestions, 1):
            print(f"{i}. {s['description']}")
            print(f"   Action: {s['action']}")
            print(f"   Estimated savings: {s['estimated_savings']:,} tokens\n")
            total_savings += s['estimated_savings']
        
        print(f"Total potential savings: {total_savings:,} tokens")
    
    elif args.command == "archive":
        text = read_file(args.file)
        summary = manager.create_summary(text)
        output_file = manager.archive_to_memory(summary, args.output)
        
        if output_file:
            print(f"Archived to: {output_file}")
            print(f"Token savings: {summary['token_savings']:,} tokens")
        else:
            print("Archive failed", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == "emergency":
        text = read_file(args.file)
        result = manager.emergency_cleanup(text, keep_lines=args.keep)
        
        print(f"Emergency Cleanup Complete:")
        print(f"  Lines kept: {result['lines_kept']:,}")
        print(f"  Lines removed: {result['lines_removed']:,}")
        print(f"  Tokens saved: {result['tokens_saved']:,}")
        print(f"\nSummary of removed content archived.")
    
    elif args.command == "thresholds":
        print("Context Thresholds:\n")
        print(f"  Warning:    {manager.WARN_THRESHOLD:,} tokens (75%)")
        print(f"  Critical:   {manager.CRITICAL_THRESHOLD:,} tokens (90%)")
        print(f"  Compress:   {manager.COMPRESS_THRESHOLD:,} tokens (100%)")


if __name__ == "__main__":
    main()
