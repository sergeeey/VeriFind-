"""
Unit Tests for Parallel Multi-Agent Orchestrator
Week 7 Day 1

Tests for parallel execution, agent coordination, and message passing.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from src.orchestration.parallel_orchestrator import (
    ParallelOrchestrator,
    ParallelAgent,
    AgentRole,
    AgentTask,
    AgentMessage,
    MessageType,
    SharedState
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def shared_state():
    """Create shared state for testing."""
    return SharedState(session_id="test_session_123")


@pytest.fixture
def orchestrator():
    """Create parallel orchestrator for testing."""
    return ParallelOrchestrator(max_parallel_agents=5)


@pytest.fixture
async def initialized_orchestrator(orchestrator):
    """Create initialized orchestrator with session."""
    await orchestrator.initialize_session("Test query")
    return orchestrator


# ============================================================================
# SharedState Tests
# ============================================================================

@pytest.mark.asyncio
async def test_shared_state_set_get_result(shared_state):
    """Test thread-safe result storage and retrieval."""
    task_id = "task_123"
    result = {"value": 42, "status": "success"}

    # Set result
    await shared_state.set_result(task_id, result)

    # Get result
    retrieved = await shared_state.get_result(task_id)

    assert retrieved == result
    assert retrieved["value"] == 42


@pytest.mark.asyncio
async def test_shared_state_add_fact(shared_state):
    """Test thread-safe fact addition."""
    from src.truth_boundary.gate import VerifiedFact

    fact = VerifiedFact(
        fact_id="fact_1",
        query_id="query_1",
        statement="Test fact",
        value=100.0,
        confidence_score=0.9,
        source_code="test code",
        execution_result={}
    )

    await shared_state.add_fact(fact)

    assert len(shared_state.verified_facts) == 1
    assert shared_state.verified_facts[0].statement == "Test fact"


@pytest.mark.asyncio
async def test_shared_state_concurrent_access(shared_state):
    """Test concurrent access to shared state."""
    async def set_result(task_id: str, value: int):
        await shared_state.set_result(task_id, {"value": value})

    # Run 10 concurrent writes
    tasks = [set_result(f"task_{i}", i) for i in range(10)]
    await asyncio.gather(*tasks)

    # Verify all results stored
    assert len(shared_state.task_results) == 10
    for i in range(10):
        result = await shared_state.get_result(f"task_{i}")
        assert result["value"] == i


# ============================================================================
# ParallelAgent Tests
# ============================================================================

def test_agent_creation(shared_state):
    """Test agent creation with role."""
    agent = ParallelAgent(
        agent_id="agent_1",
        role=AgentRole.PLANNER,
        shared_state=shared_state
    )

    assert agent.agent_id == "agent_1"
    assert agent.role == AgentRole.PLANNER
    assert agent.tasks_completed == 0
    assert agent.tasks_failed == 0


@pytest.mark.asyncio
async def test_agent_send_message(shared_state):
    """Test agent message sending."""
    agent = ParallelAgent(
        agent_id="agent_1",
        role=AgentRole.PLANNER,
        shared_state=shared_state
    )

    message = await agent.send_message(
        receiver_id="agent_2",
        message_type=MessageType.TASK_ASSIGNMENT,
        payload={"task": "test"}
    )

    assert message.sender_id == "agent_1"
    assert message.receiver_id == "agent_2"
    assert message.message_type == MessageType.TASK_ASSIGNMENT
    assert message.payload["task"] == "test"


@pytest.mark.asyncio
async def test_agent_execute_planning_task(shared_state):
    """Test agent executing planning task."""
    agent = ParallelAgent(
        agent_id="planner_1",
        role=AgentRole.PLANNER,
        shared_state=shared_state
    )

    task = AgentTask(
        task_id="task_1",
        agent_id="planner_1",
        query="Calculate Sharpe ratio of SPY"
    )

    result = await agent.execute_task(task)

    assert task.status == "completed"
    assert task.result is not None
    assert "description" in result
    assert agent.tasks_completed == 1


@pytest.mark.asyncio
async def test_agent_execute_aggregation_task(shared_state):
    """Test agent executing aggregation task."""
    # Pre-populate shared state with dependency results
    await shared_state.set_result("task_1", {"value": 1.5})
    await shared_state.set_result("task_2", {"value": 1.8})

    agent = ParallelAgent(
        agent_id="aggregator_1",
        role=AgentRole.AGGREGATOR,
        shared_state=shared_state
    )

    task = AgentTask(
        task_id="task_agg",
        agent_id="aggregator_1",
        query="Aggregate results",
        dependencies=["task_1", "task_2"]
    )

    result = await agent.execute_task(task)

    assert task.status == "completed"
    assert "combined_results" in result
    assert len(result["combined_results"]) == 2


@pytest.mark.asyncio
async def test_agent_task_failure_handling(shared_state):
    """Test agent handles task failures gracefully."""
    agent = ParallelAgent(
        agent_id="planner_1",
        role=AgentRole.PLANNER,
        shared_state=shared_state
    )

    # Create task with invalid context to trigger error
    task = AgentTask(
        task_id="task_fail",
        agent_id="planner_1",
        query="",  # Empty query should cause error
        context={"invalid": "data"}
    )

    # Mock _execute_planning to raise exception
    async def mock_execute_planning(task):
        raise ValueError("Test error")

    agent._execute_planning = mock_execute_planning

    with pytest.raises(ValueError):
        await agent.execute_task(task)

    assert task.status == "failed"
    assert task.error == "Test error"
    assert agent.tasks_failed == 1


# ============================================================================
# ParallelOrchestrator Tests
# ============================================================================

def test_orchestrator_creation(orchestrator):
    """Test orchestrator initialization."""
    assert orchestrator.max_parallel_agents == 5
    assert len(orchestrator.agents) == 0
    assert orchestrator.shared_state is None


@pytest.mark.asyncio
async def test_orchestrator_initialize_session(orchestrator):
    """Test session initialization."""
    session_id = await orchestrator.initialize_session(
        query="Test query",
        context={"user": "test"}
    )

    assert session_id is not None
    assert orchestrator.shared_state is not None
    assert orchestrator.shared_state.session_id == session_id
    assert orchestrator.shared_state.global_context["user"] == "test"


@pytest.mark.asyncio
async def test_orchestrator_create_agent(initialized_orchestrator):
    """Test agent creation via orchestrator."""
    agent = initialized_orchestrator.create_agent(role=AgentRole.PLANNER)

    assert agent.agent_id.startswith("planner_")
    assert agent.role == AgentRole.PLANNER
    assert agent.agent_id in initialized_orchestrator.agents


@pytest.mark.asyncio
async def test_orchestrator_extract_tickers():
    """Test ticker extraction from query."""
    orchestrator = ParallelOrchestrator()

    query1 = "Compare AAPL, MSFT, GOOGL"
    tickers1 = orchestrator._extract_tickers(query1)
    assert set(tickers1) == {"AAPL", "MSFT", "GOOGL"}

    query2 = "Calculate Sharpe ratio of SPY for 2023"
    tickers2 = orchestrator._extract_tickers(query2)
    assert "SPY" in tickers2

    query3 = "No tickers here"
    tickers3 = orchestrator._extract_tickers(query3)
    assert len(tickers3) == 0


@pytest.mark.asyncio
async def test_orchestrator_decompose_single_ticker_query(initialized_orchestrator):
    """Test query decomposition for single ticker."""
    query = "Calculate Sharpe ratio of SPY for 2023"

    tasks = await initialized_orchestrator.decompose_query(query)

    # Single ticker = 1 task
    assert len(tasks) == 1
    assert tasks[0].query == query
    assert len(tasks[0].dependencies) == 0


@pytest.mark.asyncio
async def test_orchestrator_decompose_multi_ticker_query(initialized_orchestrator):
    """Test query decomposition for multiple tickers."""
    query = "Compare Sharpe ratios of AAPL, MSFT, GOOGL for 2023"

    tasks = await initialized_orchestrator.decompose_query(query)

    # 3 tickers + 1 aggregation = 4 tasks
    assert len(tasks) == 4

    # First 3 tasks should be for individual tickers
    ticker_tasks = tasks[:3]
    for task in ticker_tasks:
        assert len(task.dependencies) == 0
        assert "ticker" in task.context

    # Last task should be aggregation with dependencies
    agg_task = tasks[3]
    assert len(agg_task.dependencies) == 3
    assert agg_task.query.startswith("Aggregate")


@pytest.mark.asyncio
async def test_orchestrator_assign_tasks(initialized_orchestrator):
    """Test task assignment to agents."""
    tasks = [
        AgentTask(task_id="task_1", agent_id="", query="Query 1"),
        AgentTask(task_id="task_2", agent_id="", query="Query 2"),
        AgentTask(task_id="task_agg", agent_id="", query="Aggregate", dependencies=["task_1", "task_2"])
    ]

    await initialized_orchestrator.assign_tasks(tasks)

    # All tasks should have agents assigned
    for task in tasks:
        assert task.agent_id != ""
        assert task.agent_id in initialized_orchestrator.agents

    # Aggregation task should be assigned to AGGREGATOR
    agg_task = tasks[2]
    agent = initialized_orchestrator.agents[agg_task.agent_id]
    assert agent.role == AgentRole.AGGREGATOR


@pytest.mark.asyncio
async def test_orchestrator_execute_parallel_simple(initialized_orchestrator):
    """Test parallel execution of independent tasks."""
    # Create 3 independent tasks
    tasks = [
        AgentTask(task_id=f"task_{i}", agent_id="", query=f"Query {i}")
        for i in range(3)
    ]

    # Assign tasks
    await initialized_orchestrator.assign_tasks(tasks)

    # Execute in parallel
    results = await initialized_orchestrator.execute_parallel(tasks)

    # All tasks should complete
    assert len(results) == 3
    for task in tasks:
        assert task.status == "completed"
        assert task.task_id in results


@pytest.mark.asyncio
async def test_orchestrator_execute_parallel_with_dependencies(initialized_orchestrator):
    """Test parallel execution respecting dependencies."""
    # Create tasks with dependency chain: task_1, task_2 -> task_3
    task_1 = AgentTask(task_id="task_1", agent_id="", query="Query 1")
    task_2 = AgentTask(task_id="task_2", agent_id="", query="Query 2")
    task_3 = AgentTask(
        task_id="task_3",
        agent_id="",
        query="Aggregate",
        dependencies=["task_1", "task_2"]
    )

    tasks = [task_1, task_2, task_3]

    # Assign tasks
    await initialized_orchestrator.assign_tasks(tasks)

    # Execute
    results = await initialized_orchestrator.execute_parallel(tasks)

    # All tasks should complete
    assert len(results) == 3

    # task_3 should complete after task_1 and task_2
    assert task_1.completed_at is not None
    assert task_2.completed_at is not None
    assert task_3.completed_at is not None
    assert task_3.started_at >= max(task_1.completed_at, task_2.completed_at)


@pytest.mark.asyncio
async def test_orchestrator_execute_query_end_to_end(initialized_orchestrator):
    """Test full query execution workflow."""
    query = "Compare AAPL and MSFT"

    result = await initialized_orchestrator.execute_query(query)

    assert result["query"] == query
    assert result["session_id"] is not None
    assert result["tasks_completed"] >= 2  # At least 2 ticker tasks


@pytest.mark.asyncio
async def test_orchestrator_statistics(initialized_orchestrator):
    """Test orchestrator statistics collection."""
    # Create some agents
    initialized_orchestrator.create_agent(AgentRole.PLANNER)
    initialized_orchestrator.create_agent(AgentRole.EXECUTOR)

    stats = initialized_orchestrator.get_statistics()

    assert stats["total_agents"] == 2
    assert stats["agents_by_role"][AgentRole.PLANNER.value] == 1
    assert stats["agents_by_role"][AgentRole.EXECUTOR.value] == 1


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_parallel_execution_performance():
    """Test parallel execution is faster than sequential."""
    orchestrator = ParallelOrchestrator()
    await orchestrator.initialize_session("Performance test")

    # Create 5 independent tasks
    tasks = [
        AgentTask(task_id=f"task_{i}", agent_id="", query=f"Query {i}")
        for i in range(5)
    ]

    await orchestrator.assign_tasks(tasks)

    # Measure execution time
    import time
    start = time.time()
    await orchestrator.execute_parallel(tasks)
    elapsed = time.time() - start

    # Should complete in < 2 seconds (parallel) vs > 5 seconds (sequential)
    assert elapsed < 2.0, f"Parallel execution too slow: {elapsed}s"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_complex_multi_ticker_workflow():
    """Test complex multi-ticker query workflow."""
    orchestrator = ParallelOrchestrator()

    query = "Compare Sharpe ratios of AAPL, MSFT, GOOGL, TSLA for 2023"

    result = await orchestrator.execute_query(query)

    # Should create 4 ticker tasks + 1 aggregation = 5 tasks
    assert result["tasks_completed"] == 5

    # All tasks should complete successfully
    stats = orchestrator.get_statistics()
    assert stats["success_rate"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
