"""
Quick test script for real LLM API integration.

Week 11 Day 1: Test that real API providers work.

Usage:
    cd "E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА"
    python scripts/test_real_llm_api.py
"""

import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.debate.llm_debate import LLMDebateNode

def test_openai():
    """Test OpenAI API."""
    print("\n" + "="*70)
    print("Testing OpenAI API (gpt-4o-mini)")
    print("="*70)

    node = LLMDebateNode(provider="openai")

    fact = {
        "metric": "sharpe_ratio",
        "ticker": "AAPL",
        "value": 1.95,
        "year": 2023,
        "supporting_data": [
            "Annual return: 44.9%",
            "Annual volatility: 17.8%",
            "Risk-free rate: 5.0%"
        ]
    }

    result = node.generate_debate(fact)

    print(f"\n✅ OpenAI Success!")
    print(f"   Bull: {result.bull_perspective.analysis[:100]}...")
    print(f"   Bear: {result.bear_perspective.analysis[:100]}...")
    print(f"   Synthesis: {result.synthesis[:100]}...")

    stats = node.get_stats()
    print(f"\n📊 Stats:")
    print(f"   Input tokens:  {stats['total_input_tokens']}")
    print(f"   Output tokens: {stats['total_output_tokens']}")
    print(f"   Cost:          ${stats['total_cost']:.6f}")

    return result


def test_gemini():
    """Test Gemini API."""
    print("\n" + "="*70)
    print("Testing Gemini API (gemini-2.0-flash-exp)")
    print("="*70)

    node = LLMDebateNode(provider="gemini")

    fact = {
        "metric": "sharpe_ratio",
        "ticker": "MSFT",
        "value": 1.73,
        "year": 2023,
        "supporting_data": [
            "Annual return: 38.2%",
            "Annual volatility: 22.1%"
        ]
    }

    result = node.generate_debate(fact)

    print(f"\n✅ Gemini Success!")
    print(f"   Bull: {result.bull_perspective.analysis[:100]}...")
    print(f"   Bear: {result.bear_perspective.analysis[:100]}...")
    print(f"   Synthesis: {result.synthesis[:100]}...")

    stats = node.get_stats()
    print(f"\n📊 Stats:")
    print(f"   Input tokens:  {stats['total_input_tokens']}")
    print(f"   Output tokens: {stats['total_output_tokens']}")
    print(f"   Cost:          ${stats['total_cost']:.6f} (FREE during preview)")

    return result


def test_deepseek():
    """Test DeepSeek API."""
    print("\n" + "="*70)
    print("Testing DeepSeek API (deepseek-chat)")
    print("="*70)

    node = LLMDebateNode(provider="deepseek")

    fact = {
        "metric": "sharpe_ratio",
        "ticker": "GOOGL",
        "value": 2.05,
        "year": 2023
    }

    result = node.generate_debate(fact)

    print(f"\n✅ DeepSeek Success!")
    print(f"   Bull: {result.bull_perspective.analysis[:100]}...")
    print(f"   Bear: {result.bear_perspective.analysis[:100]}...")
    print(f"   Synthesis: {result.synthesis[:100]}...")

    stats = node.get_stats()
    print(f"\n📊 Stats:")
    print(f"   Input tokens:  {stats['total_input_tokens']}")
    print(f"   Output tokens: {stats['total_output_tokens']}")
    print(f"   Cost:          ${stats['total_cost']:.6f}")

    return result


def compare_costs():
    """Compare costs across providers."""
    print("\n" + "="*70)
    print("COST COMPARISON (same fact to all 3 providers)")
    print("="*70)

    fact = {
        "metric": "correlation",
        "ticker1": "SPY",
        "ticker2": "QQQ",
        "value": 0.92,
        "year": 2023
    }

    # OpenAI
    openai_node = LLMDebateNode(provider="openai")
    openai_node.generate_debate(fact)
    openai_cost = openai_node.get_stats()["total_cost"]

    # Gemini
    gemini_node = LLMDebateNode(provider="gemini")
    gemini_node.generate_debate(fact)
    gemini_cost = gemini_node.get_stats()["total_cost"]

    # DeepSeek
    deepseek_node = LLMDebateNode(provider="deepseek")
    deepseek_node.generate_debate(fact)
    deepseek_cost = deepseek_node.get_stats()["total_cost"]

    print(f"\n💰 Cost per debate:")
    print(f"   OpenAI (gpt-4o-mini):  ${openai_cost:.6f}")
    print(f"   Gemini (2.0-flash):    ${gemini_cost:.6f}")
    print(f"   DeepSeek (chat):       ${deepseek_cost:.6f}")

    print(f"\n🏆 Winner: ", end="")
    if deepseek_cost < openai_cost and deepseek_cost < gemini_cost:
        print("DeepSeek (cheapest)")
    elif gemini_cost < openai_cost:
        print("Gemini (free during preview)")
    else:
        print("OpenAI")


if __name__ == "__main__":
    print("\n🚀 Week 11 Day 1: Real LLM API Integration Test")
    print("="*70)

    try:
        # Test each provider
        test_openai()
        test_gemini()
        test_deepseek()

        # Compare costs
        compare_costs()

        print("\n" + "="*70)
        print("✅ ALL PROVIDERS WORKING!")
        print("="*70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
