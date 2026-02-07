#!/usr/bin/env python3
"""
Session Token Optimizer - Check if we should start fresh
"""
import sys
import json
from pathlib import Path

def analyze_session(status_text):
    """Parse session status and recommend actions"""
    
    # Extract token counts from status text
    lines = status_text.split('\n')
    
    input_tokens = 0
    output_tokens = 0
    
    for line in lines:
        if 'Input:' in line or 'in:' in line.lower():
            # Extract number
            parts = line.split()
            for i, part in enumerate(parts):
                if part.lower() in ['input:', 'in:']:
                    try:
                        input_tokens = int(parts[i+1].replace(',', ''))
                    except:
                        pass
        if 'Output:' in line or 'out:' in line.lower():
            parts = line.split()
            for i, part in enumerate(parts):
                if part.lower() in ['output:', 'out:']:
                    try:
                        output_tokens = int(parts[i+1].replace(',', ''))
                    except:
                        pass
    
    total = input_tokens + output_tokens
    
    recommendations = []
    
    # Check thresholds
    if total > 150000:
        recommendations.append("⚠️ CRITICAL: >150k tokens - START FRESH SESSION NOW")
    elif total > 100000:
        recommendations.append("⚠️ WARNING: >100k tokens - Consider starting fresh soon")
    elif total > 50000:
        recommendations.append("💡 INFO: >50k tokens - Session getting heavy")
    
    # Context efficiency check
    if input_tokens > output_tokens * 3:
        recommendations.append("📊 Context baggage detected - too much input vs output")
    
    # Daily budget check (assume ~30k safe daily budget)
    if total > 30000:
        recommendations.append("💰 Daily budget warning - approaching 30k token limit")
    
    return {
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'total_tokens': total,
        'recommendations': recommendations,
        'status': 'critical' if total > 150000 else 'warning' if total > 100000 else 'ok'
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python session_check.py '<status_text>'")
        print("Or: python session_check.py --check")
        return
    
    if sys.argv[1] == '--check':
        # Placeholder for checking current session
        print("Run 'session_status' tool to get current usage, then pass output here")
        return
    
    status_text = sys.argv[1]
    result = analyze_session(status_text)
    
    print(f"\n📊 Session Analysis:")
    print(f"  Input:  {result['input_tokens']:,} tokens")
    print(f"  Output: {result['output_tokens']:,} tokens")
    print(f"  Total:  {result['total_tokens']:,} tokens")
    print(f"\n  Status: {result['status'].upper()}")
    
    if result['recommendations']:
        print(f"\n💡 Recommendations:")
        for rec in result['recommendations']:
            print(f"  {rec}")
    else:
        print(f"\n✅ Session health looks good!")
    
    # Save state
    state_file = Path(__file__).parent / "session_state.json"
    state_file.write_text(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
