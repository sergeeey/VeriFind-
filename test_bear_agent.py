"""Test Bear agent Anthropic integration."""
import asyncio
import sys
import os
import logging
from pathlib import Path

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Manual .env loading
env_file = Path('.env')
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

sys.path.insert(0, 'src')

from debate.parallel_orchestrator import run_multi_llm_debate


async def test_bear_agent():
    """Test Bear agent with a simple query."""
    print("\n" + "="*80)
    print("BEAR AGENT DIAGNOSTIC TEST")
    print("="*80 + "\n")

    query = "Analyze Apple (AAPL) stock"
    context = {}

    print(f"Query: {query}\n")
    print("Running multi-LLM debate...\n")

    try:
        result = await run_multi_llm_debate(query, context)

        # Extract perspectives
        perspectives = result.get('perspectives', {})
        bull = perspectives.get('bull', {})
        bear = perspectives.get('bear', {})
        arbiter = perspectives.get('arbiter', {})

        # Report results
        print("\n" + "="*80)
        print("RESULTS")
        print("="*80 + "\n")

        print("BULL AGENT:")
        print(f"  Analysis length: {len(bull.get('analysis', ''))} chars")
        print(f"  Confidence: {bull.get('confidence', 'N/A')}")
        print(f"  Key points: {len(bull.get('key_points', []))}")
        print(f"  Has error: {'Error' in str(bull.get('analysis', ''))}")

        print("\nBEAR AGENT:")
        print(f"  Analysis length: {len(bear.get('analysis', ''))} chars")
        print(f"  Confidence: {bear.get('confidence', 'N/A')}")
        print(f"  Key points: {len(bear.get('key_points', []))}")
        print(f"  Has error: {'Error' in str(bear.get('analysis', ''))}")

        if 'Error' in str(bear.get('analysis', '')):
            print(f"\n  ERROR MESSAGE:")
            print(f"  {bear.get('analysis', 'N/A')}")

        print("\nARBITER AGENT:")
        print(f"  Analysis length: {len(arbiter.get('analysis', ''))} chars")
        print(f"  Confidence: {arbiter.get('confidence', 'N/A')}")
        print(f"  Recommendation: {arbiter.get('recommendation', 'N/A')}")

        print("\n" + "="*80)
        print("STATUS")
        print("="*80 + "\n")

        if 'Error' not in str(bear.get('analysis', '')):
            print("✅ Bear agent: WORKING")
        else:
            print("❌ Bear agent: FAILED")

        return bear

    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    bear_result = asyncio.run(test_bear_agent())
