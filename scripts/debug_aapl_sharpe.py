"""
Debug script for AAPL Sharpe ratio queries (gs_005, gs_006)
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
env_path = project_root / '.env'
load_dotenv(env_path)
print(f"✅ Loaded environment from {env_path}")

from src.orchestration.langgraph_orchestrator import LangGraphOrchestrator

async def test_aapl_sharpe():
    # Initialize orchestrator
    print("\n🔧 Initializing orchestrator...")
    orchestrator = LangGraphOrchestrator(
        use_real_llm=True,
        llm_provider='deepseek'
    )

    # Test gs_005 query
    query = 'Calculate the Sharpe ratio for AAPL from 2023-01-01 to 2023-12-31'
    print(f'\n📊 Testing query: {query}')
    print('='*70)

    result = orchestrator.run(
        query_id='debug_gs_005',
        query_text=query
    )

    print(f'\n✅ Result status: {result.status}')

    # Check for errors (APEState stores error in state.error, not result.error)
    if hasattr(result, 'error') and result.error:
        print(f'❌ Error: {result.error}')
    elif result.status == 'FAILED' or result.status == 'ERROR':
        print(f'❌ Query failed with status: {result.status}')

    if result.verified_facts:
        print(f'\n✅ Verified facts: {len(result.verified_facts)}')
        for fact in result.verified_facts:
            print(f'  - {fact.metric_name}: {fact.value}')
    else:
        print('\n⚠️  No verified facts!')

    return result

if __name__ == '__main__':
    result = asyncio.run(test_aapl_sharpe())

    # Print summary
    print('\n'+ '='*70)
    print('SUMMARY:')
    print(f'  Status: {result.status}')
    print(f'  Facts: {len(result.verified_facts) if result.verified_facts else 0}')
    print(f'  Error: {result.error if result.error else "None"}')
