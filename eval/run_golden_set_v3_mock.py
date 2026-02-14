"""
Golden Set Validation Runner v3.0 — WITH MOCK DATA (Plan B).

Week 13 Day 3: Use mock market data to validate arbiter prompt fix in isolation.

Rationale: YFinance API has rate limiting issues. Mock data allows us to prove
that arbiter fix works WITHOUT external API dependencies.

If this passes >50%, we know fix works. Can validate with real data later.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# CRITICAL: Load .env BEFORE any src imports
project_root = Path(__file__).parent.parent
from dotenv import load_dotenv
load_dotenv(project_root / '.env', override=True)

# Now add project to path
sys.path.insert(0, str(project_root))

# Import validators
from eval.validators import AnswerValidator, extract_answer_from_debate


def get_mock_context(query: str) -> dict:
    """
    Generate realistic mock market data based on query content.

    This simulates what YFinance would return, allowing isolated testing
    of arbiter prompt fix without external API dependencies.
    """
    query_lower = query.lower()

    # Tesla Q4 2025 revenue growth
    if 'tesla' in query_lower and 'revenue' in query_lower:
        return {
            'tickers': ['TSLA'],
            'data': {
                'TSLA': {
                    'latest_price': 245.32,
                    'sma_200': 220.15,
                    'q4_revenue_2024': 25.17,  # billions
                    'q4_revenue_2025_expected': 30.5,  # +21.2% YoY
                    'yoy_growth': 0.212,  # 21.2%
                }
            }
        }

    # Apple P/E ratio
    elif 'apple' in query_lower and 'p/e' in query_lower:
        return {
            'tickers': ['AAPL'],
            'data': {
                'AAPL': {
                    'latest_price': 187.45,
                    'sma_200': 175.30,
                    'eps_ttm': 6.42,  # trailing twelve months
                    'pe_ratio': 29.2,  # 187.45 / 6.42
                    'sector_avg_pe': 25.5
                }
            }
        }

    # NVIDIA vs 200-day SMA
    elif 'nvidia' in query_lower or 'nvda' in query_lower:
        return {
            'tickers': ['NVDA'],
            'data': {
                'NVDA': {
                    'latest_price': 521.18,
                    'sma_200': 485.32,
                    'trading_above_sma': True,  # 521.18 > 485.32
                    'distance_from_sma_pct': 7.4  # (521.18 - 485.32) / 485.32
                }
            }
        }

    # Crypto compliance check
    elif 'crypto' in query_lower or 'btc' in query_lower:
        return {
            'tickers': ['BTC-USD'],
            'data': {
                'BTC-USD': {
                    'latest_price': 52340.15,
                    'volatility_30d': 0.52,  # 52% annualized
                    'warning': 'HIGH VOLATILITY ASSET - NOT SUITABLE FOR ALL INVESTORS'
                }
            }
        }

    # Fed interest rate macro question
    elif 'fed' in query_lower or 'interest rate' in query_lower:
        return {
            'tickers': ['SPY'],
            'data': {
                'SPY': {
                    'latest_price': 485.32,
                    'sma_200': 465.18,
                    'fed_funds_rate': 0.0525,  # 5.25%
                    'tech_sector_pe': 32.5,
                    'historical_avg_pe': 28.0
                }
            }
        }

    # Default empty context
    return {'tickers': [], 'data': {}}


async def run_golden_set_mock(file_path: str, limit: int = 5):
    """
    Run Golden Set validation with MOCK data.

    Args:
        file_path: Path to golden_set.json
        limit: Number of queries to test
    """
    print(f"🚀 Starting Golden Set Validation v3.0 (MOCK DATA)...")
    print(f"⚠️  Using mock data to isolate arbiter prompt fix validation")

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
        return

    # Load queries
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    queries = data['queries'][:limit]
    print(f"🔹 Testing first {limit} queries")

    results = []
    total_cost = 0.0
    total_time = 0.0

    for q in queries:
        print(f"\n{'='*60}")
        print(f"🔹 Query {q['id']}: {q['query']}")
        print(f"   Category: {q['category']} | Difficulty: {q['difficulty']}")

        try:
            # Generate mock context based on query
            context = get_mock_context(q['query'])
            print(f"   📊 Mock Data: {list(context.get('data', {}).keys())}")

            # Run debate WITH mock context
            start_time = datetime.now()
            result = await orchestrator.run_debate(query=q['query'], context=context)
            duration = (datetime.now() - start_time).total_seconds()
            total_time += duration

            # Extract cost
            cost = result.cost_usd if hasattr(result, 'cost_usd') else 0.0
            total_cost += cost

            # Validate answer
            answer_text = extract_answer_from_debate(result)
            expected = q.get('expected_answer', {})

            is_correct, validation_reason = AnswerValidator.validate_answer(
                answer_text, expected
            )

            # Report
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
                "mock_data": context['data']
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
    print(f"📊 GOLDEN SET VALIDATION SUMMARY (v3.0 MOCK)")
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
    output_path = project_root / 'results' / f'golden_set_v3_mock_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'version': '3.0-mock',
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
        print(f"   Ready to test with real data or scale to 30 queries")
    elif accuracy >= 50:
        print(f"⚠️  PARTIAL SUCCESS: {accuracy:.1f}% (50-80% range)")
        print(f"   Arbiter fix shows improvement but needs iteration")
    else:
        print(f"❌ FAILED: {accuracy:.1f}% < 50% target")
        print(f"   Arbiter fix did not work as expected")
        print(f"   Review failures and iterate on prompt")

    return results


if __name__ == "__main__":
    limit = 5
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"Usage: python run_golden_set_v3_mock.py [limit]")
            sys.exit(1)

    path = project_root / "eval" / "golden_set.json"
    asyncio.run(run_golden_set_mock(str(path), limit=limit))