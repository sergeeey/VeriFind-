"""
LangGraph State Machine Orchestrator for APE.

Week 3 Day 1: State-based orchestration with conditional routing.
Week 5 Day 3: Integrated Debate System for multi-perspective analysis.

State Machine:
- PLAN: Generate executable code
- FETCH: Get market data (conditional)
- VEE: Execute code in sandbox
- GATE: Validate output
- DEBATE: Multi-perspective analysis (Bull/Bear/Neutral)
- ERROR: Handle failures with retry

State Flow:
INITIALIZED → PLAN → (FETCH?) → VEE → GATE → DEBATE → COMPLETED
                ↓ error ↓
              ERROR → retry or FAILED
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from datetime import datetime, UTC
import time
import asyncio
import logging

from src.vee.sandbox_runner import SandboxRunner, ExecutionResult
from src.truth_boundary.gate import TruthBoundaryGate, VerifiedFact
from src.adapters.yfinance_adapter import YFinanceAdapter, MarketData
from src.debate.debater_agent import DebaterAgent
from src.debate.synthesizer_agent import SynthesizerAgent
from src.debate.real_llm_adapter import RealLLMDebateAdapter  # Week 11 Day 2: Real LLM integration
from src.debate.schemas import Perspective, DebateContext, DebateReport, Synthesis

# Logger for orchestrator
logger = logging.getLogger(__name__)


class StateStatus(str, Enum):
    """State machine status values."""
    INITIALIZED = 'initialized'
    PLANNING = 'planning'
    FETCHING = 'fetching'
    EXECUTING = 'executing'
    VALIDATING = 'validating'
    DEBATING = 'debating'
    COMPLETED = 'completed'
    FAILED = 'failed'


@dataclass
class APEState:
    """
    State object for APE state machine.

    Passed between nodes and updated at each step.
    """

    query_id: str
    query_text: str
    status: StateStatus = StateStatus.INITIALIZED
    current_node: Optional[str] = None

    # Data
    plan: Optional[Dict[str, Any]] = None
    fetched_data: Optional[Dict[str, Any]] = None
    execution_result: Optional[ExecutionResult] = None
    verified_fact: Optional[VerifiedFact] = None

    # Debate (Week 5 Day 2)
    debate_reports: Optional[List[Any]] = None  # List[DebateReport]
    synthesis: Optional[Any] = None  # Synthesis

    # Error handling
    error_count: int = 0
    error_message: Optional[str] = None

    # Metrics
    start_time: float = field(default_factory=time.time)
    nodes_visited: List[str] = field(default_factory=list)

    @classmethod
    def from_query(cls, query_id: str, query_text: str) -> 'APEState':
        """Create initial state from query."""
        return cls(
            query_id=query_id,
            query_text=query_text,
            status=StateStatus.INITIALIZED
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to dict."""
        return {
            'query_id': self.query_id,
            'query_text': self.query_text,
            'status': self.status.value,
            'current_node': self.current_node,
            'plan': self.plan,
            'error_count': self.error_count,
            'error_message': self.error_message,
            'nodes_visited': self.nodes_visited,
            # Note: execution_result and verified_fact omitted for simplicity
            # In production, would serialize these too
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APEState':
        """Deserialize state from dict."""
        return cls(
            query_id=data['query_id'],
            query_text=data['query_text'],
            status=StateStatus(data['status']),
            current_node=data.get('current_node'),
            plan=data.get('plan'),
            error_count=data.get('error_count', 0),
            error_message=data.get('error_message'),
            nodes_visited=data.get('nodes_visited', [])
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics."""
        return {
            'total_duration_ms': int((time.time() - self.start_time) * 1000),
            'nodes_visited': self.nodes_visited,
            'error_count': self.error_count,
            'status': self.status.value
        }


class LangGraphOrchestrator:
    """
    LangGraph-based state machine orchestrator.

    Coordinates PLAN→FETCH→VEE→GATE→DEBATE flow with error handling.

    Week 9 Day 1: Integrated with WebSocket for real-time updates.
    """

    def __init__(
        self,
        claude_api_key: str = None,
        enable_retry: bool = True,
        max_retries: int = 3,
        vee_config: Optional[Dict[str, Any]] = None,
        broadcast_callback: Optional[Callable] = None,
        use_real_llm: bool = True,  # Week 11 Day 2: Enable real LLM by default
        llm_provider: str = "deepseek"  # Week 11 Day 2: Default to cheapest provider
    ):
        """
        Initialize LangGraph orchestrator.

        Args:
            claude_api_key: Claude API key for PLAN node (optional for testing)
            enable_retry: Enable automatic retry on errors
            max_retries: Maximum retry attempts
            vee_config: VEE sandbox configuration
            broadcast_callback: Optional async callback for broadcasting status updates
                               Should have signature: (query_id, status, node, progress, facts_count, error, metadata)
            use_real_llm: Use real LLM API for debate (True) or mock agents (False)
            llm_provider: LLM provider for debate ("openai", "gemini", "deepseek")
        """
        self.enable_retry = enable_retry
        self.max_retries = max_retries
        self.broadcast_callback = broadcast_callback
        self.use_real_llm = use_real_llm
        self.llm_provider = llm_provider

        # Initialize components
        vee_config = vee_config or {}
        self.vee_sandbox = SandboxRunner(
            memory_limit=vee_config.get('memory_limit', '256m'),
            cpu_limit=vee_config.get('cpu_limit', 0.5),
            timeout=vee_config.get('timeout', 30)
        )

        self.truth_gate = TruthBoundaryGate()
        self.yfinance_adapter = YFinanceAdapter()

        # Initialize debate system (Week 11 Day 2)
        if self.use_real_llm:
            self.debate_adapter = RealLLMDebateAdapter(
                provider=llm_provider,
                enable_debate=True
            )
            logger.info(f"Initialized real LLM debate with provider: {llm_provider}")
        else:
            self.debate_adapter = None
            logger.info("Using mock debate agents")

    def _broadcast_update(
        self,
        query_id: str,
        status: str,
        current_node: Optional[str] = None,
        progress: float = 0.0,
        verified_facts_count: int = 0,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast status update via callback (if provided).

        Handles async callback from sync context using asyncio.

        Args:
            query_id: Query identifier
            status: Current status ("processing", "completed", "failed")
            current_node: Current pipeline node
            progress: Progress 0.0 to 1.0
            verified_facts_count: Number of facts verified
            error: Error message if failed
            metadata: Additional metadata
        """
        if not self.broadcast_callback:
            return

        try:
            # Run async callback in event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, schedule as task
                asyncio.create_task(
                    self.broadcast_callback(
                        query_id, status, current_node, progress,
                        verified_facts_count, error, metadata
                    )
                )
            else:
                # If no loop running, run in new loop
                asyncio.run(
                    self.broadcast_callback(
                        query_id, status, current_node, progress,
                        verified_facts_count, error, metadata
                    )
                )
        except Exception as e:
            logger.error(f"Failed to broadcast update: {e}", exc_info=True)

    def plan_node(
        self,
        state: APEState,
        direct_code: Optional[str] = None
    ) -> APEState:
        """
        PLAN node: Generate executable code.

        Args:
            state: Current state
            direct_code: Direct code (for testing, bypasses real PLAN)

        Returns:
            Updated state with plan
        """
        state.current_node = 'PLAN'
        state.status = StateStatus.PLANNING
        state.nodes_visited.append('PLAN')

        # Broadcast: Starting PLAN node
        self._broadcast_update(
            query_id=state.query_id,
            status="processing",
            current_node="PLAN",
            progress=0.2,
            verified_facts_count=0,
            metadata={"query_text": state.query_text}
        )

        if direct_code:
            # Test mode: use direct code
            state.plan = {
                'code': direct_code,
                'plan_id': f"{state.query_id}_direct",
                'requires_data': False
            }
        else:
            # Production mode: would call Claude API
            state.error_message = 'PLAN node requires Claude API'
            state.status = StateStatus.FAILED

            # Broadcast: PLAN failed
            self._broadcast_update(
                query_id=state.query_id,
                status="failed",
                current_node="PLAN",
                progress=0.2,
                verified_facts_count=0,
                error=state.error_message
            )

        return state

    def fetch_node(self, state: APEState) -> APEState:
        """
        FETCH node: Get market data (conditional).

        Args:
            state: Current state

        Returns:
            Updated state with fetched data
        """
        state.current_node = 'FETCH'
        state.status = StateStatus.FETCHING
        state.nodes_visited.append('FETCH')

        # Broadcast: Starting FETCH node
        self._broadcast_update(
            query_id=state.query_id,
            status="processing",
            current_node="FETCH",
            progress=0.4,
            verified_facts_count=0
        )

        if not state.plan:
            state.error_message = 'No plan available for fetching'
            state.status = StateStatus.FAILED

            # Broadcast: FETCH failed
            self._broadcast_update(
                query_id=state.query_id,
                status="failed",
                current_node="FETCH",
                progress=0.4,
                verified_facts_count=0,
                error=state.error_message
            )

            return state

        # Extract fetch parameters from plan
        tickers = state.plan.get('tickers', [])
        data_type = state.plan.get('data_type', 'OHLCV')
        start_date = state.plan.get('start_date')
        end_date = state.plan.get('end_date')

        if not tickers:
            state.error_message = 'No tickers specified in plan'
            state.status = StateStatus.FAILED
            return state

        # Fetch data for each ticker
        fetched_data = {}

        try:
            for ticker in tickers:
                if data_type.lower() == 'fundamentals':
                    # Fetch fundamentals
                    fundamentals = self.yfinance_adapter.fetch_fundamentals(ticker)
                    fetched_data[ticker] = fundamentals
                else:
                    # Fetch OHLCV (default)
                    if not start_date or not end_date:
                        state.error_message = f'start_date and end_date required for OHLCV data'
                        state.status = StateStatus.FAILED
                        return state

                    df = self.yfinance_adapter.fetch_ohlcv(
                        ticker=ticker,
                        start_date=start_date,
                        end_date=end_date,
                        interval=state.plan.get('interval', '1d')
                    )
                    fetched_data[ticker] = df

            state.fetched_data = fetched_data

        except Exception as e:
            state.error_message = f'Fetch error: {str(e)}'
            state.status = StateStatus.FAILED

            # Broadcast: FETCH failed
            self._broadcast_update(
                query_id=state.query_id,
                status="failed",
                current_node="FETCH",
                progress=0.4,
                verified_facts_count=0,
                error=state.error_message
            )

        return state

    def vee_node(self, state: APEState) -> APEState:
        """
        VEE node: Execute code in sandbox.

        Args:
            state: Current state

        Returns:
            Updated state with execution result
        """
        state.current_node = 'VEE'
        state.status = StateStatus.EXECUTING
        state.nodes_visited.append('VEE')

        # Broadcast: Starting VEE node
        self._broadcast_update(
            query_id=state.query_id,
            status="processing",
            current_node="VEE",
            progress=0.6,
            verified_facts_count=0
        )

        if not state.plan or 'code' not in state.plan:
            state.error_message = 'No code to execute'
            state.status = StateStatus.FAILED

            # Broadcast: VEE failed
            self._broadcast_update(
                query_id=state.query_id,
                status="failed",
                current_node="VEE",
                progress=0.6,
                verified_facts_count=0,
                error=state.error_message
            )

            return state

        try:
            exec_result = self.vee_sandbox.execute(state.plan['code'])
            state.execution_result = exec_result

            if exec_result.status != 'success':
                state.error_message = exec_result.stderr or 'Execution failed'
                state.status = StateStatus.FAILED

                # Broadcast: VEE execution failed
                self._broadcast_update(
                    query_id=state.query_id,
                    status="failed",
                    current_node="VEE",
                    progress=0.6,
                    verified_facts_count=0,
                    error=state.error_message
                )

        except Exception as e:
            state.error_message = str(e)
            state.status = StateStatus.FAILED

            # Broadcast: VEE exception
            self._broadcast_update(
                query_id=state.query_id,
                status="failed",
                current_node="VEE",
                progress=0.6,
                verified_facts_count=0,
                error=state.error_message
            )

        return state

    def gate_node(self, state: APEState) -> APEState:
        """
        GATE node: Validate output and create VerifiedFact.

        Args:
            state: Current state

        Returns:
            Updated state with verified fact
        """
        state.current_node = 'GATE'
        state.status = StateStatus.VALIDATING
        state.nodes_visited.append('GATE')

        # Broadcast: Starting GATE node
        self._broadcast_update(
            query_id=state.query_id,
            status="processing",
            current_node="GATE",
            progress=0.8,
            verified_facts_count=0
        )

        if not state.execution_result:
            state.error_message = 'No execution result to validate'
            state.status = StateStatus.FAILED

            # Broadcast: GATE failed
            self._broadcast_update(
                query_id=state.query_id,
                status="failed",
                current_node="GATE",
                progress=0.8,
                verified_facts_count=0,
                error=state.error_message
            )

            return state

        try:
            validation = self.truth_gate.validate(state.execution_result)

            if not validation.is_valid:
                state.error_message = validation.error_message
                state.status = StateStatus.FAILED

                # Broadcast: GATE validation failed
                self._broadcast_update(
                    query_id=state.query_id,
                    status="failed",
                    current_node="GATE",
                    progress=0.8,
                    verified_facts_count=0,
                    error=state.error_message
                )

                return state

            # Create VerifiedFact
            verified_fact = self.truth_gate.create_verified_fact(
                validation=validation,
                query_id=state.query_id,
                plan_id=state.plan.get('plan_id', 'unknown'),
                code_hash=state.execution_result.code_hash,
                execution_time_ms=state.execution_result.duration_ms,
                memory_used_mb=state.execution_result.memory_used_mb,
                source_code=state.execution_result.code  # Week 5 Day 3: for Debate System
            )

            state.verified_fact = verified_fact
            # Note: Don't set to COMPLETED yet - DEBATE node comes next

        except Exception as e:
            state.error_message = str(e)
            state.status = StateStatus.FAILED

            # Broadcast: GATE exception
            self._broadcast_update(
                query_id=state.query_id,
                status="failed",
                current_node="GATE",
                progress=0.8,
                verified_facts_count=0,
                error=state.error_message
            )

        return state

    def debate_node(self, state: APEState) -> APEState:
        """
        DEBATE node: Multi-perspective analysis (Bull/Bear/Neutral).

        Week 5 Day 2: Run debate on VerifiedFact to adjust confidence.
        Week 11 Day 2: Integrated with real LLM API (OpenAI, Gemini, DeepSeek).

        Args:
            state: Current state with verified_fact

        Returns:
            Updated state with debate_reports and synthesis
        """
        state.current_node = 'DEBATE'
        state.status = StateStatus.DEBATING
        state.nodes_visited.append('DEBATE')

        # Broadcast: Starting DEBATE node
        self._broadcast_update(
            query_id=state.query_id,
            status="processing",
            current_node="DEBATE",
            progress=0.9,
            verified_facts_count=1 if state.verified_fact else 0
        )

        if not state.verified_fact:
            state.error_message = 'No verified fact to debate'
            state.status = StateStatus.FAILED

            # Broadcast: DEBATE failed
            self._broadcast_update(
                query_id=state.query_id,
                status="failed",
                current_node="DEBATE",
                progress=0.9,
                verified_facts_count=0,
                error=state.error_message
            )

            return state

        try:
            # Create debate context from VerifiedFact
            debate_context = DebateContext(
                fact_id=state.verified_fact.fact_id,
                extracted_values=state.verified_fact.extracted_values,
                source_code=state.verified_fact.source_code,
                query_text=state.query_text,
                execution_metadata={
                    'execution_time_ms': state.verified_fact.execution_time_ms,
                    'memory_used_mb': state.verified_fact.memory_used_mb
                }
            )

            # Week 11 Day 2: Use real LLM API or mock agents
            if self.use_real_llm and self.debate_adapter:
                # Real LLM API (production mode)
                logger.info(f"Using real LLM ({self.llm_provider}) for debate")
                debate_reports, synthesis = self.debate_adapter.generate_debate(
                    context=debate_context,
                    original_confidence=state.verified_fact.confidence_score
                )

                # Log cost stats
                stats = self.debate_adapter.get_stats()
                if stats:
                    logger.info(
                        f"LLM API cost: ${stats.get('total_cost', 0):.6f} "
                        f"({stats.get('total_input_tokens', 0)} in + "
                        f"{stats.get('total_output_tokens', 0)} out tokens)"
                    )
            else:
                # Mock agents (test mode)
                logger.info("Using mock debate agents (test mode)")
                bull_agent = DebaterAgent(perspective=Perspective.BULL)
                bear_agent = DebaterAgent(perspective=Perspective.BEAR)
                neutral_agent = DebaterAgent(perspective=Perspective.NEUTRAL)

                bull_report = bull_agent.debate(debate_context)
                bear_report = bear_agent.debate(debate_context)
                neutral_report = neutral_agent.debate(debate_context)

                debate_reports = [bull_report, bear_report, neutral_report]

                # Synthesize
                synthesizer = SynthesizerAgent(enable_synthesis=True)
                synthesis = synthesizer.synthesize(
                    debate_reports=debate_reports,
                    original_confidence=state.verified_fact.confidence_score,
                    fact_id=state.verified_fact.fact_id
                )

            # Update state
            state.debate_reports = debate_reports
            state.synthesis = synthesis

            # Update verified_fact confidence with adjusted value
            state.verified_fact.confidence_score = synthesis.adjusted_confidence

            state.status = StateStatus.COMPLETED

            # Broadcast: DEBATE completed (final update before COMPLETED)
            self._broadcast_update(
                query_id=state.query_id,
                status="processing",
                current_node="DEBATE",
                progress=0.95,
                verified_facts_count=1,
                metadata={
                    "adjusted_confidence": synthesis.adjusted_confidence,
                    "llm_provider": self.llm_provider if self.use_real_llm else "mock",
                    "debate_quality": synthesis.debate_quality_score
                }
            )

        except Exception as e:
            state.error_message = f'Debate failed: {str(e)}'
            state.status = StateStatus.FAILED

            # Broadcast: DEBATE exception
            self._broadcast_update(
                query_id=state.query_id,
                status="failed",
                current_node="DEBATE",
                progress=0.9,
                verified_facts_count=1 if state.verified_fact else 0,
                error=state.error_message
            )

        return state

    def error_node(self, state: APEState) -> APEState:
        """
        ERROR node: Handle errors with retry logic.

        Args:
            state: Current state

        Returns:
            Updated state (retry or give up)
        """
        state.current_node = 'ERROR'
        state.nodes_visited.append('ERROR')
        state.error_count += 1

        if self.enable_retry and state.error_count < self.max_retries:
            # Retry: reset to INITIALIZED
            state.status = StateStatus.INITIALIZED
            state.execution_result = None
        else:
            # Give up
            state.status = StateStatus.FAILED

        return state

    def get_next_node(self, status: StateStatus) -> str:
        """
        Determine next node based on current status.

        Args:
            status: Current state status

        Returns:
            Next node name or 'END'
        """
        routing = {
            StateStatus.INITIALIZED: 'PLAN',
            StateStatus.PLANNING: 'should_fetch',  # Conditional: FETCH or VEE
            StateStatus.FETCHING: 'VEE',
            StateStatus.EXECUTING: 'GATE',
            StateStatus.VALIDATING: 'DEBATE',  # Week 5 Day 3: Add debate after validation
            StateStatus.DEBATING: 'END',
            StateStatus.COMPLETED: 'END',
            StateStatus.FAILED: 'ERROR' if self.enable_retry else 'END'
        }

        return routing.get(status, 'END')

    def should_fetch(self, state: APEState) -> str:
        """
        Conditional edge: should we fetch data?

        Args:
            state: Current state

        Returns:
            'FETCH' or 'VEE'
        """
        if state.plan and state.plan.get('requires_data', False):
            return 'FETCH'
        else:
            return 'VEE'

    def run(
        self,
        query_id: str,
        query_text: str,
        direct_code: Optional[str] = None,
        use_plan: bool = False
    ) -> APEState:
        """
        Run state machine end-to-end.

        Args:
            query_id: Query identifier
            query_text: User query
            direct_code: Direct code (for testing)
            use_plan: Enable PLAN node (requires Claude API)

        Returns:
            Final state
        """
        # Initialize state
        state = APEState.from_query(query_id, query_text)

        # Run state machine
        while state.status not in [StateStatus.COMPLETED, StateStatus.FAILED]:
            next_node = self.get_next_node(state.status)

            if next_node == 'END':
                break

            # Handle conditional edge
            if next_node == 'should_fetch':
                next_node = self.should_fetch(state)

            # Execute node
            if next_node == 'PLAN':
                state = self.plan_node(state, direct_code=direct_code)
            elif next_node == 'FETCH':
                state = self.fetch_node(state)
            elif next_node == 'VEE':
                state = self.vee_node(state)
            elif next_node == 'GATE':
                state = self.gate_node(state)
            elif next_node == 'DEBATE':
                state = self.debate_node(state)
            elif next_node == 'ERROR':
                state = self.error_node(state)

                # Check if we should give up
                if state.error_count >= self.max_retries:
                    break

        # Broadcast final status
        if state.status == StateStatus.COMPLETED:
            self._broadcast_update(
                query_id=state.query_id,
                status="completed",
                current_node=None,
                progress=1.0,
                verified_facts_count=1 if state.verified_fact else 0,
                metadata={
                    "duration_ms": int((time.time() - state.start_time) * 1000),
                    "nodes_visited": state.nodes_visited
                }
            )
        elif state.status == StateStatus.FAILED:
            self._broadcast_update(
                query_id=state.query_id,
                status="failed",
                current_node=state.current_node,
                progress=0.0,
                verified_facts_count=0,
                error=state.error_message,
                metadata={
                    "duration_ms": int((time.time() - state.start_time) * 1000),
                    "nodes_visited": state.nodes_visited,
                    "error_count": state.error_count
                }
            )

        return state
