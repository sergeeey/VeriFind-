"""
Multi-hop Query Engine for APE 2026.

Week 10 Day 1: Complex queries requiring multiple steps and data sources.

Example:
    "Compare Sharpe ratios of AAPL and MSFT, then calculate correlation"

    Decomposes into:
    1. Calculate Sharpe ratio for AAPL
    2. Calculate Sharpe ratio for MSFT
    3. Compare results
    4. Calculate correlation between AAPL and MSFT
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Tuple
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Query Types
# ============================================================================

class QueryType(str, Enum):
    """Types of sub-queries."""
    CALCULATE = "calculate"  # Calculate a metric
    COMPARE = "compare"      # Compare multiple values
    CORRELATE = "correlate"  # Calculate correlation
    AGGREGATE = "aggregate"  # Aggregate multiple results
    FILTER = "filter"        # Filter results
    TRANSFORM = "transform"  # Transform data


# ============================================================================
# Sub-Query Data Structure
# ============================================================================

@dataclass
class SubQuery:
    """
    Represents a single step in a multi-hop query.

    Attributes:
        id: Unique identifier
        type: Type of query (calculate, compare, etc.)
        metric: Metric to calculate (sharpe_ratio, correlation, etc.)
        params: Parameters for the query (ticker, date range, etc.)
        dependencies: IDs of sub-queries this depends on
        result: Result after execution (None if not executed)
    """
    id: str
    type: QueryType
    metric: str
    params: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Any] = None

    def __hash__(self):
        return hash(self.id)


# ============================================================================
# Execution Result
# ============================================================================

@dataclass
class ExecutionResult:
    """
    Result of multi-hop query execution.

    Attributes:
        success: Whether execution succeeded
        final_result: Final result of the query
        intermediate_results: Results of sub-queries (keyed by sub-query ID)
        execution_order: Order in which sub-queries were executed
        error: Error message if execution failed
    """
    success: bool
    final_result: Any
    intermediate_results: Dict[str, Any] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    error: Optional[str] = None


# ============================================================================
# Query Decomposer
# ============================================================================

class QueryDecomposer:
    """
    Decomposes complex queries into sub-queries.

    Strategy:
    1. Pattern matching for common query structures
    2. Keyword extraction (tickers, metrics, actions)
    3. Dependency inference
    """

    # Patterns for different query types
    COMPARISON_PATTERNS = [
        r"compare.*between\s+(\w+)\s+and\s+(\w+)",
        r"compare.*of\s+(\w+)\s+and\s+(\w+)",
        r"(\w+)\s+vs\.?\s+(\w+)",
    ]

    CORRELATION_PATTERNS = [
        r"correlation.*between\s+(\w+)\s+and\s+(\w+)",
        r"correlate\s+(\w+)\s+and\s+(\w+)",
    ]

    TICKER_PATTERN = r'\b[A-Z]{2,5}\b'

    METRICS = {
        "sharpe": "sharpe_ratio",
        "correlation": "correlation",
        "volatility": "volatility",
        "beta": "beta",
        "return": "return",
    }

    def decompose(self, query: str) -> List[SubQuery]:
        """
        Decompose complex query into sub-queries.

        Args:
            query: Complex query string

        Returns:
            List of SubQuery objects
        """
        query_lower = query.lower()
        sub_queries = []

        # Extract tickers
        tickers = self._extract_tickers(query)

        # Extract metric
        metric = self._extract_metric(query_lower)

        # Detect query structure
        if self._is_comparison(query_lower):
            sub_queries = self._decompose_comparison(query, tickers, metric)
        elif self._is_correlation(query_lower):
            sub_queries = self._decompose_correlation(query, tickers, metric)
        else:
            # Simple calculation
            sub_queries = self._decompose_simple(query, tickers, metric)

        return sub_queries

    def _extract_tickers(self, query: str) -> List[str]:
        """Extract ticker symbols from query."""
        matches = re.findall(self.TICKER_PATTERN, query)
        # Filter out common English words
        common_words = {'THE', 'AND', 'FOR', 'ARE', 'FROM', 'TO', 'IS', 'AS', 'OR'}
        return [t for t in matches if t not in common_words]

    def _extract_metric(self, query_lower: str) -> str:
        """Extract financial metric from query."""
        for keyword, metric in self.METRICS.items():
            if keyword in query_lower:
                return metric
        return "unknown"

    def _is_comparison(self, query_lower: str) -> bool:
        """Check if query is a comparison."""
        return any(pattern in query_lower for pattern in ["compare", "vs", "versus"])

    def _is_correlation(self, query_lower: str) -> bool:
        """Check if query involves correlation."""
        return "correlation" in query_lower or "correlate" in query_lower

    def _decompose_simple(self, query: str, tickers: List[str], metric: str) -> List[SubQuery]:
        """Decompose simple calculation query."""
        if not tickers:
            return []

        sq = SubQuery(
            id=f"sq_{uuid4().hex[:8]}",
            type=QueryType.CALCULATE,
            metric=metric,
            params={"ticker": tickers[0], "query": query},
            dependencies=[]
        )

        return [sq]

    def _decompose_comparison(self, query: str, tickers: List[str], metric: str) -> List[SubQuery]:
        """Decompose comparison query."""
        sub_queries = []

        # Create calculation sub-queries for each ticker
        calc_ids = []
        for ticker in tickers:
            sq = SubQuery(
                id=f"calc_{ticker}_{uuid4().hex[:8]}",
                type=QueryType.CALCULATE,
                metric=metric,
                params={"ticker": ticker, "query": query},
                dependencies=[]
            )
            sub_queries.append(sq)
            calc_ids.append(sq.id)

        # Create comparison sub-query
        compare_sq = SubQuery(
            id=f"compare_{uuid4().hex[:8]}",
            type=QueryType.COMPARE,
            metric=metric,
            params={"tickers": tickers},
            dependencies=calc_ids
        )
        sub_queries.append(compare_sq)

        # Check if correlation is also requested
        if "correlation" in query.lower():
            corr_sq = SubQuery(
                id=f"corr_{uuid4().hex[:8]}",
                type=QueryType.CORRELATE,
                metric="correlation",
                params={"tickers": tickers},
                dependencies=calc_ids  # Depends on calculations, not comparison
            )
            sub_queries.append(corr_sq)

        return sub_queries

    def _decompose_correlation(self, query: str, tickers: List[str], metric: str) -> List[SubQuery]:
        """Decompose correlation query."""
        if len(tickers) < 2:
            return []

        # If Sharpe ratio is mentioned, calculate it first
        if "sharpe" in query.lower():
            sub_queries = []
            calc_ids = []

            for ticker in tickers:
                sq = SubQuery(
                    id=f"calc_{ticker}_{uuid4().hex[:8]}",
                    type=QueryType.CALCULATE,
                    metric="sharpe_ratio",
                    params={"ticker": ticker, "query": query},
                    dependencies=[]
                )
                sub_queries.append(sq)
                calc_ids.append(sq.id)

            # Then correlation
            corr_sq = SubQuery(
                id=f"corr_{uuid4().hex[:8]}",
                type=QueryType.CORRELATE,
                metric="correlation",
                params={"tickers": tickers},
                dependencies=calc_ids
            )
            sub_queries.append(corr_sq)

            return sub_queries
        else:
            # Direct correlation
            sq = SubQuery(
                id=f"corr_{uuid4().hex[:8]}",
                type=QueryType.CORRELATE,
                metric="correlation",
                params={"tickers": tickers, "query": query},
                dependencies=[]
            )
            return [sq]


# ============================================================================
# Dependency Graph
# ============================================================================

class DependencyGraph:
    """
    Tracks dependencies between sub-queries.

    Features:
    - Topological sorting for execution order
    - Parallel execution group identification
    - Cycle detection
    """

    def __init__(self):
        self.nodes: Dict[str, SubQuery] = {}
        self.edges: Dict[str, List[str]] = {}  # node_id -> [dependent_node_ids]

    def add_node(self, sub_query: SubQuery):
        """Add a node to the graph."""
        self.nodes[sub_query.id] = sub_query

        # Initialize edges
        if sub_query.id not in self.edges:
            self.edges[sub_query.id] = []

        # Add edges for dependencies
        for dep_id in sub_query.dependencies:
            if dep_id not in self.edges:
                self.edges[dep_id] = []
            self.edges[dep_id].append(sub_query.id)

    def get_dependencies(self, node_id: str) -> List[str]:
        """Get dependencies for a node."""
        if node_id not in self.nodes:
            return []
        return self.nodes[node_id].dependencies

    def topological_sort(self) -> List[str]:
        """
        Return topological ordering of nodes.

        Uses Kahn's algorithm.

        Returns:
            List of node IDs in execution order
        """
        # Calculate in-degrees
        in_degree = {node_id: len(self.nodes[node_id].dependencies) for node_id in self.nodes}

        # Find nodes with no dependencies
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)

            # Reduce in-degree of dependent nodes
            for dependent in self.edges.get(node_id, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        return result

    def get_parallel_groups(self) -> List[List[str]]:
        """
        Identify groups of nodes that can be executed in parallel.

        Returns:
            List of groups, where each group can run in parallel
        """
        order = self.topological_sort()
        groups = []

        # Calculate earliest execution level for each node
        levels = {}
        for node_id in order:
            deps = self.get_dependencies(node_id)
            if not deps:
                levels[node_id] = 0
            else:
                levels[node_id] = max(levels[dep] for dep in deps) + 1

        # Group nodes by level
        max_level = max(levels.values()) if levels else 0
        for level in range(max_level + 1):
            group = [node_id for node_id, l in levels.items() if l == level]
            if group:
                groups.append(group)

        return groups

    def has_cycles(self) -> bool:
        """Check if graph has cycles."""
        order = self.topological_sort()
        return len(order) != len(self.nodes)


# ============================================================================
# Multi-hop Orchestrator
# ============================================================================

class MultiHopOrchestrator:
    """
    Executes multi-hop queries.

    Flow:
    1. Decompose query into sub-queries
    2. Build dependency graph
    3. Execute in topological order
    4. Cache intermediate results
    5. Return final result
    """

    def __init__(self):
        self.decomposer = QueryDecomposer()
        self.cache: Dict[str, Any] = {}

    def execute(self, query: str) -> ExecutionResult:
        """
        Execute multi-hop query.

        Args:
            query: Complex query string

        Returns:
            ExecutionResult with final result and intermediate results
        """
        try:
            # Step 1: Decompose query
            sub_queries = self.decomposer.decompose(query)

            if not sub_queries:
                return ExecutionResult(
                    success=False,
                    final_result=None,
                    error="Could not decompose query"
                )

            # Step 2: Build dependency graph
            graph = DependencyGraph()
            for sq in sub_queries:
                graph.add_node(sq)

            # Step 3: Check for cycles
            if graph.has_cycles():
                return ExecutionResult(
                    success=False,
                    final_result=None,
                    error="Circular dependencies detected in query"
                )

            # Step 4: Execute in topological order
            execution_order = graph.topological_sort()
            intermediate_results = {}

            for sq_id in execution_order:
                sq = graph.nodes[sq_id]

                # Execute sub-query
                result = self._execute_sub_query(sq, intermediate_results)
                intermediate_results[sq_id] = result
                sq.result = result

            # Step 5: Final result is the result of the last sub-query
            final_sq_id = execution_order[-1]
            final_result = intermediate_results[final_sq_id]

            return ExecutionResult(
                success=True,
                final_result=final_result,
                intermediate_results=intermediate_results,
                execution_order=execution_order
            )

        except Exception as e:
            logger.error(f"Multi-hop execution error: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                final_result=None,
                error=str(e)
            )

    def _execute_sub_query(self, sq: SubQuery, context: Dict[str, Any]) -> Any:
        """
        Execute a single sub-query.

        Args:
            sq: SubQuery to execute
            context: Intermediate results from previous sub-queries

        Returns:
            Result of sub-query execution
        """
        # Check cache first
        cache_key = self._get_cache_key(sq)
        if cache_key in self.cache:
            logger.info(f"Cache hit for sub-query {sq.id}")
            return self.cache[cache_key]

        # Execute based on type
        if sq.type == QueryType.CALCULATE:
            result = self._execute_calculate(sq)
        elif sq.type == QueryType.COMPARE:
            result = self._execute_compare(sq, context)
        elif sq.type == QueryType.CORRELATE:
            result = self._execute_correlate(sq, context)
        else:
            result = {"error": f"Unknown query type: {sq.type}"}

        # Cache result
        self.cache[cache_key] = result

        return result

    def _get_cache_key(self, sq: SubQuery) -> str:
        """Generate cache key for sub-query."""
        params_str = "_".join(f"{k}={v}" for k, v in sorted(sq.params.items()))
        return f"{sq.type}_{sq.metric}_{params_str}"

    def _execute_calculate(self, sq: SubQuery) -> Dict[str, Any]:
        """Execute calculation sub-query."""
        # Mock implementation - in production, this would call VEE
        ticker = sq.params.get("ticker", "UNKNOWN")
        metric = sq.metric

        logger.info(f"Calculating {metric} for {ticker}")

        # Return mock result
        return {
            "metric": metric,
            "ticker": ticker,
            "value": 1.5,  # Mock value
            "status": "success"
        }

    def _execute_compare(self, sq: SubQuery, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute comparison sub-query."""
        # Get results from dependencies
        dep_results = [context.get(dep_id) for dep_id in sq.dependencies]

        logger.info(f"Comparing {len(dep_results)} results")

        # Extract values
        values = {}
        for result in dep_results:
            if result and isinstance(result, dict):
                ticker = result.get("ticker")
                value = result.get("value")
                if ticker and value is not None:
                    values[ticker] = value

        return {
            "comparison": values,
            "metric": sq.metric,
            "status": "success"
        }

    def _execute_correlate(self, sq: SubQuery, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute correlation sub-query."""
        tickers = sq.params.get("tickers", [])

        logger.info(f"Calculating correlation for {tickers}")

        # Mock correlation value
        return {
            "metric": "correlation",
            "tickers": tickers,
            "value": 0.75,  # Mock correlation
            "status": "success"
        }
