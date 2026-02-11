"""Neo4j resilience tests for LangGraph orchestrator."""

from src.orchestration.langgraph_orchestrator import LangGraphOrchestrator, StateStatus


def test_orchestrator_runs_when_neo4j_unavailable(monkeypatch):
    """Pipeline must complete even when Neo4j client initialization fails."""
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)

    orchestrator = LangGraphOrchestrator(
        claude_api_key="mock_key",
        use_real_llm=False,
        enable_retry=True,
        max_retries=2
    )

    assert orchestrator.neo4j_client is None

    result = orchestrator.run(
        query_id="neo4j_resilience_001",
        query_text="Calculate 10 + 20",
        direct_code='print("result: 30")'
    )

    assert result.status == StateStatus.COMPLETED
    assert result.verified_fact is not None
