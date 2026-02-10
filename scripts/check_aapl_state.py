"""
Quick check: what's actually in the state for AAPL query?
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')

from src.orchestration.langgraph_orchestrator import LangGraphOrchestrator

orchestrator = LangGraphOrchestrator(use_real_llm=True, llm_provider='deepseek')

print("Running AAPL query...")
state = orchestrator.run('test_aapl', 'Calculate the Sharpe ratio for AAPL from 2023-01-01 to 2023-12-31')

print(f"\nStatus: {state.status}")
print(f"\nState attributes: {dir(state)}")

# Check for verified facts in different locations
if hasattr(state, 'verified_fact'):
    print(f"\nstate.verified_fact: {state.verified_fact}")
    if state.verified_fact:
        if isinstance(state.verified_fact, list):
            print(f"  List of {len(state.verified_fact)} facts")
            for i, fact in enumerate(state.verified_fact):
                print(f"  [{i}] {fact.metric_name}: {fact.value}")
        else:
            print(f"  Single fact: {state.verified_fact.metric_name} = {state.verified_fact.value}")

if hasattr(state, 'verified_facts'):
    print(f"\nstate.verified_facts: {state.verified_facts}")

if hasattr(state, 'facts'):
    print(f"\nstate.facts: {state.facts}")

# Check final result
if hasattr(state, 'final_report'):
    print(f"\nstate.final_report: {state.final_report}")

if hasattr(state, 'synthesis'):
    print(f"\nstate.synthesis: {state.synthesis}")

print("\n" + "="*70)
print("RAW STATE:")
print("="*70)
print(state)
