"""Tests for query history persistence in orchestrator."""

from datetime import datetime, UTC

import pytest

from src.orchestration.langgraph_orchestrator import APEState, LangGraphOrchestrator, StateStatus
from src.truth_boundary.gate import VerifiedFact


class _FakeHistoryStore:
    def __init__(self):
        self.saved = None

    @staticmethod
    def extract_ticker_mentions(query_text: str):
        return ["AAPL"] if "AAPL" in query_text.upper() else []

    def save_entry(self, **kwargs):
        self.saved = kwargs


@pytest.mark.asyncio
async def test_process_query_async_persists_history(monkeypatch):
    orchestrator = LangGraphOrchestrator(use_real_llm=False, enable_retry=False)
    fake_history = _FakeHistoryStore()
    orchestrator.query_history_store = fake_history

    verified_fact = VerifiedFact(
        fact_id="fact_hist_001",
        query_id="query_hist_001",
        plan_id="plan_hist_001",
        code_hash="hash001",
        status="success",
        extracted_values={"price": 123.45},
        execution_time_ms=1000,
        memory_used_mb=30.0,
        created_at=datetime.now(UTC),
        statement="AAPL price is 123.45",
    )

    def _fake_run(query_id, query_text, direct_code, use_plan):
        state = APEState.from_query(query_id=query_id, query_text=query_text)
        state.status = StateStatus.COMPLETED
        state.verified_fact = verified_fact
        return state

    monkeypatch.setattr(orchestrator, "run", _fake_run)

    result = await orchestrator.process_query_async(
        query_id="query_hist_001",
        query_text="What is AAPL price?",
    )

    assert result["status"] == "completed"
    assert fake_history.saved is not None
    assert fake_history.saved["query_id"] == "query_hist_001"
    assert fake_history.saved["status"] == "completed"
    assert fake_history.saved["ticker_mentions"] == ["AAPL"]
