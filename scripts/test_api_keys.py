"""
Test script to verify API keys are working.

Tests:
1. OpenAI (GPT-4) - Chat completion
2. Google Gemini - Generate content
3. DeepSeek - If key is provided

Usage:
    python scripts/test_api_keys.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_path = project_root / ".env"
load_dotenv(env_path)

print("=" * 70)
print("API Keys Test - APE 2026")
print("=" * 70)
print()

# ============================================================================
# Test 1: OpenAI API
# ============================================================================

def test_openai():
    """Test OpenAI API key."""
    print("1. Testing OpenAI API...")
    print("-" * 70)

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key or api_key == "your_openai_api_key_here":
        print("❌ FAIL: OpenAI API key not set")
        print("   Please set OPENAI_API_KEY in .env file")
        return False

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        # Simple test request
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use cheaper model for testing
            messages=[
                {"role": "user", "content": "Say 'Hello from APE 2026!' and nothing else."}
            ],
            max_tokens=20
        )

        result = response.choices[0].message.content.strip()
        print(f"✅ SUCCESS: OpenAI API is working!")
        print(f"   Response: {result}")
        print(f"   Model: {response.model}")
        print(f"   Tokens: {response.usage.total_tokens}")
        return True

    except Exception as e:
        print(f"❌ FAIL: OpenAI API error: {e}")
        return False


# ============================================================================
# Test 2: Google Gemini API
# ============================================================================

def test_gemini():
    """Test Google Gemini API key."""
    print("\n2. Testing Google Gemini API...")
    print("-" * 70)

    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("❌ FAIL: Google API key not set")
        print("   Please set GOOGLE_API_KEY in .env file")
        return False

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)

        # Simple test request (use gemini-2.5-flash, latest model)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("Say 'Hello from APE 2026!' and nothing else.")

        result = response.text.strip()
        print(f"✅ SUCCESS: Google Gemini API is working!")
        print(f"   Response: {result}")
        print(f"   Model: gemini-pro")
        return True

    except Exception as e:
        print(f"❌ FAIL: Google Gemini API error: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False


# ============================================================================
# Test 3: DeepSeek API
# ============================================================================

def test_deepseek():
    """Test DeepSeek API key."""
    print("\n3. Testing DeepSeek API...")
    print("-" * 70)

    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    if not api_key or api_key == "your_deepseek_api_key_here":
        print("⚠️  SKIP: DeepSeek API key not set (optional)")
        print("   Set DEEPSEEK_API_KEY in .env file if you want to use DeepSeek")
        return None

    try:
        from openai import OpenAI

        # DeepSeek uses OpenAI-compatible API
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": "Say 'Hello from APE 2026!' and nothing else."}
            ],
            max_tokens=20
        )

        result = response.choices[0].message.content.strip()
        print(f"✅ SUCCESS: DeepSeek API is working!")
        print(f"   Response: {result}")
        print(f"   Model: {response.model}")
        return True

    except Exception as e:
        print(f"❌ FAIL: DeepSeek API error: {e}")
        return False


# ============================================================================
# Test 4: Anthropic (Claude) API
# ============================================================================

def test_anthropic():
    """Test Anthropic Claude API key."""
    print("\n4. Testing Anthropic (Claude) API...")
    print("-" * 70)

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key or api_key == "your_anthropic_api_key_here":
        print("⚠️  SKIP: Anthropic API key not set (optional for testing)")
        print("   Set ANTHROPIC_API_KEY in .env file if you want to use Claude")
        return None

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)

        response = client.messages.create(
            model="claude-3-haiku-20240307",  # Use cheaper model for testing
            max_tokens=20,
            messages=[
                {"role": "user", "content": "Say 'Hello from APE 2026!' and nothing else."}
            ]
        )

        result = response.content[0].text.strip()
        print(f"✅ SUCCESS: Anthropic API is working!")
        print(f"   Response: {result}")
        print(f"   Model: {response.model}")
        return True

    except Exception as e:
        print(f"❌ FAIL: Anthropic API error: {e}")
        return False


# ============================================================================
# Main Test Runner
# ============================================================================

def main():
    """Run all API tests."""
    results = {
        "OpenAI": test_openai(),
        "Gemini": test_gemini(),
        "DeepSeek": test_deepseek(),
        "Anthropic": test_anthropic()
    }

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    for service, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"

        print(f"{service:15} {status}")

    # Count results
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)

    print()
    print(f"Passed: {passed}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")
    print(f"Skipped: {skipped}/{len(results)}")

    if failed > 0:
        print("\n❌ Some API keys are not working. Please check your .env file.")
        sys.exit(1)
    elif passed == 0:
        print("\n⚠️  No API keys were tested. Please configure at least one API key.")
        sys.exit(1)
    else:
        print("\n✅ All configured API keys are working!")
        sys.exit(0)


if __name__ == "__main__":
    main()
