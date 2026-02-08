"""
APE Orchestrator - Coordinates PLAN→VEE→GATE pipeline.

Week 2 Day 5: Simplified orchestrator (before LangGraph in Week 3).

Flow:
1. Receive user query
2. Generate execution plan (PLAN node)
3. Execute code in VEE sandbox
4. Validate through Truth Boundary
5. Return VerifiedFact

This is a simple synchronous orchestrator. Week 3 will add:
- LangGraph state machine
- Async execution
- FETCH node integration
- Multi-step plans
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging

from src.orchestration.nodes.plan_node import PlanNode
from src.vee.sandbox_runner import SandboxRunner, ExecutionResult
from src.truth_boundary.gate import TruthBoundaryGate, VerifiedFact, ValidationResult


@dataclass
class QueryResult:
    """Result of processing a user query through the pipeline."""

    query_id: str
    query_text: str
    status: str  # 'success', 'plan_error', 'execution_error', 'validation_error'
    verified_fact: Optional[VerifiedFact] = None
    error_message: Optional[str] = None
    plan_generated: bool = False
    code_executed: bool = False
    output_validated: bool = False


class APEOrchestrator:
    """
    APE Pipeline Orchestrator.

    Coordinates PLAN→VEE→GATE flow for simple queries.

    Design:
    - Synchronous execution (async in Week 3)
    - Single-step plans only (multi-step in Week 3)
    - No caching yet (Week 3+)
    - No LangGraph state machine (Week 3)
    """

    def __init__(
        self,
        claude_api_key: str,
        vee_config: Optional[Dict[str, Any]] = None,
        enable_logging: bool = True
    ):
        """
        Initialize orchestrator.

        Args:
            claude_api_key: Claude API key for PLAN node
            vee_config: VEE sandbox configuration (memory, CPU, timeout)
            enable_logging: Enable debug logging
        """
        # Initialize components
        self.plan_node = PlanNode(api_key=claude_api_key)

        vee_config = vee_config or {}
        self.vee_sandbox = SandboxRunner(
            memory_limit=vee_config.get('memory_limit', '256m'),
            cpu_limit=vee_config.get('cpu_limit', 0.5),
            timeout=vee_config.get('timeout', 30)
        )

        self.truth_gate = TruthBoundaryGate()

        # Logging
        self.logger = logging.getLogger(__name__)
        if enable_logging:
            logging.basicConfig(level=logging.INFO)

    def process_query(
        self,
        query_id: str,
        query_text: str,
        context: Optional[Dict[str, Any]] = None,
        skip_plan: bool = False,
        direct_code: Optional[str] = None
    ) -> QueryResult:
        """
        Process user query through PLAN→VEE→GATE pipeline.

        Args:
            query_id: Unique query identifier
            query_text: User query text
            context: Optional context (market data, etc.)
            skip_plan: Skip PLAN generation (use direct_code instead)
            direct_code: Direct Python code (for testing, bypasses PLAN)

        Returns:
            QueryResult with VerifiedFact or error
        """
        self.logger.info(f"Processing query {query_id}: {query_text[:50]}...")

        result = QueryResult(
            query_id=query_id,
            query_text=query_text,
            status='processing'
        )

        # Step 1: PLAN - Generate executable code
        if skip_plan and direct_code:
            self.logger.info("Skipping PLAN (using direct code)")
            generated_code = direct_code
            plan_id = f"{query_id}_direct"
            code_hash = None
            result.plan_generated = True
        else:
            try:
                self.logger.info("PLAN: Generating execution plan...")
                # In production, this would call Claude API
                # For now, we'll mark it as not implemented
                result.status = 'plan_error'
                result.error_message = 'PLAN node requires Claude API (not in test mode)'
                return result
            except Exception as e:
                self.logger.error(f"PLAN failed: {e}")
                result.status = 'plan_error'
                result.error_message = str(e)
                return result

        # Step 2: VEE - Execute code in sandbox
        try:
            self.logger.info("VEE: Executing code in sandbox...")
            exec_result = self.vee_sandbox.execute(generated_code)
            result.code_executed = True

            if exec_result.status != 'success':
                self.logger.warning(f"VEE execution failed: {exec_result.status}")
                result.status = 'execution_error'
                result.error_message = exec_result.stderr or 'Execution failed'
                return result

        except Exception as e:
            self.logger.error(f"VEE execution error: {e}")
            result.status = 'execution_error'
            result.error_message = str(e)
            return result

        # Step 3: GATE - Validate output
        try:
            self.logger.info("GATE: Validating execution output...")
            validation = self.truth_gate.validate(exec_result)
            result.output_validated = True

            if not validation.is_valid:
                self.logger.warning("GATE validation failed")
                result.status = 'validation_error'
                result.error_message = validation.error_message
                return result

            # Create VerifiedFact
            verified_fact = self.truth_gate.create_verified_fact(
                validation=validation,
                query_id=query_id,
                plan_id=plan_id,
                code_hash=exec_result.code_hash,
                execution_time_ms=exec_result.duration_ms,
                memory_used_mb=exec_result.memory_used_mb
            )

            result.verified_fact = verified_fact
            result.status = 'success'

            self.logger.info(f"SUCCESS: Query {query_id} completed")
            return result

        except Exception as e:
            self.logger.error(f"GATE validation error: {e}")
            result.status = 'validation_error'
            result.error_message = str(e)
            return result

    def process_batch(
        self,
        queries: list[tuple[str, str]],
        direct_codes: Optional[list[str]] = None
    ) -> list[QueryResult]:
        """
        Process multiple queries in batch.

        Args:
            queries: List of (query_id, query_text) tuples
            direct_codes: Optional list of direct Python codes (for testing)

        Returns:
            List of QueryResult objects
        """
        results = []

        for i, (query_id, query_text) in enumerate(queries):
            direct_code = direct_codes[i] if direct_codes and i < len(direct_codes) else None

            result = self.process_query(
                query_id=query_id,
                query_text=query_text,
                skip_plan=direct_code is not None,
                direct_code=direct_code
            )

            results.append(result)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """
        Get orchestrator statistics.

        Returns:
            Dictionary with execution stats
        """
        return {
            'plan_node_initialized': self.plan_node is not None,
            'vee_sandbox_initialized': self.vee_sandbox is not None,
            'truth_gate_initialized': self.truth_gate is not None,
            'vee_image': self.vee_sandbox.image,
            'vee_memory_limit': self.vee_sandbox.memory_limit,
            'vee_timeout': self.vee_sandbox.timeout
        }
