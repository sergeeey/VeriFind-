"""
Test script to verify all API keys are working.
Week 13 Day 1: API key validation
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables manually (dotenv has parsing issues)
import sys
from pathlib import Path

env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
else:
    print("⚠️ .env file not found!")

print("=" * 60)
print("API KEYS VALIDATION TEST")
print("=" * 60)
print()


async def test_deepseek():
    """Test DeepSeek API key."""
    print("🔵 Testing DeepSeek API...")
    try:
        from openai import AsyncOpenAI

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            print("❌ DeepSeek API key not found in .env")
            return False

        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": "Say 'DeepSeek API works!' in one sentence."}
            ],
            max_tokens=20
        )

        result = response.choices[0].message.content
        print(f"✅ DeepSeek API: Working! Response: {result[:50]}...")
        print(f"   Tokens used: {response.usage.total_tokens}")
        return True

    except Exception as e:
        print(f"❌ DeepSeek API Error: {e}")
        return False


async def test_openai():
    """Test OpenAI API key."""
    print("\n🟢 Testing OpenAI API...")
    try:
        from openai import AsyncOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OpenAI API key not found in .env")
            return False

        client = AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Say 'OpenAI API works!' in one sentence."}
            ],
            max_tokens=20
        )

        result = response.choices[0].message.content
        print(f"✅ OpenAI API: Working! Response: {result[:50]}...")
        print(f"   Tokens used: {response.usage.total_tokens}")
        return True

    except Exception as e:
        print(f"❌ OpenAI API Error: {e}")
        return False


async def test_anthropic():
    """Test Anthropic Claude API key."""
    print("\n🟣 Testing Anthropic Claude API...")
    try:
        from anthropic import AsyncAnthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("❌ Anthropic API key not found in .env")
            return False

        client = AsyncAnthropic(api_key=api_key)

        response = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=20,
            messages=[
                {"role": "user", "content": "Say 'Claude API works!' in one sentence."}
            ]
        )

        result = response.content[0].text
        print(f"✅ Anthropic API: Working! Response: {result[:50]}...")
        print(f"   Tokens used: {response.usage.input_tokens + response.usage.output_tokens}")
        return True

    except Exception as e:
        print(f"❌ Anthropic API Error: {e}")
        return False


async def test_gemini():
    """Test Google Gemini API key."""
    print("\n🔴 Testing Google Gemini API...")
    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ Gemini API key not found in .env")
            return False

        genai.configure(api_key=api_key)
        # Use Gemini 1.5 Flash (latest stable as of Feb 2026)
        model = genai.GenerativeModel('gemini-1.5-flash')

        response = model.generate_content("Say 'Gemini API works!' in one sentence.")

        result = response.text
        print(f"✅ Gemini API: Working! Response: {result[:50]}...")
        return True

    except Exception as e:
        print(f"❌ Gemini API Error: {e}")
        return False


def test_fred():
    """Test FRED API key."""
    print("\n🟡 Testing FRED API...")
    try:
        from fredapi import Fred

        api_key = os.getenv("FRED_API_KEY")
        if not api_key:
            print("❌ FRED API key not found in .env")
            return False

        fred = Fred(api_key=api_key)

        # Get latest GDP data
        data = fred.get_series_latest_release('GDP')
        latest_gdp = data.iloc[-1]

        print(f"✅ FRED API: Working! Latest US GDP: ${latest_gdp:.2f} billion")
        return True

    except Exception as e:
        print(f"❌ FRED API Error: {e}")
        return False


async def main():
    """Run all API tests."""
    results = {}

    # Test LLM APIs (async)
    results['deepseek'] = await test_deepseek()
    results['openai'] = await test_openai()
    results['anthropic'] = await test_anthropic()
    results['gemini'] = await test_gemini()

    # Test FRED API (sync)
    results['fred'] = test_fred()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    working = sum(1 for v in results.values() if v)
    total = len(results)

    for service, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {service.upper()}: {'Working' if status else 'Failed'}")

    print()
    print(f"Total: {working}/{total} APIs working ({working/total*100:.0f}%)")

    if working == total:
        print("\n🎉 All API keys are valid and working!")
    else:
        print(f"\n⚠️ {total - working} API(s) failed. Check keys and quotas.")

    return working == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
