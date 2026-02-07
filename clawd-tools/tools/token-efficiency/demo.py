#!/usr/bin/env python3
"""
Token Efficiency Toolkit Demo
Shows how the tools work together to optimize token usage
"""

from efficiency_cli import EfficiencyCLI
import json

def demo_token_efficiency():
    print("[!] TOKEN EFFICIENCY TOOLKIT DEMO\n")
    
    cli = EfficiencyCLI()
    
    # Demo 1: Check before expensive operation
    print("[#] DEMO 1: Pre-operation Check")
    print("=" * 40)
    
    result = cli.check_before_operation("browser_snapshot_linkedin", url="https://linkedin.com/jobs")
    
    print(f"Operation: {result['operation']}")
    print(f"Estimated cost: {result['estimated_cost']:,} tokens")
    print(f"Should proceed: {result['should_proceed']}")
    
    if result['warnings']:
        print("[!] Warnings:")
        for warning in result['warnings']:
            print(f"  {warning}")
    
    if result['alternatives']:
        print("[*] Alternatives:")
        for alt in result['alternatives'][:3]:
            print(f"  • {alt}")
    
    print()
    
    # Demo 2: Workflow optimization
    print("[*] DEMO 2: Workflow Optimization")
    print("=" * 40)
    
    workflow_result = cli.optimize_workflow("linkedin_job_search")
    
    if "error" not in workflow_result:
        print(f"Workflow: {workflow_result['workflow']}")
        print(f"Total cost: {workflow_result['total_cost']:,} tokens")
        print(f"Budget impact: {workflow_result['budget_impact']}")
        print(f"Recommendation: {workflow_result['proceed_recommendation'].upper()}")
        
        if workflow_result['optimization_suggestions']:
            print("[*] Optimizations:")
            for suggestion in workflow_result['optimization_suggestions']:
                print(f"  • {suggestion}")
    
    print()
    
    # Demo 3: Emergency mode
    print("[!!] DEMO 3: Emergency Mode Check")  
    print("=" * 40)
    
    emergency = cli.emergency_mode()
    
    print(f"Emergency level: {emergency['emergency_level'].upper()}")
    print(f"Remaining budget: {emergency['remaining_budget']:,} tokens")
    print(f"Suggested model: {emergency['suggested_model']}")
    
    if emergency['recommendations']:
        print("[#] Emergency recommendations:")
        for rec in emergency['recommendations'][:3]:
            print(f"  {rec}")
    
    print()
    
    # Demo 4: Cost comparison
    print("[$] DEMO 4: Cost Comparison")
    print("=" * 40)
    
    alternatives = [
        {
            "name": "Full Browser Automation", 
            "operation": "browser_snapshot_linkedin",
            "description": "Take full page snapshots",
            "pros": ["Complete visual context", "Easy to debug"],
            "cons": ["Very expensive", "Lots of irrelevant data"]
        },
        {
            "name": "Targeted Extraction",
            "operation": "browser_evaluate", 
            "description": "Extract specific elements only",
            "pros": ["Much cheaper", "Focused data", "Faster"],
            "cons": ["Requires knowing page structure"]
        },
        {
            "name": "Direct API",
            "operation": "api_call",
            "description": "Use LinkedIn API if available", 
            "pros": ["Cheapest", "Most reliable", "Structured data"],
            "cons": ["Limited availability", "Authentication needed"]
        }
    ]
    
    comparison = cli.cost_estimator.create_cost_comparison(alternatives)
    
    print("[#] Cost Comparison (LinkedIn job search):")
    for approach in comparison:
        print(f"  {approach['approach']}: {approach['cost']:,} tokens")
        print(f"    [>] {approach['description']}")
        print(f"    [OK] Pros: {', '.join(approach['pros'])}")
        print(f"    [X] Cons: {', '.join(approach['cons'])}")
        print()
    
    # Demo 5: Real-world savings example
    print("[*] DEMO 5: Real-World Savings")
    print("=" * 40)
    
    print("Today's LinkedIn job applications:")
    print("  [!] OLD WAY: 2 jobs × 150k tokens = 300k tokens")
    print("  [OK] NEW WAY: 2 jobs × 20k tokens = 40k tokens")  
    print("  [$] SAVINGS: 260k tokens (87% reduction!)")
    print("  [#] That's ~13 hours of Opus usage saved!")
    
    print("\n[>] KEY TAKEAWAYS:")
    print("  • Check budget before expensive operations") 
    print("  • Use Sonnet for automation, Opus for reasoning")
    print("  • Avoid LinkedIn snapshots when possible")
    print("  • Log operations to learn and improve")
    print("  • Emergency mode when budget is low")

if __name__ == "__main__":
    demo_token_efficiency()