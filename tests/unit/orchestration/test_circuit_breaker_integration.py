"""Unit tests for orchestrator circuit breaker integration."""

import time

from src.orchestration.langgraph_orchestrator import (
    LangGraphOrchestrator,
    APEState,
    StateStatus,
)
from src.resilience.circuit_breaker import CircuitState
from src.truth_boundary.gate import VerifiedFact


def _verified_fact() -> VerifiedFact:
    from datetime import datetime, UTC

    return VerifiedFact(
        fact_id="fact_cb_001",
        query_id="query_cb_001",
        plan_id="plan_cb_001",
        code_hash="hash123",
        status="success",
        extracted_values={"value": 1.23},
        execution_time_ms=100,
        memory_used_mb=10.0,
        created_at=datetime.now(UTC),
        source_code="print('ok')",
        confidence_score=0.8,
    )


def test_fetch_node_fails_when_market_data_circuit_open():
    orchestrator = LangGraphOrchestrator(enable_retry=False, use_real_llm=False)
    orchestrator.market_data_breaker.state = CircuitState.OPEN
    orchestrator.market_data_breaker.last_failure_time = time.time()

    state = APEState(
        query_id="q_fetch_cb",
        query_text="Analyze AAPL",
        status=StateStatus.PLANNING,
        plan={
            "requires_data": True,
            "data_requirements": [
                {
                    "ticker": "AAPL",
                    "data_type": "ohlcv",
                    "source": "yfinance",
                    "start_date": "2025-01-01",
                    "end_date": "2025-06-01",
                }
            ],
            "interval": "1d",
        },
    )

    result = orchestrator.fetch_node(state)

    assert result.status == StateStatus.FAILED
    assert "open" in (result.error_message or "").lower()


def test_debate_node_falls_back_to_mock_when_llm_circuit_open(monkeypatch):
    class FakeDebateAdapter:
        def generate_debate(self, context, original_confidence):
            raise AssertionError("Should not be called while circuit is OPEN")

        def get_stats(self):
            return {}

    monkeypatch.setattr(
        "src.orchestration.langgraph_orchestrator.RealLLMDebateAdapter",
        lambda provider="deepseek", enable_debate=True: FakeDebateAdapter(),
    )

    orchestrator = LangGraphOrchestrator(enable_retry=False, use_real_llm=True)
    orchestrator.llm_debate_breaker.state = CircuitState.OPEN
    orchestrator.llm_debate_breaker.last_failure_time = time.time()

    state = APEState(
        query_id="q_debate_cb",
        query_text="Analyze AAPL valuation",
        status=StateStatus.VALIDATING,
        verified_fact=_verified_fact(),
    )

    result = orchestrator.debate_node(state)

    assert result.status == StateStatus.COMPLETED
    assert result.synthesis is not None
    assert result.debate_reports is not None
    assert len(result.debate_reports) == 3
