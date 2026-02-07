#!/usr/bin/env python3
"""
Token Budget Tracker
Monitors token usage and provides warnings/recommendations for AI agents.

Part of the AgentForge Toolkit by Practical Systems.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


def get_default_data_path():
    """Get default data file path, respecting AGENTFORGE_DATA env var."""
    base = os.environ.get("AGENTFORGE_DATA", Path(__file__).parent)
    return Path(base) / "token-usage.json"


class TokenTracker:
    def __init__(self, data_file=None):
        self.data_file = Path(data_file) if data_file else get_default_data_path()
        self.data = self._load_data()
        
    def _load_data(self):
        """Load data from JSON file with error handling."""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"Warning: Corrupt data file, starting fresh. Error: {e}", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Could not read data file: {e}", file=sys.stderr)
        
        return self._default_data()
    
    def _default_data(self):
        """Return default data structure."""
        return {
            "daily_limit": 50000,
            "weekly_limit": 350000,
            "usage": {},
            "sessions": []
        }
    
    def _save_data(self):
        """Save data to JSON file."""
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}", file=sys.stderr)
    
    def set_limits(self, daily=None, weekly=None):
        """Update budget limits."""
        if daily is not None:
            self.data["daily_limit"] = daily
        if weekly is not None:
            self.data["weekly_limit"] = weekly
        self._save_data()
        print(f"Limits updated - Daily: {self.data['daily_limit']:,} | Weekly: {self.data['weekly_limit']:,}")
    
    def log_usage(self, tokens_in, tokens_out, operation_type="general", model="default"):
        """Log token usage for an operation."""
        timestamp = datetime.now().isoformat()
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in self.data["usage"]:
            self.data["usage"][today] = {"total": 0, "operations": []}
        
        total_tokens = tokens_in + tokens_out
        self.data["usage"][today]["total"] += total_tokens
        self.data["usage"][today]["operations"].append({
            "timestamp": timestamp,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total": total_tokens,
            "operation": operation_type,
            "model": model
        })
        
        self._save_data()
        return self.get_budget_status()
    
    def estimate_operation_cost(self, operation_type):
        """Estimate token cost for different operations."""
        costs = {
            "linkedin_snapshot": 50000,
            "browser_snapshot": 20000,
            "browser_snapshot_simple": 10000,
            "simple_click": 100,
            "form_fill": 5000,
            "file_read_large": 30000,
            "file_read_small": 2000,
            "web_search": 2000,
            "web_fetch": 5000,
            "image_analysis": 15000,
            "code_generation": 8000,
            "api_call": 500
        }
        return costs.get(operation_type, 1000)
    
    def get_budget_status(self):
        """Get current budget status with warnings."""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_used = self.data["usage"].get(today, {}).get("total", 0)
        
        # Calculate weekly usage (last 7 days)
        weekly_used = 0
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            weekly_used += self.data["usage"].get(date, {}).get("total", 0)
        
        daily_limit = self.data.get("daily_limit", 50000)
        weekly_limit = self.data.get("weekly_limit", 350000)
        
        daily_remaining = max(0, daily_limit - daily_used)
        weekly_remaining = max(0, weekly_limit - weekly_used)
        
        status = {
            "daily": {
                "used": daily_used,
                "limit": daily_limit,
                "remaining": daily_remaining,
                "percentage": round((daily_used / daily_limit) * 100, 1) if daily_limit > 0 else 0
            },
            "weekly": {
                "used": weekly_used,
                "limit": weekly_limit,
                "remaining": weekly_remaining,
                "percentage": round((weekly_used / weekly_limit) * 100, 1) if weekly_limit > 0 else 0
            }
        }
        
        # Add warnings
        status["warnings"] = []
        if daily_remaining < 5000:
            status["warnings"].append("CRITICAL: Low daily tokens remaining")
        if weekly_remaining < 20000:
            status["warnings"].append("CRITICAL: Low weekly tokens remaining")
        if status["daily"]["percentage"] > 80:
            status["warnings"].append("NOTICE: Consider switching to a lighter model")
        
        return status
    
    def should_warn_before_operation(self, operation_type):
        """Check if we should warn before a high-cost operation."""
        cost = self.estimate_operation_cost(operation_type)
        status = self.get_budget_status()
        remaining = status["daily"]["remaining"]
        
        if remaining == 0:
            return {
                "warn": True,
                "message": f"BLOCKED: Daily budget exhausted. {operation_type} requires ~{cost:,} tokens.",
                "alternatives": self._suggest_alternatives(operation_type)
            }
        
        if cost > remaining * 0.1:  # >10% of remaining budget
            return {
                "warn": True,
                "message": f"WARNING: {operation_type} will use ~{cost:,} tokens ({round(cost/remaining*100, 1)}% of remaining daily budget)",
                "alternatives": self._suggest_alternatives(operation_type)
            }
        return {"warn": False}
    
    def _suggest_alternatives(self, operation_type):
        """Suggest lower-cost alternatives."""
        alternatives = {
            "linkedin_snapshot": [
                "Use targeted click instead of full snapshot",
                "Switch to a lighter model",
                "Use exec/curl for simple data extraction"
            ],
            "browser_snapshot": [
                "Navigate then act without snapshot",
                "Use specific element targeting",
                "Switch to lighter automation method"
            ],
            "file_read_large": [
                "Read specific lines with offset/limit",
                "Use grep/findstr to filter content first",
                "Process in smaller chunks"
            ],
            "image_analysis": [
                "Resize image before analysis",
                "Use text extraction if just reading text",
                "Crop to relevant section only"
            ]
        }
        return alternatives.get(operation_type, ["Switch to a lighter model", "Simplify operation"])
    
    def show_history(self, days=7):
        """Show usage history for the past N days."""
        print(f"\nUsage History (last {days} days):\n")
        print(f"{'Date':<12} {'Tokens':>10} {'Operations':>12}")
        print("-" * 36)
        
        total = 0
        for i in range(days - 1, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            day_data = self.data["usage"].get(date, {"total": 0, "operations": []})
            tokens = day_data.get("total", 0)
            ops = len(day_data.get("operations", []))
            total += tokens
            
            marker = " <-- today" if i == 0 else ""
            print(f"{date:<12} {tokens:>10,} {ops:>12}{marker}")
        
        print("-" * 36)
        print(f"{'Total':<12} {total:>10,}")
    
    def reset_day(self, date=None):
        """Reset usage for a specific day (default: today)."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if date in self.data["usage"]:
            old_total = self.data["usage"][date].get("total", 0)
            del self.data["usage"][date]
            self._save_data()
            print(f"Reset {date}: cleared {old_total:,} tokens")
        else:
            print(f"No data for {date}")


def main():
    parser = argparse.ArgumentParser(
        description="Token Budget Tracker - Monitor and manage AI token usage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      Show current budget status
  %(prog)s estimate browser_snapshot
                                Estimate cost of an operation
  %(prog)s log 5000 2000 code_generation
                                Log 7000 tokens for code generation
  %(prog)s history              Show 7-day usage history
  %(prog)s set-limits --daily 100000 --weekly 500000
                                Update budget limits
  %(prog)s --config /path/to/data.json
                                Use custom data file

Operation types for estimates:
  linkedin_snapshot, browser_snapshot, browser_snapshot_simple,
  simple_click, form_fill, file_read_large, file_read_small,
  web_search, web_fetch, image_analysis, code_generation, api_call
        """
    )
    
    parser.add_argument("--config", "-c", metavar="PATH",
                        help="Path to data file (default: token-usage.json)")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # estimate command
    est_parser = subparsers.add_parser("estimate", help="Estimate operation cost")
    est_parser.add_argument("operation", help="Operation type to estimate")
    
    # log command
    log_parser = subparsers.add_parser("log", help="Log token usage")
    log_parser.add_argument("tokens_in", type=int, help="Input tokens")
    log_parser.add_argument("tokens_out", type=int, help="Output tokens")
    log_parser.add_argument("operation", help="Operation description")
    log_parser.add_argument("--model", "-m", default="default", help="Model used")
    
    # history command
    hist_parser = subparsers.add_parser("history", help="Show usage history")
    hist_parser.add_argument("--days", "-d", type=int, default=7, help="Days to show")
    
    # set-limits command
    limits_parser = subparsers.add_parser("set-limits", help="Update budget limits")
    limits_parser.add_argument("--daily", type=int, help="Daily token limit")
    limits_parser.add_argument("--weekly", type=int, help="Weekly token limit")
    
    # reset command
    reset_parser = subparsers.add_parser("reset", help="Reset usage for a day")
    reset_parser.add_argument("--date", help="Date to reset (YYYY-MM-DD, default: today)")
    
    args = parser.parse_args()
    
    # Initialize tracker
    tracker = TokenTracker(data_file=args.config)
    
    # Handle commands
    if args.command == "estimate":
        cost = tracker.estimate_operation_cost(args.operation)
        warning = tracker.should_warn_before_operation(args.operation)
        
        print(f"Estimated cost: {cost:,} tokens")
        if warning["warn"]:
            print(f"\n{warning['message']}")
            print("\nAlternatives:")
            for alt in warning["alternatives"]:
                print(f"  - {alt}")
    
    elif args.command == "log":
        status = tracker.log_usage(args.tokens_in, args.tokens_out, args.operation, args.model)
        total = args.tokens_in + args.tokens_out
        print(f"Logged {total:,} tokens for '{args.operation}'")
        print(f"Daily: {status['daily']['used']:,}/{status['daily']['limit']:,} ({status['daily']['percentage']}%)")
        if status['warnings']:
            for w in status['warnings']:
                print(w)
    
    elif args.command == "history":
        tracker.show_history(args.days)
    
    elif args.command == "set-limits":
        if args.daily is None and args.weekly is None:
            print("Specify --daily and/or --weekly limits")
            sys.exit(1)
        tracker.set_limits(daily=args.daily, weekly=args.weekly)
    
    elif args.command == "reset":
        tracker.reset_day(args.date)
    
    else:
        # Default: show status
        status = tracker.get_budget_status()
        print(f"Daily:  {status['daily']['used']:,} / {status['daily']['limit']:,} ({status['daily']['percentage']}% used)")
        print(f"Weekly: {status['weekly']['used']:,} / {status['weekly']['limit']:,} ({status['weekly']['percentage']}% used)")
        
        if status['warnings']:
            print("")
            for warning in status['warnings']:
                print(warning)
        else:
            print("\nBudget healthy.")


if __name__ == "__main__":
    main()
