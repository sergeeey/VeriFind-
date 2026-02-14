import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# CRITICAL: Load .env BEFORE any src imports
project_root = Path(__file__).parent.parent
from dotenv import load_dotenv
load_dotenv(project_root / '.env', override=True)

# Now add project to path
sys.path.insert(0, str(project_root))

# Week 13 Day 2: Import validators
from eval.validators import AnswerValidator, extract_answer_from_debate

# Заглушка оркестратора для первого прогона
class MockOrchestrator:
    async def run_debate(self, query, context=None):
        print(f"   [AI Thinking] Analyzing: {query[:30]}...")
        await asyncio.sleep(0.5)  # Эмуляция обработки
        # Эмуляция ответа
        return {
            "synthesis": {
                "recommendation": "HOLD",
                "confidence": 0.85,
                "analysis": "Based on technical indicators and macro data..."
            },
            "metadata": {"cost_usd": 0.005, "latency_ms": 1200}
        }

async def run_golden_set(file_path):
    print(f"🚀 Starting Golden Set Validation...")
    
    try:
        # Пытаемся импортировать реальный оркестратор
        from src.debate.parallel_orchestrator import MultiLLMDebateOrchestrator
        orchestrator = MultiLLMDebateOrchestrator()
        print("✅ Real Orchestrator loaded.")
        print(f"   Bull: {orchestrator.bull_model}")
        print(f"   Bear: {orchestrator.bear_model}")
        print(f"   Arbiter: {orchestrator.arbiter_model}")
    except ImportError as e:
        print(f"⚠️  Real Orchestrator not found: {e}. Using MOCK for testing.")
        orchestrator = MockOrchestrator()
    except Exception as e:
        print(f"⚠️  Error loading Orchestrator: {e}. Using MOCK.")
        orchestrator = MockOrchestrator()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = []
    
    for q in data['queries']:
        print(f"\n🔹 Query {q['id']}: {q['query']}")
        try:
            start_time = datetime.now()
            result = await orchestrator.run_debate(query=q['query'])
            duration = (datetime.now() - start_time).total_seconds()

            # Week 13 Day 2: Real validation (not just field existence)
            answer_text = extract_answer_from_debate(result)
            expected = q.get('expected_answer', {})

            is_correct, validation_reason = AnswerValidator.validate_answer(
                answer_text, expected
            )

            status = "✅" if is_correct else "❌"
            print(f"   {status} Result: {answer_text[:60]}... (Time: {duration:.2f}s)")
            print(f"      Validation: {validation_reason}")

            results.append({
                "id": q["id"],
                "passed": is_correct,
                "duration": duration,
                "answer": answer_text,
                "validation_reason": validation_reason,
                "response": result
            })
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results.append({"id": q["id"], "passed": False, "error": str(e)})
    
    success_count = sum(1 for r in results if r['passed'])
    print(f"\n📊 SUMMARY: {success_count}/{len(results)} passed.")

if __name__ == "__main__":
    path = "eval/golden_set.json"
    if len(sys.argv) > 1:
        path = sys.argv[1]
    asyncio.run(run_golden_set(path))
