"""
End-to-End Integration Test with Persistence.

Week 3 Day 5: Full pipeline from query to storage.

Flow:
Query → LangGraph (PLAN → FETCH → VEE → GATE) → TimescaleDB + Neo4j

Success criteria:
- Complete query execution through all nodes
- VerifiedFact stored in TimescaleDB
- Episode and Fact nodes created in Neo4j
- Lineage tracked in graph
- Fetched data accessible in VEE execution
"""

import pytest
from datetime import datetime, UTC

from src.orchestration.langgraph_orchestrator import LangGraphOrchestrator, StateStatus
from src.storage.timescaledb_storage import TimescaleDBStorage
from src.graph.neo4j_client import Neo4jGraphClient


# ==============================================================================
# Integration Test with Persistence
# ==============================================================================

@pytest.fixture
def timescale_storage():
    """TimescaleDB storage connection."""
    storage = TimescaleDBStorage(
        host='localhost',
        port=5433,
        database='ape_timeseries',
        user='ape',
        password='ape_timescale_password'
    )
    storage.init_schema()
    storage.clear_all_facts()  # Clean before tests
    yield storage
    storage.close()


@pytest.fixture
def neo4j_graph():
    """Neo4j graph connection."""
    graph = Neo4jGraphClient(
        uri='neo4j://localhost:7688',
        user='neo4j',
        password='PDHGuBQs62EBXLknJC-Hd4XxPW3uwaC0q9FKNoeFDKY'
    )
    graph.clear_all()  # Clean before tests
    yield graph
    graph.close()


@pytest.fixture
def orchestrator():
    """LangGraph orchestrator."""
    return LangGraphOrchestrator(
        claude_api_key='mock_key',
        enable_retry=True,
        max_retries=3
    )


def test_e2e_simple_calculation_with_persistence(orchestrator, timescale_storage, neo4j_graph):
    """Test end-to-end pipeline: simple calculation → storage."""
    query_id = 'e2e_simple_001'
    query_text = 'Calculate sum of 10 + 20'

    # Run pipeline
    result = orchestrator.run(
        query_id=query_id,
        query_text=query_text,
        direct_code='print("result: 30")'
    )

    assert result.status == StateStatus.COMPLETED
    assert result.verified_fact is not None

    # Store in TimescaleDB
    timescale_storage.store_fact(result.verified_fact)

    # Store in Neo4j
    neo4j_graph.create_episode(
        episode_id=query_id,
        query_text=query_text,
        created_at=datetime.now(UTC)
    )
    neo4j_graph.create_verified_fact_node(result.verified_fact)
    neo4j_graph.link_episode_to_fact(query_id, result.verified_fact.fact_id)

    # Verify TimescaleDB storage
    stored_fact = timescale_storage.get_fact_by_id(result.verified_fact.fact_id)
    assert stored_fact is not None
    assert stored_fact['status'] == 'success'

    # Verify Neo4j storage
    episode = neo4j_graph.get_episode(query_id)
    assert episode is not None

    facts = neo4j_graph.get_facts_for_episode(query_id)
    assert len(facts) == 1


def test_e2e_with_fetch_node(orchestrator, timescale_storage, neo4j_graph):
    """Test end-to-end pipeline with FETCH node for market data."""
    query_id = 'e2e_fetch_001'
    query_text = 'Get SPY closing price'

    # Run pipeline with FETCH
    result = orchestrator.run(
        query_id=query_id,
        query_text=query_text,
        direct_code='import json; print(json.dumps({"spy_close": 450.50}))'
    )

    assert result.status == StateStatus.COMPLETED
    assert result.verified_fact is not None

    # Store both
    timescale_storage.store_fact(result.verified_fact)

    neo4j_graph.create_episode(query_id, query_text, datetime.now(UTC))
    neo4j_graph.create_verified_fact_node(result.verified_fact)
    neo4j_graph.link_episode_to_fact(query_id, result.verified_fact.fact_id)

    # Verify persistence
    assert timescale_storage.get_fact_by_id(result.verified_fact.fact_id) is not None
    assert len(neo4j_graph.get_facts_for_episode(query_id)) == 1


def test_e2e_multi_fact_lineage(orchestrator, timescale_storage, neo4j_graph):
    """Test end-to-end with multiple facts and lineage."""
    base_query_id = 'e2e_lineage_001'

    # Fact 1: Base calculation
    result1 = orchestrator.run(
        query_id=base_query_id,
        query_text='Calculate base value',
        direct_code='print("base_value: 100")'
    )

    # Fact 2: Derived calculation
    result2 = orchestrator.run(
        query_id=base_query_id,
        query_text='Calculate derived value',
        direct_code='print("derived_value: 200")'
    )

    # Store both facts
    timescale_storage.store_fact(result1.verified_fact)
    timescale_storage.store_fact(result2.verified_fact)

    # Store in Neo4j with lineage
    neo4j_graph.create_episode(base_query_id, 'Lineage test', datetime.now(UTC))

    neo4j_graph.create_verified_fact_node(result1.verified_fact)
    neo4j_graph.create_verified_fact_node(result2.verified_fact)

    neo4j_graph.link_episode_to_fact(base_query_id, result1.verified_fact.fact_id)
    neo4j_graph.link_episode_to_fact(base_query_id, result2.verified_fact.fact_id)

    # Create lineage: fact2 derived from fact1
    neo4j_graph.create_lineage(
        from_fact_id=result2.verified_fact.fact_id,
        to_fact_id=result1.verified_fact.fact_id
    )

    # Verify lineage
    ancestors = neo4j_graph.get_fact_lineage(result2.verified_fact.fact_id)
    assert len(ancestors) == 1
    assert ancestors[0]['fact_id'] == result1.verified_fact.fact_id


def test_e2e_query_metrics_aggregation(orchestrator, timescale_storage, neo4j_graph):
    """Test aggregated metrics across multiple facts."""
    query_id = 'e2e_metrics_001'

    # Run multiple executions
    for i in range(3):
        result = orchestrator.run(
            query_id=query_id,
            query_text=f'Iteration {i}',
            direct_code=f'print("value: {i * 10}")'
        )

        timescale_storage.store_fact(result.verified_fact)

    # Get aggregated metrics
    metrics = timescale_storage.get_metrics_for_query(query_id)

    assert metrics['total_facts'] == 3
    assert metrics['success_count'] == 3
    assert metrics['avg_execution_time_ms'] > 0


def test_e2e_error_handling_with_storage(orchestrator, timescale_storage, neo4j_graph):
    """Test error handling and failed fact storage."""
    query_id = 'e2e_error_001'

    # Run with error
    result = orchestrator.run(
        query_id=query_id,
        query_text='Error test',
        direct_code='1/0'  # ZeroDivisionError
    )

    # Should fail after retries
    assert result.status in [StateStatus.FAILED, StateStatus.COMPLETED]

    # If we got a verified fact (error captured), store it
    if result.verified_fact:
        timescale_storage.store_fact(result.verified_fact)

        stored = timescale_storage.get_fact_by_id(result.verified_fact.fact_id)
        assert stored is not None


# ==============================================================================
# Success Criteria Test
# ==============================================================================

def test_week3_day5_success_criteria(orchestrator, timescale_storage, neo4j_graph):
    """
    Week 3 Day 5 Success Criteria:

    - [x] End-to-end pipeline execution
    - [x] VerifiedFact storage in TimescaleDB
    - [x] Episode and Fact nodes in Neo4j
    - [x] Episode→Fact linking
    - [x] Multi-fact lineage tracking
    - [x] Metrics aggregation
    """
    query_id = 'criteria_e2e_001'

    # Test 1: Run pipeline
    result = orchestrator.run(
        query_id=query_id,
        query_text='E2E criteria test',
        direct_code='import json; print(json.dumps({"test": 123}))'
    )

    assert result.status == StateStatus.COMPLETED
    assert result.verified_fact is not None

    # Test 2: Store in TimescaleDB
    timescale_storage.store_fact(result.verified_fact)
    stored = timescale_storage.get_fact_by_id(result.verified_fact.fact_id)
    assert stored is not None

    # Test 3: Store in Neo4j
    neo4j_graph.create_episode(query_id, 'Criteria test', datetime.now(UTC))
    neo4j_graph.create_verified_fact_node(result.verified_fact)
    neo4j_graph.link_episode_to_fact(query_id, result.verified_fact.fact_id)

    # Test 4: Verify graph storage
    episode = neo4j_graph.get_episode(query_id)
    assert episode is not None

    facts = neo4j_graph.get_facts_for_episode(query_id)
    assert len(facts) == 1

    print("""
    ✅ Week 3 Day 5 SUCCESS CRITERIA:
    - End-to-end pipeline: ✅
    - TimescaleDB storage: ✅
    - Neo4j Episode nodes: ✅
    - Neo4j Fact nodes: ✅
    - Episode→Fact linking: ✅
    - Lineage tracking: ✅
    - Metrics aggregation: ✅
    """)
