#!/usr/bin/env python3
"""
Smart Browser Helper for Token Efficiency
Provides alternatives to expensive browser operations.

Part of the AgentForge Toolkit by Practical Systems.
"""

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


class SmartBrowser:
    def __init__(self, tracker=None):
        self.tracker = tracker
        
        # Site-specific token costs (based on page complexity)
        self.site_costs = {
            "linkedin.com": 50000,
            "github.com": 15000,
            "google.com": 10000,
            "stackoverflow.com": 12000,
            "reddit.com": 20000,
            "twitter.com": 25000,
            "x.com": 25000,
            "youtube.com": 30000,
            "facebook.com": 35000,
            "instagram.com": 30000,
            "default": 8000
        }
    
    def estimate_snapshot_cost(self, url):
        """Estimate token cost for taking a snapshot of a URL."""
        if not url:
            return self.site_costs["default"]
            
        try:
            domain = urlparse(url).netloc.lower()
            domain = re.sub(r'^www\.', '', domain)
        except Exception:
            return self.site_costs["default"]
        
        for site, cost in self.site_costs.items():
            if site != "default" and site in domain:
                return cost
        
        return self.site_costs["default"]
    
    def suggest_alternatives(self, action, url=None, target_element=None):
        """Suggest token-efficient alternatives for browser actions."""
        suggestions = []
        
        if action == "snapshot":
            suggestions.append({
                "method": "targeted_click",
                "cost": 100,
                "description": "Navigate directly to element without snapshot",
                "code": 'browser act click ref="target_element"'
            })
            
            selector = target_element or ".main-content"
            suggestions.append({
                "method": "structured_extract",
                "cost": 2000,
                "description": "Extract specific data instead of full page",
                "code": f'browser act evaluate fn="() => document.querySelector(\'{selector}\').innerText"'
            })
            
            if url and ("api" in url or "json" in url):
                suggestions.append({
                    "method": "direct_api",
                    "cost": 500,
                    "description": "Use direct API call instead of browser",
                    "code": f'exec curl -s "{url}"'
                })
        
        elif action == "form_fill":
            suggestions.extend([
                {
                    "method": "batch_fill",
                    "cost": 1000,
                    "description": "Fill multiple fields in one action",
                    "code": 'browser act fill fields=[{ref, value}, ...]'
                },
                {
                    "method": "template_based",
                    "cost": 500,
                    "description": "Use saved form templates",
                    "code": "Load predefined form data from config"
                }
            ])
        
        elif action == "search":
            suggestions.extend([
                {
                    "method": "direct_url",
                    "cost": 200,
                    "description": "Navigate directly to search URL pattern",
                    "code": 'browser navigate "site.com/search?q=..."'
                },
                {
                    "method": "api_search",
                    "cost": 500,
                    "description": "Use site API if available",
                    "code": "Direct API call instead of browser"
                }
            ])
        
        elif action == "login":
            suggestions.extend([
                {
                    "method": "saved_session",
                    "cost": 0,
                    "description": "Use browser profile with saved cookies",
                    "code": 'browser profile="saved_profile"'
                },
                {
                    "method": "batch_fill",
                    "cost": 500,
                    "description": "Fill credentials in one action",
                    "code": 'browser act fill fields=[{ref:"user"}, {ref:"pass"}]'
                }
            ])
        
        return sorted(suggestions, key=lambda x: x["cost"])
    
    def check_before_action(self, action, url=None):
        """Check if we should proceed with a browser action."""
        if action == "snapshot":
            cost = self.estimate_snapshot_cost(url)
            
            # Check budget if tracker available
            if self.tracker:
                warning = self.tracker.should_warn_before_operation("browser_snapshot")
                if warning.get("warn"):
                    return {
                        "proceed": False,
                        "warning": warning["message"],
                        "alternatives": self.suggest_alternatives(action, url),
                        "estimated_cost": cost
                    }
            
            # Always warn for high-cost sites
            if cost >= 25000:
                return {
                    "proceed": False,
                    "warning": f"High-cost site detected (~{cost:,} tokens)",
                    "alternatives": self.suggest_alternatives(action, url),
                    "estimated_cost": cost
                }
        
        return {"proceed": True, "estimated_cost": self.estimate_snapshot_cost(url) if url else 0}
    
    def optimize_sequence(self, steps):
        """Optimize a sequence of browser steps to minimize tokens."""
        if not steps:
            return []
            
        optimized = []
        last_snapshot = -999
        
        for i, step in enumerate(steps):
            if step.get("action") == "snapshot":
                # Only keep snapshot if >3 steps since last one
                if i - last_snapshot > 3:
                    optimized.append(step)
                    last_snapshot = len(optimized) - 1
                # else skip redundant snapshot
            else:
                optimized.append(step)
        
        return optimized
    
    def get_template(self, task_type):
        """Get token-efficient automation template."""
        templates = {
            "job_apply": '''# Token-efficient job application
browser navigate "{url}"
browser act click ref="apply_button"  # No snapshot needed
browser act fill fields=[
    {{"ref": "email", "value": "$EMAIL"}},
    {{"ref": "phone", "value": "$PHONE"}}
]
browser act click ref="submit"
''',
            
            "form": '''# Batch form filling
browser navigate "{url}"
browser act fill fields=[
    {{"ref": "field1", "value": "value1"}},
    {{"ref": "field2", "value": "value2"}}
]
browser act click ref="submit"
''',
            
            "extract": '''# Data extraction without full snapshot
browser navigate "{url}"
browser act evaluate fn="
    () => ({{
        title: document.querySelector('h1')?.innerText,
        content: document.querySelector('.content')?.innerText
    }})
"
''',
            
            "login": '''# Efficient login
browser navigate "{url}"
browser act fill fields=[
    {{"ref": "username", "value": "$USERNAME"}},
    {{"ref": "password", "value": "$PASSWORD"}}
]
browser act click ref="login_button"
'''
        }
        
        return templates.get(task_type, "# No template found for: " + task_type)


def main():
    parser = argparse.ArgumentParser(
        description="Smart Browser Helper - Token-efficient browser automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s estimate https://linkedin.com/jobs
                                Estimate snapshot cost for URL
  %(prog)s alternatives snapshot --url https://example.com
                                Show cheaper alternatives
  %(prog)s check snapshot --url https://linkedin.com
                                Check if action is budget-safe
  %(prog)s template job_apply   Get efficient automation template

Actions for alternatives/check: snapshot, form_fill, search, login
Templates: job_apply, form, extract, login
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # estimate command
    est_parser = subparsers.add_parser("estimate", help="Estimate snapshot cost")
    est_parser.add_argument("url", help="URL to estimate")
    
    # alternatives command
    alt_parser = subparsers.add_parser("alternatives", help="Suggest cheaper alternatives")
    alt_parser.add_argument("action", choices=["snapshot", "form_fill", "search", "login"],
                           help="Action type")
    alt_parser.add_argument("--url", "-u", help="Target URL")
    alt_parser.add_argument("--element", "-e", help="Target element selector")
    
    # check command
    chk_parser = subparsers.add_parser("check", help="Check if action is safe for budget")
    chk_parser.add_argument("action", choices=["snapshot", "form_fill", "search", "login"],
                           help="Action type")
    chk_parser.add_argument("--url", "-u", help="Target URL")
    
    # template command
    tpl_parser = subparsers.add_parser("template", help="Get automation template")
    tpl_parser.add_argument("type", choices=["job_apply", "form", "extract", "login"],
                           help="Template type")
    
    # sites command
    subparsers.add_parser("sites", help="Show known site costs")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    browser = SmartBrowser()
    
    if args.command == "estimate":
        cost = browser.estimate_snapshot_cost(args.url)
        print(f"Estimated snapshot cost: {cost:,} tokens")
        if cost >= 25000:
            print("WARNING: High-cost site - consider alternatives")
    
    elif args.command == "alternatives":
        alts = browser.suggest_alternatives(args.action, args.url, args.element)
        print(f"Alternatives for '{args.action}':\n")
        for i, alt in enumerate(alts, 1):
            print(f"{i}. {alt['method']} ({alt['cost']:,} tokens)")
            print(f"   {alt['description']}")
            print(f"   Code: {alt['code']}\n")
    
    elif args.command == "check":
        result = browser.check_before_action(args.action, args.url)
        if result["proceed"]:
            print(f"OK: Safe to proceed (~{result.get('estimated_cost', 0):,} tokens)")
        else:
            print(f"WARNING: {result['warning']}")
            print(f"Estimated cost: {result['estimated_cost']:,} tokens")
            print("\nCheaper alternatives:")
            for alt in result["alternatives"][:3]:
                print(f"  - {alt['method']}: {alt['cost']:,} tokens")
    
    elif args.command == "template":
        template = browser.get_template(args.type)
        print(template)
    
    elif args.command == "sites":
        print("Known site costs (tokens per snapshot):\n")
        for site, cost in sorted(browser.site_costs.items(), key=lambda x: -x[1]):
            if site != "default":
                print(f"  {site:<25} {cost:>10,}")
        print(f"\n  {'(other sites)':<25} {browser.site_costs['default']:>10,}")


if __name__ == "__main__":
    main()
