"""
Test DeepSeek API connectivity.

Quick test to verify API key and connection work.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import dspy
from src.optimization.deepseek_adapter import configure_deepseek, estimate_cost


def test_api():
    """Test DeepSeek API with simple query."""
    print("="*60)
    print("🧪 Testing DeepSeek R1 API")
    print("="*60)
    print()

    # Check API key
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        print("❌ DEEPSEEK_API_KEY not found")
        sys.exit(1)

    print(f"✅ API Key: {api_key[:10]}...{api_key[-4:]}")
    print()

    # Configure DeepSeek
    print("🔧 Configuring DeepSeek R1...")
    try:
        deepseek = configure_deepseek(model='deepseek-chat', temperature=0.0)
        print(f"   ✅ Configured: {deepseek}")
        print()
    except Exception as e:
        print(f"   ❌ Configuration failed: {e}")
        sys.exit(1)

    # Test simple query
    print("💬 Testing API call...")
    print("   Query: 'Write a Python function to calculate factorial'")
    print()

    try:
        # Create simple DSPy module
        class SimpleQA(dspy.Signature):
            """Answer coding questions."""
            question = dspy.InputField()
            answer = dspy.OutputField()

        qa = dspy.Predict(SimpleQA)

        # Make API call
        response = qa(question="Write a Python function to calculate factorial")

        print("✅ API call successful!")
        print()
        print("📝 Response:")
        print("-" * 60)
        print(response.answer[:500])  # First 500 chars
        if len(response.answer) > 500:
            print(f"\n... ({len(response.answer) - 500} more characters)")
        print("-" * 60)
        print()

        # Estimate cost
        est_cost = estimate_cost(100, 200, model='deepseek-chat')
        print(f"💰 Estimated cost for 100 input + 200 output tokens: ${est_cost:.6f}")
        print()

        print("="*60)
        print("✅ DeepSeek API test PASSED!")
        print("="*60)

    except Exception as e:
        print(f"❌ API call failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    test_api()
