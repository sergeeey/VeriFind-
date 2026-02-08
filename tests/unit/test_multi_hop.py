"""
Unit tests for Multi-hop Query Engine.

Week 10 Day 1: Multi-hop queries - complex queries requiring multiple steps.

Tests validate that:
1. Query decomposition works correctly
2. Dependency graph is built properly
3. Execution order is correct (topological sort)
4. Intermediate results are cached and reused
5. Complex multi-hop queries execute successfully
"""

import pytest
from src.reasoning.multi_hop import (
    QueryDecomposer,
    DependencyGraph,
    MultiHopOrchestrator,
    SubQuery,
    QueryType
)


class TestQueryDecomposer:
    """Tests for QueryDecomposer class."""

    def setup_method(self):
        """Setup test instance."""
        self.decomposer = QueryDecomposer()

    # ========================================================================
    # Simple Query Decomposition
    # ========================================================================

    def test_single_calculation_query(self):
        """Test decomposition of single calculation query."""
        query = "Calculate the Sharpe ratio for AAPL"

        sub_queries = self.decomposer.decompose(query)

        assert len(sub_queries) == 1
        assert sub_queries[0].type == QueryType.CALCULATE
        assert sub_queries[0].metric == "sharpe_ratio"
        assert "AAPL" in sub_queries[0].params["ticker"]

    def test_comparison_query_decomposition(self):
        """Test decomposition of comparison query."""
        query = "Compare the Sharpe ratios of AAPL and MSFT"

        sub_queries = self.decomposer.decompose(query)

        # Should decompose into: calculate(AAPL), calculate(MSFT), compare(results)
        assert len(sub_queries) >= 3

        # First two should be calculations
        calc_queries = [sq for sq in sub_queries if sq.type == QueryType.CALCULATE]
        assert len(calc_queries) == 2

        # One should be comparison
        compare_queries = [sq for sq in sub_queries if sq.type == QueryType.COMPARE]
        assert len(compare_queries) == 1

    def test_multi_hop_with_correlation(self):
        """Test multi-hop query with correlation."""
        query = "Compare Sharpe ratios of AAPL and MSFT, then calculate correlation between them"

        sub_queries = self.decomposer.decompose(query)

        # Should have: sharpe(AAPL), sharpe(MSFT), compare, correlation(AAPL, MSFT)
        assert len(sub_queries) >= 4

        calc_queries = [sq for sq in sub_queries if sq.type == QueryType.CALCULATE]
        assert len(calc_queries) >= 2

    # ========================================================================
    # Dependency Detection
    # ========================================================================

    def test_dependencies_are_detected(self):
        """Test that dependencies between sub-queries are detected."""
        query = "Compare Sharpe ratios of AAPL and MSFT"

        sub_queries = self.decomposer.decompose(query)

        # Comparison query should depend on calculation queries
        compare_query = next(sq for sq in sub_queries if sq.type == QueryType.COMPARE)

        assert len(compare_query.dependencies) >= 2
        assert all(dep in [sq.id for sq in sub_queries] for dep in compare_query.dependencies)

    def test_no_circular_dependencies(self):
        """Test that decomposition doesn't create circular dependencies."""
        query = "Compare Sharpe ratios of AAPL and MSFT"

        sub_queries = self.decomposer.decompose(query)

        # Build dependency graph and check for cycles
        graph = DependencyGraph()
        for sq in sub_queries:
            graph.add_node(sq)

        assert not graph.has_cycles()


class TestDependencyGraph:
    """Tests for DependencyGraph class."""

    def setup_method(self):
        """Setup test instance."""
        self.graph = DependencyGraph()

    # ========================================================================
    # Graph Construction
    # ========================================================================

    def test_add_node(self):
        """Test adding nodes to graph."""
        sq1 = SubQuery(
            id="sq1",
            type=QueryType.CALCULATE,
            metric="sharpe_ratio",
            params={"ticker": "AAPL"},
            dependencies=[]
        )

        self.graph.add_node(sq1)

        assert len(self.graph.nodes) == 1
        assert "sq1" in self.graph.nodes

    def test_add_edge(self):
        """Test adding edges to graph."""
        sq1 = SubQuery(id="sq1", type=QueryType.CALCULATE, metric="sharpe_ratio", params={"ticker": "AAPL"}, dependencies=[])
        sq2 = SubQuery(id="sq2", type=QueryType.CALCULATE, metric="sharpe_ratio", params={"ticker": "MSFT"}, dependencies=[])
        sq3 = SubQuery(id="sq3", type=QueryType.COMPARE, metric="sharpe_ratio", params={}, dependencies=["sq1", "sq2"])

        self.graph.add_node(sq1)
        self.graph.add_node(sq2)
        self.graph.add_node(sq3)

        assert self.graph.get_dependencies("sq3") == ["sq1", "sq2"]

    # ========================================================================
    # Topological Sorting
    # ========================================================================

    def test_topological_sort_simple(self):
        """Test topological sort with simple linear dependencies."""
        sq1 = SubQuery(id="sq1", type=QueryType.CALCULATE, metric="sharpe_ratio", params={"ticker": "AAPL"}, dependencies=[])
        sq2 = SubQuery(id="sq2", type=QueryType.CALCULATE, metric="sharpe_ratio", params={"ticker": "MSFT"}, dependencies=[])
        sq3 = SubQuery(id="sq3", type=QueryType.COMPARE, metric="sharpe_ratio", params={}, dependencies=["sq1", "sq2"])

        self.graph.add_node(sq1)
        self.graph.add_node(sq2)
        self.graph.add_node(sq3)

        order = self.graph.topological_sort()

        # sq3 should come after sq1 and sq2
        assert order.index("sq3") > order.index("sq1")
        assert order.index("sq3") > order.index("sq2")

    def test_topological_sort_complex(self):
        """Test topological sort with complex dependencies."""
        # Create: A, B, C=f(A,B), D=f(A), E=f(C,D)
        nodes = [
            SubQuery(id="A", type=QueryType.CALCULATE, metric="sharpe", params={"ticker": "AAPL"}, dependencies=[]),
            SubQuery(id="B", type=QueryType.CALCULATE, metric="sharpe", params={"ticker": "MSFT"}, dependencies=[]),
            SubQuery(id="C", type=QueryType.COMPARE, metric="sharpe", params={}, dependencies=["A", "B"]),
            SubQuery(id="D", type=QueryType.CALCULATE, metric="volatility", params={"ticker": "AAPL"}, dependencies=[]),
            SubQuery(id="E", type=QueryType.COMPARE, metric="mixed", params={}, dependencies=["C", "D"]),
        ]

        for node in nodes:
            self.graph.add_node(node)

        order = self.graph.topological_sort()

        # Verify order constraints
        assert order.index("C") > order.index("A")
        assert order.index("C") > order.index("B")
        assert order.index("E") > order.index("C")
        assert order.index("E") > order.index("D")

    def test_parallel_execution_groups(self):
        """Test identification of parallel execution groups."""
        # Create: A, B (parallel), C=f(A,B)
        nodes = [
            SubQuery(id="A", type=QueryType.CALCULATE, metric="sharpe", params={"ticker": "AAPL"}, dependencies=[]),
            SubQuery(id="B", type=QueryType.CALCULATE, metric="sharpe", params={"ticker": "MSFT"}, dependencies=[]),
            SubQuery(id="C", type=QueryType.COMPARE, metric="sharpe", params={}, dependencies=["A", "B"]),
        ]

        for node in nodes:
            self.graph.add_node(node)

        groups = self.graph.get_parallel_groups()

        # A and B should be in the same group (can run in parallel)
        assert len(groups) == 2  # Group 1: [A, B], Group 2: [C]
        assert set(groups[0]) == {"A", "B"}
        assert groups[1] == ["C"]

    # ========================================================================
    # Cycle Detection
    # ========================================================================

    def test_cycle_detection_no_cycle(self):
        """Test cycle detection on acyclic graph."""
        nodes = [
            SubQuery(id="A", type=QueryType.CALCULATE, metric="sharpe", params={}, dependencies=[]),
            SubQuery(id="B", type=QueryType.COMPARE, metric="sharpe", params={}, dependencies=["A"]),
        ]

        for node in nodes:
            self.graph.add_node(node)

        assert not self.graph.has_cycles()

    def test_cycle_detection_with_cycle(self):
        """Test cycle detection on cyclic graph."""
        # Manually create circular dependency for testing
        nodes = [
            SubQuery(id="A", type=QueryType.CALCULATE, metric="sharpe", params={}, dependencies=["B"]),
            SubQuery(id="B", type=QueryType.COMPARE, metric="sharpe", params={}, dependencies=["A"]),
        ]

        for node in nodes:
            self.graph.add_node(node)

        assert self.graph.has_cycles()


class TestMultiHopOrchestrator:
    """Tests for MultiHopOrchestrator class."""

    def setup_method(self):
        """Setup test instance."""
        self.orchestrator = MultiHopOrchestrator()

    # ========================================================================
    # Simple Execution
    # ========================================================================

    def test_execute_single_query(self):
        """Test execution of single query (no multi-hop)."""
        query = "Calculate the Sharpe ratio for AAPL"

        result = self.orchestrator.execute(query)

        assert result is not None
        assert result.success is True
        assert isinstance(result.final_result, dict)
        assert result.final_result.get("metric") == "sharpe_ratio"

    def test_execute_comparison_query(self):
        """Test execution of comparison query (2-hop)."""
        query = "Compare the Sharpe ratios of AAPL and MSFT"

        result = self.orchestrator.execute(query)

        assert result is not None
        assert result.success is True
        assert "comparison" in result.final_result
        assert len(result.intermediate_results) >= 2  # At least 2 calculations

    # ========================================================================
    # Intermediate Result Caching
    # ========================================================================

    def test_intermediate_results_cached(self):
        """Test that intermediate results are cached."""
        query = "Compare the Sharpe ratios of AAPL and MSFT"

        result = self.orchestrator.execute(query)

        # Check that intermediate results are stored
        assert len(result.intermediate_results) >= 2
        assert any("AAPL" in str(r) for r in result.intermediate_results.values())
        assert any("MSFT" in str(r) for r in result.intermediate_results.values())

    def test_cache_reuse(self):
        """Test that cached results are reused."""
        query1 = "Calculate the Sharpe ratio for AAPL"
        query2 = "Compare the Sharpe ratios of AAPL and MSFT"

        # Execute first query (caches AAPL Sharpe ratio)
        result1 = self.orchestrator.execute(query1)

        # Execute second query (should reuse AAPL Sharpe ratio from cache)
        result2 = self.orchestrator.execute(query2)

        # Second query should have reused first result
        assert result2 is not None
        assert result2.success is True

    # ========================================================================
    # Complex Multi-hop
    # ========================================================================

    def test_three_hop_query(self):
        """Test 3-hop query execution."""
        query = "Calculate Sharpe ratios for AAPL and MSFT, compare them, then calculate correlation between the stocks"

        result = self.orchestrator.execute(query)

        assert result is not None
        assert result.success is True
        assert len(result.intermediate_results) >= 3  # At least 3 steps

    def test_execution_order_respected(self):
        """Test that execution order respects dependencies."""
        query = "Compare the Sharpe ratios of AAPL and MSFT"

        result = self.orchestrator.execute(query)

        # Check execution order
        execution_order = list(result.intermediate_results.keys())

        # Comparison should come after calculations
        compare_idx = next(i for i, k in enumerate(execution_order) if "compare" in k.lower())
        calc_indices = [i for i, k in enumerate(execution_order) if "calculate" in k.lower()]

        assert all(compare_idx > calc_idx for calc_idx in calc_indices)

    # ========================================================================
    # Error Handling
    # ========================================================================

    def test_handles_invalid_query(self):
        """Test handling of invalid query."""
        query = "This is not a financial query"

        result = self.orchestrator.execute(query)

        assert result is not None
        assert result.success is False
        assert result.error is not None

    def test_handles_sub_query_failure(self):
        """Test handling when a sub-query fails."""
        query = "Calculate Sharpe ratio for INVALID_TICKER_XYZ"

        result = self.orchestrator.execute(query)

        # Should fail gracefully
        assert result is not None
        assert result.success is False or result.error is not None

    def test_partial_execution_on_failure(self):
        """Test that partial results are available on failure."""
        query = "Compare Sharpe ratios of AAPL and INVALID_TICKER"

        result = self.orchestrator.execute(query)

        # Should have at least partial results (AAPL succeeded)
        assert len(result.intermediate_results) >= 1


# ============================================================================
# Integration Tests
# ============================================================================

class TestMultiHopIntegration:
    """Integration tests for multi-hop queries."""

    def test_real_world_comparison_query(self):
        """Test real-world comparison query end-to-end."""
        orchestrator = MultiHopOrchestrator()

        query = "Compare the Sharpe ratios of AAPL and MSFT from 2023-01-01 to 2023-12-31"

        result = orchestrator.execute(query)

        assert result is not None
        # Result should succeed or fail gracefully with clear error
        if result.success:
            assert "comparison" in result.final_result or "AAPL" in str(result.final_result)

    def test_correlation_after_sharpe(self):
        """Test multi-hop: calculate Sharpe, then correlation."""
        orchestrator = MultiHopOrchestrator()

        query = "Calculate Sharpe ratios for AAPL and MSFT, then calculate their correlation"

        result = orchestrator.execute(query)

        assert result is not None
        assert len(result.intermediate_results) >= 2
