"""
DSPy-based PLAN Node optimizer.

Week 5 Day 1: Infrastructure for prompt optimization.

Design:
- Uses DSPy to optimize PLAN Node system prompt
- Evaluation metrics: executability, code quality, temporal validity
- Training data: user queries + expected AnalysisPlan outputs
- Optimizer: DSPy's BootstrapFewShot or MIPRO

Architecture:
1. Define DSPy Signature (input/output structure)
2. Create Module (wraps PLAN generation logic)
3. Define metrics (executability, quality, temporal)
4. Compile optimizer with training data
5. Export optimized prompts

Status: Infrastructure ready, requires API key for actual optimization.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import json
import dspy

from ..orchestration.schemas.plan_output import AnalysisPlan
from .metrics import CompositeMetric


@dataclass
class TrainingExample:
    """
    Training example for DSPy optimization.

    Attributes:
        user_query: User's question
        expected_plan: Expected AnalysisPlan (gold standard)
        query_date: Optional query date for temporal validation
        context: Optional additional context
    """
    user_query: str
    expected_plan: AnalysisPlan
    query_date: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class PlanGenerationSignature(dspy.Signature):
    """DSPy signature for PLAN generation task."""

    user_query = dspy.InputField(desc="User's financial analysis question")
    context = dspy.InputField(desc="Optional context (previous queries, preferences)", default="")

    plan = dspy.OutputField(
        desc="Executable analysis plan as JSON matching AnalysisPlan schema. "
             "CRITICAL: Generate CODE, not numbers. All numerical outputs from execution."
    )


class PlanGenerationModule(dspy.Module):
    """
    DSPy Module for PLAN generation.

    Wraps the PLAN Node logic in DSPy framework.
    """

    def __init__(self):
        super().__init__()
        # ChainOfThought for reasoning before plan generation
        self.generate = dspy.ChainOfThought(PlanGenerationSignature)

    def forward(self, user_query: str, context: str = "") -> dspy.Prediction:
        """
        Generate analysis plan.

        Args:
            user_query: User's question
            context: Optional context

        Returns:
            DSPy Prediction with plan JSON
        """
        prediction = self.generate(user_query=user_query, context=context)
        return prediction


class PlanOptimizer:
    """
    Optimizer for PLAN Node prompts using DSPy.

    Usage:
        optimizer = PlanOptimizer(api_key="...")
        optimizer.add_training_examples(examples)
        optimized_module = optimizer.optimize()

        # Export optimized prompt
        optimized_prompt = optimizer.export_optimized_prompt()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20250929",
        metric_weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize optimizer.

        Args:
            api_key: Anthropic API key (required for optimization)
            model: Claude model to use
            metric_weights: Custom weights for composite metric
        """
        self.api_key = api_key
        self.model = model
        self.training_examples: List[TrainingExample] = []
        self.optimized_module: Optional[PlanGenerationModule] = None

        # Evaluation metric
        self.metric = CompositeMetric(weights=metric_weights)

        # Configure DSPy (if API key provided)
        if api_key:
            # Note: DSPy doesn't have native Anthropic support yet
            # This is a placeholder for when it's available
            # For now, we'll use mock mode for testing
            pass

    def add_training_example(self, example: TrainingExample):
        """
        Add a training example.

        Args:
            example: TrainingExample with query and expected plan
        """
        self.training_examples.append(example)

    def add_training_examples(self, examples: List[TrainingExample]):
        """
        Add multiple training examples.

        Args:
            examples: List of TrainingExample
        """
        self.training_examples.extend(examples)

    def optimize(
        self,
        optimizer_type: str = "bootstrap",
        max_bootstrapped_demos: int = 4,
        max_labeled_demos: int = 8
    ) -> PlanGenerationModule:
        """
        Optimize PLAN generation prompt using DSPy.

        Args:
            optimizer_type: 'bootstrap' or 'mipro'
            max_bootstrapped_demos: Max examples to bootstrap
            max_labeled_demos: Max labeled examples to use

        Returns:
            Optimized PlanGenerationModule

        Raises:
            ValueError: If no API key or no training examples
        """
        if not self.api_key:
            raise ValueError(
                "API key required for optimization. "
                "Use mock_optimize() for testing without API."
            )

        if not self.training_examples:
            raise ValueError("No training examples provided")

        # Convert training examples to DSPy format
        trainset = self._convert_to_dspy_format()

        # Define evaluation metric for DSPy
        def evaluate_plan(example, prediction, trace=None) -> float:
            """Evaluate generated plan using composite metric."""
            try:
                # Parse prediction as AnalysisPlan
                plan_dict = json.loads(prediction.plan)
                plan = AnalysisPlan(**plan_dict)

                # Evaluate with composite metric
                result = self.metric.evaluate(
                    plan,
                    query_date=example.query_date if hasattr(example, 'query_date') else None
                )
                return result.score

            except (json.JSONDecodeError, TypeError, ValueError):
                # Invalid JSON or schema mismatch = 0 score
                return 0.0

        # Initialize module
        module = PlanGenerationModule()

        # Choose optimizer
        if optimizer_type == "bootstrap":
            optimizer = dspy.BootstrapFewShot(
                metric=evaluate_plan,
                max_bootstrapped_demos=max_bootstrapped_demos,
                max_labeled_demos=max_labeled_demos
            )
        elif optimizer_type == "mipro":
            # MIPRO (More Intelligent Prompt Optimization)
            optimizer = dspy.MIPROv2(
                metric=evaluate_plan,
                num_candidates=10,
                init_temperature=1.0
            )
        else:
            raise ValueError(f"Unknown optimizer type: {optimizer_type}")

        # Compile (optimize) the module
        self.optimized_module = optimizer.compile(
            module,
            trainset=trainset
        )

        return self.optimized_module

    def mock_optimize(self) -> PlanGenerationModule:
        """
        Mock optimization for testing without API key.

        Returns a module with basic few-shot examples.

        Returns:
            PlanGenerationModule with few-shot demos
        """
        module = PlanGenerationModule()

        # Add few-shot examples manually (mock optimization)
        few_shot_demos = self._convert_to_dspy_format()
        if few_shot_demos:
            # Simulate optimized prompts with examples
            module.generate.demos = few_shot_demos[:4]  # Use first 4 as demos

        self.optimized_module = module
        return module

    def export_optimized_prompt(self) -> str:
        """
        Export optimized system prompt.

        Returns:
            Optimized prompt as string

        Raises:
            ValueError: If optimization not run yet
        """
        if not self.optimized_module:
            raise ValueError("Run optimize() or mock_optimize() first")

        # Extract prompt from optimized module
        # DSPy stores optimized prompts in module.generate
        prompt_parts = []

        # Base instruction
        prompt_parts.append(
            "You are an expert financial analyst planning system.\n"
            "Generate EXECUTABLE ANALYSIS PLANS from user queries.\n"
        )

        # Few-shot examples (if any)
        if hasattr(self.optimized_module.generate, 'demos') and self.optimized_module.generate.demos:
            prompt_parts.append("\n## EXAMPLES:\n")
            for i, demo in enumerate(self.optimized_module.generate.demos, 1):
                prompt_parts.append(f"\nExample {i}:")
                prompt_parts.append(f"Query: {demo.user_query}")
                prompt_parts.append(f"Plan: {demo.plan}\n")

        # Constraints
        prompt_parts.append(
            "\n## CONSTRAINTS:\n"
            "1. Generate CODE, NEVER numbers directly\n"
            "2. ALL numerical outputs must come from code execution\n"
            "3. Use only approved data sources: yfinance, FRED, SEC filings\n"
            "4. No file system or subprocess access\n"
        )

        return '\n'.join(prompt_parts)

    def evaluate_on_testset(
        self,
        testset: List[TrainingExample]
    ) -> Dict[str, float]:
        """
        Evaluate optimized module on test set.

        Args:
            testset: List of test examples

        Returns:
            Dictionary with average scores
        """
        if not self.optimized_module:
            raise ValueError("Run optimize() or mock_optimize() first")

        scores = {
            'executability': [],
            'quality': [],
            'temporal': [],
            'composite': []
        }

        for example in testset:
            # Generate plan with optimized module
            prediction = self.optimized_module(
                user_query=example.user_query,
                context=json.dumps(example.context) if example.context else ""
            )

            try:
                # Parse prediction
                plan_dict = json.loads(prediction.plan)
                plan = AnalysisPlan(**plan_dict)

                # Evaluate
                result = self.metric.evaluate(plan, query_date=example.query_date)

                scores['composite'].append(result.score)
                scores['executability'].append(result.details['executability'])
                scores['quality'].append(result.details['quality'])
                scores['temporal'].append(result.details['temporal'])

            except (json.JSONDecodeError, TypeError, ValueError):
                # Failed to parse = 0 scores
                scores['composite'].append(0.0)
                scores['executability'].append(0.0)
                scores['quality'].append(0.0)
                scores['temporal'].append(0.0)

        # Calculate averages
        return {
            metric: sum(values) / len(values) if values else 0.0
            for metric, values in scores.items()
        }

    def _convert_to_dspy_format(self) -> List[dspy.Example]:
        """Convert training examples to DSPy Example format."""
        dspy_examples = []

        for ex in self.training_examples:
            # Serialize expected plan to JSON
            plan_json = ex.expected_plan.model_dump_json(indent=2)

            dspy_example = dspy.Example(
                user_query=ex.user_query,
                context=json.dumps(ex.context) if ex.context else "",
                plan=plan_json
            ).with_inputs("user_query", "context")

            # Add query_date as metadata (for evaluation)
            if ex.query_date:
                dspy_example = dspy_example.with_inputs("query_date")
                dspy_example.query_date = ex.query_date

            dspy_examples.append(dspy_example)

        return dspy_examples

    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        return {
            "training_examples": len(self.training_examples),
            "optimized": self.optimized_module is not None,
            "model": self.model,
            "metric_weights": self.metric.weights
        }
