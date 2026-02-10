"""
Quick retry script for gs_005 and gs_006 (AAPL Sharpe queries)
"""
import json
import time
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load Golden Set
golden_set_path = Path(__file__).parent.parent / 'tests' / 'golden_set' / 'financial_queries_v1.json'
with open(golden_set_path) as f:
    golden_set = json.load(f)

# Find gs_005 and gs_006
target_queries = ['gs_005', 'gs_006']
queries_to_retry = [q for q in golden_set['queries'] if q['id'] in target_queries]

print(f"Found {len(queries_to_retry)} queries to retry:")
for q in queries_to_retry:
    print(f"  - {q['id']}: {q['query']}")

# Load environment
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)
print(f"\n✅ Loaded environment from {env_path}")

# Initialize orchestrator
import asyncio
from src.orchestration.langgraph_orchestrator import LangGraphOrchestrator

orchestrator = LangGraphOrchestrator(
    use_real_llm=True,
    llm_provider='deepseek'
)
print("✅ Orchestrator initialized\n")

# Retry queries
results = []
for query_data in queries_to_retry:
    query_id = query_data['id']
    query_text = query_data['query']
    expected = query_data['expected_value']

    print(f"\n{'='*70}")
    print(f"🔄 Retrying {query_id}")
    print(f"Query: {query_text}")
    print(f"Expected: {expected}")

    try:
        start = time.time()
        state = orchestrator.run(query_id, query_text)
        duration = time.time() - start

        print(f"✅ Status: {state.status}")
        print(f"⏱️  Duration: {duration:.1f}s")

        if state.status.value == 'COMPLETED':
            # Extract Sharpe ratio value from verified_fact.extracted_values
            if hasattr(state, 'verified_fact') and state.verified_fact:
                fact = state.verified_fact
                print(f"DEBUG: fact type: {type(fact)}")
                print(f"DEBUG: has extracted_values: {hasattr(fact, 'extracted_values')}")

                sharpe_value = None

                # Check extracted_values dict
                if hasattr(fact, 'extracted_values') and fact.extracted_values:
                    print(f"DEBUG: extracted_values: {fact.extracted_values}")
                    sharpe_value = fact.extracted_values.get('sharpe_ratio')
                    print(f"DEBUG: sharpe_value from dict: {sharpe_value}")

                # Fallback: check if it's a dict directly
                if sharpe_value is None and isinstance(fact, dict):
                    sharpe_value = fact.get('sharpe_ratio')

                if sharpe_value:
                    tolerance = query_data['tolerance']
                    error = abs(sharpe_value - expected)
                    within_tolerance = error <= tolerance

                    print(f"📊 Sharpe Ratio: {sharpe_value:.4f}")
                    print(f"🎯 Expected: {expected} ± {tolerance}")
                    print(f"📏 Error: {error:.4f}")

                    if within_tolerance:
                        print(f"✅ PASS")
                        results.append({'id': query_id, 'status': 'PASS', 'value': sharpe_value})
                    else:
                        print(f"❌ FAIL (outside tolerance)")
                        results.append({'id': query_id, 'status': 'FAIL', 'value': sharpe_value})
                else:
                    print(f"⚠️  No Sharpe ratio found in verified facts")
                    results.append({'id': query_id, 'status': 'ERROR', 'value': None})
            else:
                print(f"⚠️  No verified facts")
                results.append({'id': query_id, 'status': 'ERROR', 'value': None})
        else:
            print(f"❌ FAILED with status: {state.status}")
            results.append({'id': query_id, 'status': 'ERROR', 'value': None})

    except Exception as e:
        print(f"❌ Exception: {e}")
        results.append({'id': query_id, 'status': 'EXCEPTION', 'value': None})

# Summary
print(f"\n{'='*70}")
print(f"RETRY SUMMARY:")
print(f"{'='*70}")
for r in results:
    status_icon = '✅' if r['status'] == 'PASS' else '❌'
    print(f"{status_icon} {r['id']}: {r['status']} (value: {r['value']})")

passed = sum(1 for r in results if r['status'] == 'PASS')
print(f"\nResult: {passed}/{len(results)} passed")

if passed == len(results):
    print("\n🎉 Both queries PASSED! Can update Golden Set baseline to 93.33%")
elif passed > 0:
    print(f"\n⚠️  {passed} query passed, {len(results)-passed} still failing")
else:
    print("\n❌ Both queries still failing - may be systematic issue")
