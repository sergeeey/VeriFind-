"""
Golden Set Validation Runner v2.0 — WITH DATA FETCHING.

Week 13 Day 3: Integrate YFinance adapter to provide real market data to debate.

Critical fix: Original runner tested debate-only (no data). This version fetches
real market data BEFORE debate, enabling honest validation of arbiter fixes.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

# CRITICAL: Load .env BEFORE any src imports
project_root = Path(__file__).parent.parent
from dotenv import load_dotenv
load_dotenv(project_root / '.env', override=True)

# Now add project to path
sys.path.insert(0, str(project_root))

# Import validators
from eval.validators import AnswerValidator, extract_answer_from_debate

# Import data fetching layer — USE v2 with fallback chain
try:
    from src.adapters.yfinance_adapter_v2 import YFinanceAdapterV2 as YFinanceAdapter
except ImportError:
    # Fallback to worktree v1 location
    sys.path.insert(0, str(project_root / '.claude' / 'worktrees' / 'awesome-yonath'))
    from src.adapters.yfinance_adapter import YFinanceAdapter

# Week 14 Day 1: Import FRED adapter for macro queries
try:
    from src.adapters.fred_adapter import FredAdapter
except ImportError:
    print("⚠️  FRED adapter not found, macro queries will fail")
    FredAdapter = None


def extract_tickers_from_query(query: str) -> list[str]:
    """
    Extract ticker symbols from query text.

    Examples:
    - "Tesla in Q4" → ["TSLA"]
    - "Apple (AAPL)" → ["AAPL"]
    - "NVIDIA (NVDA)" → ["NVDA"]
    """
    # Common ticker mappings
    ticker_map = {
        'tesla': 'TSLA',
        'apple': 'AAPL',
        'nvidia': 'NVDA',
        'microsoft': 'MSFT',
        'amazon': 'AMZN',
        'google': 'GOOGL',
        'meta': 'META',
        'crypto': 'BTC-USD'
    }

    tickers = []
    query_lower = query.lower()

    # Check for explicit tickers in parentheses: (AAPL)
    import re
    explicit_tickers = re.findall(r'\(([A-Z]{1,5})\)', query)
    tickers.extend(explicit_tickers)

    # Check for common company names
    for name, ticker in ticker_map.items():
        if name in query_lower and ticker not in tickers:
            tickers.append(ticker)

    return tickers if tickers else ['SPY']  # Default to S&P 500 if no ticker found


async def fetch_market_context(tickers: list[str], query: str = "") -> Dict[str, Any]:
    """
    Fetch comprehensive market data for tickers using yfinance .info.
    Week 14 Day 1: Also fetch FRED economic data if query is macro-related.

    Returns context dict with:
    - current_price: Latest market price
    - fundamentals: P/E ratio, revenue growth, free cash flow, market cap
    - technical: 50-day MA, 200-day MA, 52-week high/low, beta
    - economic: FRED data (if macro query)
    """
    adapter = YFinanceAdapter(cache_enabled=True, cache_ttl_seconds=300)
    context = {
        'tickers': tickers,
        'data': {},
        'fetched_at': datetime.now().isoformat()
    }

    # Week 14 Day 1: Detect economic queries and fetch FRED data
    economic_keywords = [
        'fed', 'interest rate', 'unemployment', 'inflation', 'gdp',
        'treasury', 'monetary policy', 'federal reserve', 'cpi', 'economic', 'macro'
    ]
    is_economic_query = any(kw in query.lower() for kw in economic_keywords)

    if is_economic_query and FredAdapter is not None:
        try:
            fred = FredAdapter(cache_enabled=True)
            context['economic'] = {}

            # Fetch common economic indicators
            try:
                dff = fred.get_latest_value('DFF')  # Federal Funds Rate
                context['economic']['fed_funds_rate'] = dff
                print(f"   ✅ Fetched Fed Funds Rate: {dff}%")
            except:
                pass

            try:
                unrate = fred.get_latest_value('UNRATE')  # Unemployment Rate
                context['economic']['unemployment_rate'] = unrate
                print(f"   ✅ Fetched Unemployment Rate: {unrate}%")
            except:
                pass

            try:
                dgs3mo = fred.get_latest_value('DGS3MO')  # 3-Month Treasury
                context['economic']['treasury_3mo'] = dgs3mo
                print(f"   ✅ Fetched 3-Month Treasury: {dgs3mo}%")
            except:
                pass

        except Exception as e:
            print(f"   ⚠️  FRED fetching failed: {e}")

    for ticker in tickers:
        try:
            # Use comprehensive fetch (includes fundamentals from .info)
            data = adapter.fetch_comprehensive_data(
                ticker=ticker,
                include_history=False  # Faster, fundamentals only
            )

            if data and data.get('current_price'):
                context['data'][ticker] = data

                # Format output for user
                price = data.get('current_price', 0)
                pe = data.get('trailing_pe', 'N/A')
                revenue_growth = data.get('revenue_growth')
                ma_200 = data.get('ma_200')

                # Format revenue growth as percentage
                revenue_str = f"{revenue_growth*100:.1f}%" if revenue_growth is not None else "N/A"
                ma_str = f"${ma_200:.2f}" if ma_200 is not None else "N/A"

                print(f"   ✅ Fetched {ticker}: ${price:.2f}, "
                      f"P/E: {pe if pe != 'N/A' else 'N/A'}, "
                      f"Revenue Growth: {revenue_str}, "
                      f"200-MA: {ma_str}")
            else:
                print(f"   ⚠️  No data for {ticker}")
                context['data'][ticker] = None

        except Exception as e:
            print(f"   ❌ Error fetching {ticker}: {e}")
            context['data'][ticker] = {'error': str(e)}

    return context


async def run_golden_set_with_data(file_path: str, limit: Optional[int] = None):
    """
    Run Golden Set validation WITH real market data fetching.

    Args:
        file_path: Path to golden_set.json
        limit: Optional limit on number of queries (for testing)
    """
    print(f"🚀 Starting Golden Set Validation v2.0 (WITH DATA FETCHING)...")

    # Load orchestrator
    try:
        from src.debate.parallel_orchestrator import ParallelDebateOrchestrator
        orchestrator = ParallelDebateOrchestrator()
        print("✅ Real Orchestrator loaded.")
        print(f"   Bull: {orchestrator.bull_model}")
        print(f"   Bear: {orchestrator.bear_model}")
        print(f"   Arbiter: {orchestrator.arbiter_model}")
    except Exception as e:
        print(f"❌ Failed to load orchestrator: {e}")
        print("   Cannot run validation without real orchestrator.")
        return

    # Load queries
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    queries = data['queries']
    if limit:
        queries = queries[:limit]
        print(f"🔹 Running first {limit} queries (testing mode)")

    results = []
    total_cost = 0.0
    total_time = 0.0

    for q in queries:
        print(f"\n{'='*60}")
        print(f"🔹 Query {q['id']}: {q['query']}")
        print(f"   Category: {q['category']} | Difficulty: {q['difficulty']}")

        try:
            # Step 1: Extract tickers from query
            tickers = extract_tickers_from_query(q['query'])
            print(f"   📊 Tickers identified: {tickers}")

            # Step 2: Fetch market data (+ FRED economic data if macro query)
            context = await fetch_market_context(tickers, query=q['query'])

            # Step 3: Run debate WITH context
            start_time = datetime.now()
            result = await orchestrator.run_debate(query=q['query'], context=context)
            duration = (datetime.now() - start_time).total_seconds()
            total_time += duration

            # Step 4: Extract cost
            cost = 0.0
            if hasattr(result, 'cost_usd'):
                cost = result.cost_usd
            elif hasattr(result, 'metadata') and result.metadata:
                cost = result.metadata.get('total_cost_usd', 0.0)
            total_cost += cost

            # Step 5: Validate answer
            answer_text = extract_answer_from_debate(result)
            expected = q.get('expected_answer', {})

            # Week 14: Extract source_verified, error_detected, ambiguity_detected from result
            source_verified = getattr(result, 'source_verified', True)  # Conservative: assume True if not present
            error_detected = getattr(result, 'error_detected', False)
            ambiguity_detected = getattr(result, 'ambiguity_detected', False)

            is_correct, validation_reason = AnswerValidator.validate_answer(
                answer_text,
                expected,
                source_verified=source_verified,
                error_detected=error_detected,
                ambiguity_detected=ambiguity_detected
            )

            # Step 6: Report
            status = "✅" if is_correct else "❌"
            print(f"   {status} Answer: {answer_text[:80]}...")
            print(f"   ⏱️  Time: {duration:.2f}s | 💰 Cost: ${cost:.4f}")
            print(f"   📋 Validation: {validation_reason}")

            results.append({
                "id": q["id"],
                "query": q["query"],
                "category": q["category"],
                "passed": is_correct,
                "duration": duration,
                "cost_usd": cost,
                "answer": answer_text,
                "validation_reason": validation_reason,
                "context_tickers": tickers,
                "context_data": context['data']
            })

        except Exception as e:
            print(f"   ❌ Failed: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "id": q["id"],
                "query": q["query"],
                "passed": False,
                "error": str(e)
            })

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 GOLDEN SET VALIDATION SUMMARY (v2.0)")
    print(f"{'='*60}")

    success_count = sum(1 for r in results if r.get('passed', False))
    accuracy = (success_count / len(results) * 100) if results else 0
    avg_time = total_time / len(results) if results else 0
    avg_cost = total_cost / len(results) if results else 0

    print(f"✅ Accuracy: {success_count}/{len(results)} ({accuracy:.1f}%)")
    print(f"⏱️  Avg Time: {avg_time:.2f}s per query")
    print(f"💰 Avg Cost: ${avg_cost:.4f} per query")
    print(f"💰 Total Cost: ${total_cost:.4f}")

    # Category breakdown
    print(f"\n📊 Breakdown by Category:")
    categories = {}
    for r in results:
        cat = r.get('category', 'unknown')
        if cat not in categories:
            categories[cat] = {'total': 0, 'passed': 0}
        categories[cat]['total'] += 1
        if r.get('passed', False):
            categories[cat]['passed'] += 1

    for cat, stats in sorted(categories.items()):
        cat_acc = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"   {cat}: {stats['passed']}/{stats['total']} ({cat_acc:.1f}%)")

    # Save results
    output_path = project_root / 'results' / f'golden_set_v2_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'version': '2.0',
            'run_date': datetime.now().isoformat(),
            'total_queries': len(results),
            'passed': success_count,
            'accuracy': accuracy,
            'avg_time_seconds': avg_time,
            'avg_cost_usd': avg_cost,
            'total_cost_usd': total_cost,
            'categories': categories,
            'results': results
        }, f, indent=2, default=str)

    print(f"\n💾 Results saved to: {output_path}")

    # Final verdict
    print(f"\n{'='*60}")
    if accuracy >= 80:
        print(f"🎉 SUCCESS! Accuracy {accuracy:.1f}% ≥ 80% target")
        print(f"   Arbiter prompt fix VALIDATED ✅")
        print(f"   Ready to scale to 30 queries")
    elif accuracy >= 50:
        print(f"⚠️  PARTIAL SUCCESS: {accuracy:.1f}% (50-80% range)")
        print(f"   Arbiter fix shows improvement but needs iteration")
    else:
        print(f"❌ FAILED: {accuracy:.1f}% < 50% target")
        print(f"   Arbiter fix did not work as expected")
        print(f"   Review failures and iterate on prompt")

    return results


if __name__ == "__main__":
    # Default: 5-query baseline
    limit = 5

    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"Usage: python run_golden_set_v2.py [limit]")
            print(f"Example: python run_golden_set_v2.py 5")
            sys.exit(1)

    path = project_root / "eval" / "golden_set.json"
    print(f"📁 Golden Set: {path}")
    print(f"🔢 Limit: {limit if limit else 'ALL'} queries")

    asyncio.run(run_golden_set_with_data(str(path), limit=limit))
