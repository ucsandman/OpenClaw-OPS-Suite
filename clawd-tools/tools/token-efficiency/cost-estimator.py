#!/usr/bin/env python3
"""
Comprehensive Cost Estimator
Estimates token costs and suggests efficient alternatives.

Part of the AgentForge Toolkit by Practical Systems.
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


class CostEstimator:
    def __init__(self):
        self._load_cost_database()
    
    def _load_cost_database(self):
        """Load operation cost estimates."""
        self.operation_costs = {
            # Browser operations
            "browser_snapshot_linkedin": 50000,
            "browser_snapshot_github": 15000,
            "browser_snapshot_generic": 20000,
            "browser_snapshot": 20000,
            "browser_click": 100,
            "browser_navigate": 200,
            "browser_fill_form": 5000,
            "browser_evaluate": 2000,
            
            # File operations  
            "file_read_small": 1000,
            "file_read_medium": 5000,
            "file_read_large": 25000,
            "file_read_huge": 100000,
            "file_write": 500,
            "file_edit": 1000,
            
            # Web operations
            "web_search": 2000,
            "web_fetch": 5000,
            "api_call": 500,
            
            # AI operations
            "image_analysis_small": 10000,
            "image_analysis_large": 25000,
            "image_analysis": 15000,
            "code_generation": 8000,
            "text_analysis": 3000,
            "summarization": 5000,
            
            # System operations
            "exec_command": 300,
            "process_management": 200,
            "memory_search": 1000,
            "memory_get": 500,
            
            # Communication
            "message_send": 100,
            "tts_generation": 2000,
            
            # Workflows
            "job_application_full": 150000,
            "job_application_minimal": 20000,
            "email_check": 5000,
            "calendar_sync": 3000,
            "social_media_post": 8000
        }
        
        self.model_multipliers = {
            "opus": 1.0,
            "sonnet": 0.2,
            "haiku": 0.05
        }
        
        self.context_multipliers = {
            "small": 1.0,
            "medium": 1.2,
            "large": 1.5,
            "huge": 2.0
        }
    
    def estimate(self, operation_type, **kwargs):
        """Estimate cost for a specific operation."""
        base_cost = self.operation_costs.get(operation_type, 1000)
        
        # URL-based adjustments
        if "url" in kwargs and kwargs["url"]:
            try:
                domain = urlparse(kwargs["url"]).netloc.lower()
                if "linkedin.com" in domain:
                    base_cost = max(base_cost, 50000)
                elif "github.com" in domain:
                    base_cost = max(base_cost, 15000)
            except Exception:
                pass
        
        # File size adjustments
        if "file_size" in kwargs:
            size = kwargs["file_size"]
            if size > 1000000:
                base_cost = max(base_cost, 100000)
            elif size > 100000:
                base_cost = max(base_cost, 25000)
        
        # Model adjustments
        if "model" in kwargs:
            model = kwargs["model"].lower()
            for key, mult in self.model_multipliers.items():
                if key in model:
                    base_cost = int(base_cost * mult)
                    break
        
        # Context size adjustments
        if "context_size" in kwargs:
            size = kwargs["context_size"]
            if size > 150000:
                base_cost = int(base_cost * self.context_multipliers["huge"])
            elif size > 100000:
                base_cost = int(base_cost * self.context_multipliers["large"])
            elif size > 50000:
                base_cost = int(base_cost * self.context_multipliers["medium"])
        
        return base_cost
    
    def estimate_workflow(self, workflow_steps):
        """Estimate total cost for a workflow."""
        total_cost = 0
        step_costs = []
        
        for step in workflow_steps:
            cost = self.estimate(
                step.get("operation", "unknown"),
                **step.get("params", {})
            )
            total_cost += cost
            step_costs.append({
                "operation": step.get("operation"),
                "cost": cost,
                "description": step.get("description", "")
            })
        
        expensive = [s for s in step_costs if s["cost"] > 10000]
        optimization = self._calc_optimization_potential(step_costs)
        
        return {
            "total_cost": total_cost,
            "step_breakdown": step_costs,
            "expensive_steps": expensive,
            "optimization_potential": optimization
        }
    
    def _calc_optimization_potential(self, step_costs):
        """Calculate potential savings."""
        potential_savings = 0
        suggestions = []
        
        for step in step_costs:
            if step["cost"] > 50000:
                potential_savings += int(step["cost"] * 0.8)
                suggestions.append(f"High-cost: {step['operation']} - consider alternatives")
            elif step["cost"] > 20000:
                potential_savings += int(step["cost"] * 0.5)
                suggestions.append(f"Medium-cost: {step['operation']} - optimization possible")
        
        return {
            "potential_savings": potential_savings,
            "suggestions": suggestions
        }
    
    def suggest_optimizations(self, operation_type, current_cost=None):
        """Suggest ways to reduce costs."""
        if current_cost is None:
            current_cost = self.estimate(operation_type)
        
        suggestions = []
        
        if "browser" in operation_type and "snapshot" in operation_type:
            suggestions.extend([
                {
                    "method": "targeted_extraction",
                    "savings": int(current_cost * 0.9),
                    "description": "Extract specific elements instead of full snapshot"
                },
                {
                    "method": "model_switch",
                    "savings": int(current_cost * 0.8),
                    "description": "Switch to Sonnet for browser automation"
                },
                {
                    "method": "api_alternative",
                    "savings": int(current_cost * 0.95),
                    "description": "Use direct API calls instead of browser"
                }
            ])
        
        elif "file_read" in operation_type:
            suggestions.extend([
                {
                    "method": "selective_reading",
                    "savings": int(current_cost * 0.7),
                    "description": "Read specific lines with offset/limit"
                },
                {
                    "method": "preprocessing",
                    "savings": int(current_cost * 0.6),
                    "description": "Filter content before reading"
                }
            ])
        
        elif "job_application" in operation_type:
            suggestions.extend([
                {
                    "method": "template_based",
                    "savings": int(current_cost * 0.8),
                    "description": "Use pre-filled templates"
                },
                {
                    "method": "batch_processing",
                    "savings": int(current_cost * 0.6),
                    "description": "Apply to multiple jobs in one session"
                }
            ])
        
        # Universal suggestion for expensive ops
        if current_cost > 20000:
            suggestions.append({
                "method": "sonnet_switch",
                "savings": int(current_cost * 0.8),
                "description": "Switch to Claude Sonnet for this operation"
            })
        
        return sorted(suggestions, key=lambda x: x["savings"], reverse=True)
    
    def list_operations(self):
        """List all known operations and their costs."""
        return dict(sorted(self.operation_costs.items(), key=lambda x: -x[1]))


def main():
    parser = argparse.ArgumentParser(
        description="Cost Estimator - Estimate and optimize token costs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s estimate browser_snapshot_linkedin
                                Estimate cost for LinkedIn snapshot
  %(prog)s estimate browser_navigate --url https://github.com
                                Estimate with URL context
  %(prog)s optimize browser_snapshot_linkedin
                                Get optimization suggestions
  %(prog)s list                 Show all operations and costs
  %(prog)s workflow             Show example workflow analysis

Operation Categories:
  browser_*     Browser automation (snapshot, click, navigate, fill_form)
  file_*        File operations (read_small, read_large, write, edit)
  web_*         Web operations (search, fetch)
  image_*       Image analysis
  job_*         Job application workflows
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # estimate command
    est_parser = subparsers.add_parser("estimate", help="Estimate operation cost")
    est_parser.add_argument("operation", help="Operation type")
    est_parser.add_argument("--url", "-u", help="URL context")
    est_parser.add_argument("--model", "-m", help="Model (opus/sonnet/haiku)")
    est_parser.add_argument("--context-size", "-c", type=int, help="Current context size")
    
    # optimize command
    opt_parser = subparsers.add_parser("optimize", help="Get optimization suggestions")
    opt_parser.add_argument("operation", help="Operation type")
    
    # list command
    subparsers.add_parser("list", help="List all operations and costs")
    
    # workflow command
    subparsers.add_parser("workflow", help="Example workflow analysis")
    
    # compare command
    cmp_parser = subparsers.add_parser("compare", help="Compare operation costs")
    cmp_parser.add_argument("operations", nargs="+", help="Operations to compare")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    estimator = CostEstimator()
    
    if args.command == "estimate":
        kwargs = {}
        if args.url:
            kwargs["url"] = args.url
        if args.model:
            kwargs["model"] = args.model
        if args.context_size:
            kwargs["context_size"] = args.context_size
        
        cost = estimator.estimate(args.operation, **kwargs)
        print(f"Estimated cost for '{args.operation}': {cost:,} tokens")
        
        if cost > 10000:
            print("\nOptimization suggestions:")
            for opt in estimator.suggest_optimizations(args.operation, cost)[:3]:
                print(f"  - {opt['method']}: Save {opt['savings']:,} tokens")
                print(f"    {opt['description']}")
    
    elif args.command == "optimize":
        cost = estimator.estimate(args.operation)
        suggestions = estimator.suggest_optimizations(args.operation, cost)
        
        print(f"Optimizations for '{args.operation}' ({cost:,} tokens):\n")
        
        if not suggestions:
            print("No specific optimizations - operation is already efficient.")
        else:
            for i, opt in enumerate(suggestions, 1):
                print(f"{i}. {opt['method']}")
                print(f"   Potential savings: {opt['savings']:,} tokens")
                print(f"   {opt['description']}\n")
    
    elif args.command == "list":
        ops = estimator.list_operations()
        print("Operations by cost (highest first):\n")
        print(f"{'Operation':<35} {'Cost':>12}")
        print("-" * 48)
        for op, cost in ops.items():
            print(f"{op:<35} {cost:>10,}")
    
    elif args.command == "workflow":
        workflow = [
            {"operation": "browser_navigate", "description": "Open job site"},
            {"operation": "browser_snapshot_linkedin", "description": "Capture page"},
            {"operation": "browser_click", "description": "Click job"},
            {"operation": "browser_snapshot_linkedin", "description": "Job details"},
            {"operation": "browser_fill_form", "description": "Fill application"},
            {"operation": "browser_click", "description": "Submit"}
        ]
        
        result = estimator.estimate_workflow(workflow)
        
        print("Example Workflow: LinkedIn Job Application\n")
        print(f"{'Step':<30} {'Cost':>12}")
        print("-" * 43)
        for step in result["step_breakdown"]:
            print(f"{step['operation']:<30} {step['cost']:>10,}")
        print("-" * 43)
        print(f"{'TOTAL':<30} {result['total_cost']:>10,}")
        
        if result["optimization_potential"]["suggestions"]:
            print("\nOptimization opportunities:")
            for s in result["optimization_potential"]["suggestions"]:
                print(f"  - {s}")
            print(f"\nPotential savings: {result['optimization_potential']['potential_savings']:,} tokens")
    
    elif args.command == "compare":
        print(f"{'Operation':<35} {'Cost':>12}")
        print("-" * 48)
        for op in args.operations:
            cost = estimator.estimate(op)
            print(f"{op:<35} {cost:>10,}")


if __name__ == "__main__":
    main()
