"""
Parallel Multi-Agent Orchestrator
Week 7 Day 1 - Advanced Multi-Agent Coordination

Coordinates multiple agents executing in parallel for complex queries.
Supports:
- Parallel PLAN execution for sub-queries
- Agent communication protocols
- Shared state management
- Result aggregation
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from uuid import uuid4

from .langgraph_orchestrator import LangGraphOrchestrator, APEState, StateStatus
from ..truth_boundary.gate import VerifiedFact

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Agent roles in multi-agent system."""
    COORDINATOR = "coordinator"  # Orchestrates other agents
    PLANNER = "planner"  # Generates analysis plans
    EXECUTOR = "executor"  # Executes code in VEE
    AGGREGATOR = "aggregator"  # Combines results
    VALIDATOR = "validator"  # Validates facts


class MessageType(Enum):
    """Inter-agent message types."""
    TASK_ASSIGNMENT = "task_assignment"
    RESULT_READY = "result_ready"
    ERROR_REPORT = "error_report"
    STATE_UPDATE = "state_update"
    COORDINATION = "coordination"


@dataclass
class AgentMessage:
    """Message passed between agents."""
    message_id: str
    sender_id: str
    receiver_id: str
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: int = 0  # Higher = more urgent


@dataclass
class AgentTask:
    """Task assigned to an agent."""
    task_id: str
    agent_id: str
    query: str
    context: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # Task IDs that must complete first
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class SharedState:
    """Shared state accessible by all agents."""
    session_id: str
    global_context: Dict[str, Any] = field(default_factory=dict)
    task_results: Dict[str, Any] = field(default_factory=dict)  # task_id -> result
    verified_facts: List[VerifiedFact] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def set_result(self, task_id: str, result: Any):
        """Thread-safe result storage."""
        async with self.lock:
            self.task_results[task_id] = result
            logger.debug(f"Stored result for task {task_id}")

    async def get_result(self, task_id: str) -> Optional[Any]:
        """Thread-safe result retrieval."""
        async with self.lock:
            return self.task_results.get(task_id)

    async def add_fact(self, fact: VerifiedFact):
        """Thread-safe fact addition."""
        async with self.lock:
            self.verified_facts.append(fact)
            logger.debug(f"Added verified fact: {fact.fact_id}")


class ParallelAgent:
    """
    Single agent in multi-agent system.

    Each agent has:
    - Unique ID
    - Role (coordinator, planner, executor, etc.)
    - Message queue for communication
    - Reference to shared state
    - LangGraph orchestrator for task execution
    """

    def __init__(
        self,
        agent_id: str,
        role: AgentRole,
        shared_state: SharedState,
        orchestrator: Optional[LangGraphOrchestrator] = None
    ):
        self.agent_id = agent_id
        self.role = role
        self.shared_state = shared_state
        self.orchestrator = orchestrator  # Don't create default orchestrator to avoid requiring API key

        # Message queue (asyncio.Queue for async support)
        self.message_queue: asyncio.Queue[AgentMessage] = asyncio.Queue()

        # Current tasks
        self.current_tasks: Dict[str, AgentTask] = {}

        # Statistics
        self.tasks_completed = 0
        self.tasks_failed = 0

    async def send_message(self, receiver_id: str, message_type: MessageType, payload: Dict[str, Any]):
        """Send message to another agent."""
        message = AgentMessage(
            message_id=str(uuid4()),
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            message_type=message_type,
            payload=payload
        )

        logger.debug(f"Agent {self.agent_id} sending {message_type.value} to {receiver_id}")

        # In real implementation, this would route through message broker
        # For now, we'll use direct queue injection (handled by ParallelOrchestrator)
        return message

    async def receive_message(self) -> AgentMessage:
        """Receive message from queue (blocking)."""
        return await self.message_queue.get()

    async def execute_task(self, task: AgentTask) -> Any:
        """
        Execute assigned task.

        Behavior depends on agent role:
        - PLANNER: Generate analysis plan
        - EXECUTOR: Execute code in VEE
        - VALIDATOR: Validate results
        - AGGREGATOR: Combine multiple results
        """
        task.status = "running"
        task.started_at = datetime.utcnow()

        try:
            if self.role == AgentRole.PLANNER:
                result = await self._execute_planning(task)
            elif self.role == AgentRole.EXECUTOR:
                result = await self._execute_code(task)
            elif self.role == AgentRole.VALIDATOR:
                result = await self._validate_results(task)
            elif self.role == AgentRole.AGGREGATOR:
                result = await self._aggregate_results(task)
            else:
                raise ValueError(f"Unknown role: {self.role}")

            task.status = "completed"
            task.result = result
            task.completed_at = datetime.utcnow()
            self.tasks_completed += 1

            # Store result in shared state
            await self.shared_state.set_result(task.task_id, result)

            logger.info(f"Agent {self.agent_id} completed task {task.task_id}")
            return result

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            self.tasks_failed += 1
            logger.error(f"Agent {self.agent_id} task {task.task_id} failed: {e}")
            raise

    async def _execute_planning(self, task: AgentTask) -> Dict[str, Any]:
        """Execute PLAN node for query."""
        logger.debug(f"Agent {self.agent_id} planning: {task.query}")

        # Use LangGraph orchestrator to generate plan
        state = APEState(
            query_id=task.task_id,
            query_text=task.query
        )

        # Execute just the PLAN node
        # (In full implementation, would use orchestrator.plan_node)
        plan = {
            "description": f"Plan for: {task.query}",
            "code": "# Generated code placeholder",
            "data_requirements": {}
        }

        return plan

    async def _execute_code(self, task: AgentTask) -> Dict[str, Any]:
        """Execute code in VEE sandbox."""
        logger.debug(f"Agent {self.agent_id} executing code for task {task.task_id}")

        # Get plan from task context
        plan = task.context.get("plan")
        if not plan:
            raise ValueError("No plan provided for execution")

        # Execute using VEE (simplified for now)
        result = {
            "status": "success",
            "output": "Mock execution result",
            "execution_time_ms": 100
        }

        return result

    async def _validate_results(self, task: AgentTask) -> Dict[str, Any]:
        """Validate execution results."""
        logger.debug(f"Agent {self.agent_id} validating results for task {task.task_id}")

        result = task.context.get("result")
        if not result:
            raise ValueError("No result provided for validation")

        # Simple validation (in production, use Doubter agent)
        validation = {
            "is_valid": True,
            "confidence": 0.85,
            "issues": []
        }

        return validation

    async def _aggregate_results(self, task: AgentTask) -> Dict[str, Any]:
        """Aggregate results from multiple tasks."""
        logger.debug(f"Agent {self.agent_id} aggregating results")

        # Get results from dependencies
        dependency_results = []
        for dep_task_id in task.dependencies:
            result = await self.shared_state.get_result(dep_task_id)
            if result:
                dependency_results.append(result)

        # Simple aggregation (in production, use Synthesis agent)
        aggregated = {
            "combined_results": dependency_results,
            "summary": f"Aggregated {len(dependency_results)} results",
            "confidence": 0.80
        }

        return aggregated


class ParallelOrchestrator:
    """
    Coordinates multiple agents executing tasks in parallel.

    Features:
    - Task decomposition (break complex query into sub-tasks)
    - Dependency management (ensure tasks execute in correct order)
    - Parallel execution (run independent tasks concurrently)
    - Result aggregation (combine results from multiple agents)
    - Message routing (route messages between agents)
    """

    def __init__(self, max_parallel_agents: int = 5):
        self.max_parallel_agents = max_parallel_agents
        self.agents: Dict[str, ParallelAgent] = {}
        self.shared_state: Optional[SharedState] = None
        self.message_broker: asyncio.Queue[AgentMessage] = asyncio.Queue()

    def create_agent(self, role: AgentRole, orchestrator: Optional[LangGraphOrchestrator] = None) -> ParallelAgent:
        """Create new agent with specified role."""
        agent_id = f"{role.value}_{str(uuid4())[:8]}"

        if not self.shared_state:
            raise ValueError("Shared state not initialized. Call initialize_session() first.")

        agent = ParallelAgent(
            agent_id=agent_id,
            role=role,
            shared_state=self.shared_state,
            orchestrator=orchestrator
        )

        self.agents[agent_id] = agent
        logger.info(f"Created agent {agent_id} with role {role.value}")

        return agent

    async def initialize_session(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Initialize new parallel execution session."""
        session_id = str(uuid4())

        self.shared_state = SharedState(
            session_id=session_id,
            global_context=context or {},
        )

        logger.info(f"Initialized session {session_id} for query: {query}")
        return session_id

    async def decompose_query(self, query: str) -> List[AgentTask]:
        """
        Decompose complex query into sub-tasks.

        Example:
        Query: "Compare Sharpe ratios of AAPL, MSFT, GOOGL for 2023"
        Sub-tasks:
        1. Calculate Sharpe ratio for AAPL
        2. Calculate Sharpe ratio for MSFT
        3. Calculate Sharpe ratio for GOOGL
        4. Aggregate and compare results
        """
        # Simple heuristic-based decomposition (in production, use LLM)
        tasks = []

        # Detect multi-ticker queries
        tickers = self._extract_tickers(query)

        if len(tickers) > 1:
            # Create task for each ticker
            for ticker in tickers:
                task_query = query.replace(", ".join(tickers), ticker)
                task = AgentTask(
                    task_id=str(uuid4()),
                    agent_id="",  # Will be assigned later
                    query=task_query,
                    context={"ticker": ticker}
                )
                tasks.append(task)

            # Create aggregation task (depends on all ticker tasks)
            agg_task = AgentTask(
                task_id=str(uuid4()),
                agent_id="",
                query=f"Aggregate results for: {query}",
                dependencies=[t.task_id for t in tasks]
            )
            tasks.append(agg_task)
        else:
            # Single task
            task = AgentTask(
                task_id=str(uuid4()),
                agent_id="",
                query=query
            )
            tasks.append(task)

        logger.info(f"Decomposed query into {len(tasks)} tasks")
        return tasks

    def _extract_tickers(self, query: str) -> List[str]:
        """Extract ticker symbols from query (simple pattern matching)."""
        # Simple heuristic: uppercase 1-5 letter words
        import re
        pattern = r'\b[A-Z]{1,5}\b'
        tickers = re.findall(pattern, query)

        # Filter out common words
        excluded = {'AND', 'OR', 'THE', 'FOR', 'IN', 'ON', 'AT', 'TO', 'FROM'}
        tickers = [t for t in tickers if t not in excluded]

        return tickers

    async def assign_tasks(self, tasks: List[AgentTask]):
        """Assign tasks to appropriate agents based on role."""
        for task in tasks:
            # Determine required role
            if task.dependencies:
                # Aggregation task
                role = AgentRole.AGGREGATOR
            else:
                # Planning task
                role = AgentRole.PLANNER

            # Find or create agent with this role
            agent = self._find_agent_by_role(role)
            if not agent:
                agent = self.create_agent(role)

            task.agent_id = agent.agent_id
            agent.current_tasks[task.task_id] = task

            logger.debug(f"Assigned task {task.task_id} to agent {agent.agent_id}")

    def _find_agent_by_role(self, role: AgentRole) -> Optional[ParallelAgent]:
        """Find available agent with specified role."""
        for agent in self.agents.values():
            if agent.role == role and len(agent.current_tasks) < 3:
                return agent
        return None

    async def execute_parallel(self, tasks: List[AgentTask]) -> Dict[str, Any]:
        """
        Execute tasks in parallel, respecting dependencies.

        Uses asyncio.gather for parallel execution.
        """
        # Build dependency graph
        task_map = {task.task_id: task for task in tasks}

        # Execute in waves (tasks with satisfied dependencies)
        completed_tasks = set()
        results = {}

        while len(completed_tasks) < len(tasks):
            # Find tasks ready to execute (dependencies satisfied)
            ready_tasks = [
                task for task in tasks
                if task.task_id not in completed_tasks
                and all(dep in completed_tasks for dep in task.dependencies)
            ]

            if not ready_tasks:
                raise RuntimeError("Circular dependency detected or all tasks failed")

            logger.info(f"Executing wave of {len(ready_tasks)} parallel tasks")

            # Execute ready tasks in parallel
            task_coroutines = []
            for task in ready_tasks:
                agent = self.agents.get(task.agent_id)
                if agent:
                    task_coroutines.append(agent.execute_task(task))

            # Wait for all tasks in this wave to complete
            wave_results = await asyncio.gather(*task_coroutines, return_exceptions=True)

            # Process results
            for task, result in zip(ready_tasks, wave_results):
                if isinstance(result, Exception):
                    logger.error(f"Task {task.task_id} failed: {result}")
                    task.status = "failed"
                    task.error = str(result)
                else:
                    results[task.task_id] = result
                    completed_tasks.add(task.task_id)

        logger.info(f"Completed all {len(tasks)} tasks")
        return results

    async def execute_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute complex query using parallel agents.

        Workflow:
        1. Initialize session
        2. Decompose query into tasks
        3. Assign tasks to agents
        4. Execute tasks in parallel
        5. Aggregate results
        """
        # Initialize
        session_id = await self.initialize_session(query, context)

        # Decompose
        tasks = await self.decompose_query(query)

        # Assign
        await self.assign_tasks(tasks)

        # Execute
        results = await self.execute_parallel(tasks)

        # Return aggregated result
        return {
            "session_id": session_id,
            "query": query,
            "tasks_completed": len(results),
            "results": results,
            "verified_facts": self.shared_state.verified_facts if self.shared_state else []
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics from all agents."""
        total_completed = sum(agent.tasks_completed for agent in self.agents.values())
        total_failed = sum(agent.tasks_failed for agent in self.agents.values())

        return {
            "total_agents": len(self.agents),
            "agents_by_role": {
                role.value: sum(1 for a in self.agents.values() if a.role == role)
                for role in AgentRole
            },
            "total_tasks_completed": total_completed,
            "total_tasks_failed": total_failed,
            "success_rate": total_completed / (total_completed + total_failed) if (total_completed + total_failed) > 0 else 0
        }
