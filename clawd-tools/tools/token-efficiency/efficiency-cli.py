#!/usr/bin/env python3
"""
Token Efficiency CLI - Unified interface for token optimization.

Part of the AgentForge Toolkit by Practical Systems.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


# Get the directory where this script lives
SCRIPT_DIR = Path(__file__).parent


def run_tool(tool_name, args):
    """Run another tool in this directory."""
    tool_path = SCRIPT_DIR / f"{tool_name}.py"
    if not tool_path.exists():
        print(f"Error: Tool not found: {tool_path}", file=sys.stderr)
        return None
    
    cmd = [sys.executable, str(tool_path)] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(SCRIPT_DIR))
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return f"Error running {tool_name}: {e}"


def cmd_check(args):
    """Check before an operation."""
    output = run_tool("cost-estimator", ["estimate", args.operation])
    if output:
        print(output.strip())
    
    # Also check budget
    budget_output = run_tool("token-tracker", [])
    if budget_output:
        print("\nBudget Status:")
        print(budget_output.strip())
    
    # Suggest alternatives if expensive
    cost_line = output.split('\n')[0] if output else ""
    if "50,000" in cost_line or "100,000" in cost_line:
        print("\nWARNING: High-cost operation detected!")
        opt_output = run_tool("cost-estimator", ["optimize", args.operation])
        if opt_output:
            print(opt_output.strip())


def cmd_log(args):
    """Log token usage."""
    output = run_tool("token-tracker", [
        "log", str(args.tokens_in), str(args.tokens_out), args.operation
    ])
    if output:
        print(output.strip())


def cmd_status(args):
    """Show current status."""
    print("=== Token Efficiency Status ===\n")
    
    # Budget status
    print("Budget:")
    budget_output = run_tool("token-tracker", [])
    if budget_output:
        for line in budget_output.strip().split('\n'):
            print(f"  {line}")
    
    # History
    print("\nRecent History:")
    history_output = run_tool("token-tracker", ["history", "--days", "3"])
    if history_output:
        for line in history_output.strip().split('\n'):
            print(f"  {line}")


def cmd_estimate(args):
    """Estimate operation cost."""
    cmd_args = ["estimate", args.operation]
    if args.url:
        cmd_args.extend(["--url", args.url])
    
    output = run_tool("cost-estimator", cmd_args)
    if output:
        print(output.strip())


def cmd_optimize(args):
    """Get optimization suggestions."""
    if args.operation:
        output = run_tool("cost-estimator", ["optimize", args.operation])
    elif args.workflow:
        output = run_tool("cost-estimator", ["workflow"])
    else:
        output = "Specify --operation or --workflow"
    
    if output:
        print(output.strip())


def cmd_browser(args):
    """Browser-specific checks."""
    cmd_args = []
    if args.subcommand == "estimate":
        cmd_args = ["estimate", args.url]
    elif args.subcommand == "sites":
        cmd_args = ["sites"]
    elif args.subcommand == "alternatives":
        cmd_args = ["alternatives", "snapshot", "--url", args.url]
    
    output = run_tool("smart-browser", cmd_args)
    if output:
        print(output.strip())


def cmd_context(args):
    """Context management."""
    if args.subcommand == "analyze" and args.file:
        output = run_tool("context-manager", ["analyze", args.file])
    elif args.subcommand == "thresholds":
        output = run_tool("context-manager", ["thresholds"])
    elif args.subcommand == "cleanup" and args.file:
        output = run_tool("context-manager", ["cleanup", args.file])
    else:
        output = "Specify a valid subcommand"
    
    if output:
        print(output.strip())


def cmd_emergency(args):
    """Emergency mode check."""
    print("=== Emergency Mode Check ===\n")
    
    # Get budget status
    budget_output = run_tool("token-tracker", [])
    if budget_output:
        print("Current Budget:")
        for line in budget_output.strip().split('\n'):
            print(f"  {line}")
    
    print("\nEmergency Recommendations:")
    
    # Parse budget to check if emergency
    if budget_output and "remaining" in budget_output.lower():
        # Check if low budget
        if "CRITICAL" in budget_output or "WARNING" in budget_output:
            print("  [!] CRITICAL: Switch to Claude Sonnet immediately")
            print("  [!] Avoid browser automation - use direct API calls")
            print("  [!] No large file operations")
            print("  [!] Summarize and archive context immediately")
        else:
            print("  Budget is healthy - no emergency actions needed")
    else:
        print("  Could not determine budget status")


def cmd_help(args):
    """Show help for all tools."""
    print("=== AgentForge Token Efficiency Toolkit ===\n")
    print("Individual Tools:")
    print("  python token-tracker.py --help     Budget tracking")
    print("  python smart-browser.py --help     Browser optimization")
    print("  python context-manager.py --help   Context management")
    print("  python cost-estimator.py --help    Cost estimation")
    print("\nQuick Commands:")
    print("  efficiency-cli.py status           Show current status")
    print("  efficiency-cli.py check <op>       Check before operation")
    print("  efficiency-cli.py estimate <op>    Estimate cost")
    print("  efficiency-cli.py emergency        Check if emergency mode needed")


def main():
    parser = argparse.ArgumentParser(
        description="Token Efficiency CLI - Unified interface for optimization tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  status                    Show budget and recent usage
  check <operation>         Pre-flight check before operation
  estimate <operation>      Estimate token cost
  log <in> <out> <op>       Log token usage
  optimize                  Get optimization suggestions
  browser                   Browser-specific tools
  context                   Context management tools
  emergency                 Check if emergency mode needed
  tools                     Show individual tool help

Examples:
  %(prog)s status
  %(prog)s check browser_snapshot_linkedin
  %(prog)s estimate browser_navigate --url https://github.com
  %(prog)s log 5000 2000 code_generation
  %(prog)s optimize --operation browser_snapshot
  %(prog)s browser sites
  %(prog)s emergency
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # status command
    subparsers.add_parser("status", help="Show current status")
    
    # check command
    chk_parser = subparsers.add_parser("check", help="Pre-flight check")
    chk_parser.add_argument("operation", help="Operation to check")
    
    # estimate command
    est_parser = subparsers.add_parser("estimate", help="Estimate cost")
    est_parser.add_argument("operation", help="Operation type")
    est_parser.add_argument("--url", "-u", help="URL context")
    
    # log command
    log_parser = subparsers.add_parser("log", help="Log usage")
    log_parser.add_argument("tokens_in", type=int, help="Input tokens")
    log_parser.add_argument("tokens_out", type=int, help="Output tokens")
    log_parser.add_argument("operation", help="Operation type")
    
    # optimize command
    opt_parser = subparsers.add_parser("optimize", help="Optimization suggestions")
    opt_parser.add_argument("--operation", "-o", help="Operation to optimize")
    opt_parser.add_argument("--workflow", "-w", action="store_true", help="Show workflow example")
    
    # browser command
    brw_parser = subparsers.add_parser("browser", help="Browser tools")
    brw_parser.add_argument("subcommand", choices=["estimate", "sites", "alternatives"],
                           help="Browser subcommand")
    brw_parser.add_argument("url", nargs="?", default="https://example.com", help="URL")
    
    # context command
    ctx_parser = subparsers.add_parser("context", help="Context tools")
    ctx_parser.add_argument("subcommand", choices=["analyze", "thresholds", "cleanup"],
                           help="Context subcommand")
    ctx_parser.add_argument("file", nargs="?", help="File to analyze")
    
    # emergency command
    subparsers.add_parser("emergency", help="Emergency mode check")
    
    # tools command
    subparsers.add_parser("tools", help="Show individual tool help")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    commands = {
        "status": cmd_status,
        "check": cmd_check,
        "estimate": cmd_estimate,
        "log": cmd_log,
        "optimize": cmd_optimize,
        "browser": cmd_browser,
        "context": cmd_context,
        "emergency": cmd_emergency,
        "tools": cmd_help
    }
    
    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
