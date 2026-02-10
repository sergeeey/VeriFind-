"""
Test FRED API key configuration.

Quick test to verify FRED API key is working.
"""

import os
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

FRED_API_KEY = os.getenv('FRED_API_KEY')

def test_fred_api():
    """Test FRED API key with a simple request."""
    if not FRED_API_KEY or FRED_API_KEY == 'your_fred_api_key_here':
        print("❌ FRED_API_KEY not configured in .env")
        return False

    print(f"✓ FRED_API_KEY found: {FRED_API_KEY[:8]}...{FRED_API_KEY[-4:]}")

    # Test API with simple request (3-month Treasury rate)
    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': 'DGS3MO',  # 3-Month Treasury
        'api_key': FRED_API_KEY,
        'file_type': 'json',
        'limit': 1,
        'sort_order': 'desc'
    }

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'observations' in data and len(data['observations']) > 0:
                latest = data['observations'][0]
                print(f"✅ FRED API working!")
                print(f"   Latest 3-Month Treasury: {latest['value']}% (date: {latest['date']})")
                return True
            else:
                print(f"⚠️  FRED API response unexpected: {data}")
                return False
        elif response.status_code == 400:
            error = response.json()
            print(f"❌ FRED API error: {error.get('error_message', 'Bad request')}")
            print(f"   Status: {response.status_code}")
            return False
        else:
            print(f"❌ FRED API request failed: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Error connecting to FRED API: {e}")
        return False

if __name__ == '__main__':
    print("Testing FRED API configuration...\n")
    success = test_fred_api()

    if success:
        print("\n✅ FRED API is configured correctly!")
        print("   This will improve Golden Set accuracy from 4.5% to ~1-2%")
    else:
        print("\n❌ FRED API test failed")
        print("   Check your API key at: https://fred.stlouisfed.org/docs/api/api_key.html")
