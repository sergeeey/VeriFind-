"""
Unit tests for Reasoning Chains.

Week 10 Day 2: Chain-of-thought reasoning for complex financial analysis.

Tests validate that:
1. ReasoningStep tracks individual steps correctly
2. ReasoningChain executes steps in order
3. Confidence propagates through the chain
4. Explanations are generated
5. ChainBuilder constructs chains from queries
"""

import pytest
from src.reasoning.chains import (
    ReasoningStep,
    ReasoningChain,
    ReasoningChainBuilder,
    StepAction,
    ChainResult
)


class TestReasoningStep:
    """Tests for ReasoningStep dataclass."""

    # ========================================================================
    # Basic Step Creation
    # ========================================================================

    def test_create_reasoning_step(self):
        """Test creating a reasoning step."""
        step = ReasoningStep(
            step_number=1,
            description="Calculate P/E ratio for AAPL",
            action=StepAction.CALCULATE,
            inputs={"ticker": "AAPL", "metric": "pe_ratio"},
            output=None,
            confidence=1.0
        )

        assert step.step_number == 1
        assert step.description == "Calculate P/E ratio for AAPL"
        assert step.action == StepAction.CALCULATE
        assert step.inputs["ticker"] == "AAPL"
        assert step.confidence == 1.0

    def test_step_with_output(self):
        """Test step after execution with output."""
        step = ReasoningStep(
            step_number=1,
            description="Calculate Sharpe ratio",
            action=StepAction.CALCULATE,
            inputs={"ticker": "AAPL"},
            output={"value": 1.5, "metric": "sharpe_ratio"},
            confidence=0.95
        )

        assert step.output is not None
        assert step.output["value"] == 1.5
        assert step.confidence == 0.95

    def test_step_actions(self):
        """Test different step actions."""
        actions = [
            StepAction.CALCULATE,
            StepAction.COMPARE,
            StepAction.ANALYZE,
            StepAction.CONCLUDE
        ]

        for i, action in enumerate(actions):
            step = ReasoningStep(
                step_number=i + 1,
                description=f"Step {i + 1}",
                action=action,
                inputs={},
                output=None,
                confidence=1.0
            )
            assert step.action == action


class TestReasoningChain:
    """Tests for ReasoningChain class."""

    def setup_method(self):
        """Setup test instance."""
        self.chain = ReasoningChain(query="Test query")

    # ========================================================================
    # Chain Construction
    # ========================================================================

    def test_create_empty_chain(self):
        """Test creating an empty reasoning chain."""
        chain = ReasoningChain(query="What is the Sharpe ratio of AAPL?")

        assert chain.query == "What is the Sharpe ratio of AAPL?"
        assert len(chain.steps) == 0
        assert chain.is_complete() is False

    def test_add_step_to_chain(self):
        """Test adding a step to chain."""
        step = ReasoningStep(
            step_number=1,
            description="Fetch price data",
            action=StepAction.CALCULATE,
            inputs={"ticker": "AAPL"},
            output=None,
            confidence=1.0
        )

        self.chain.add_step(step)

        assert len(self.chain.steps) == 1
        assert self.chain.steps[0] == step

    def test_add_multiple_steps(self):
        """Test adding multiple steps in order."""
        steps = [
            ReasoningStep(1, "Step 1", StepAction.CALCULATE, {}, None, 1.0),
            ReasoningStep(2, "Step 2", StepAction.COMPARE, {}, None, 1.0),
            ReasoningStep(3, "Step 3", StepAction.CONCLUDE, {}, None, 1.0),
        ]

        for step in steps:
            self.chain.add_step(step)

        assert len(self.chain.steps) == 3
        assert self.chain.steps[0].step_number == 1
        assert self.chain.steps[2].step_number == 3

    # ========================================================================
    # Chain Execution
    # ========================================================================

    def test_execute_empty_chain(self):
        """Test executing empty chain fails gracefully."""
        result = self.chain.execute()

        assert result.success is False
        assert "empty" in result.error.lower()

    def test_execute_single_step_chain(self):
        """Test executing chain with single step."""
        step = ReasoningStep(
            step_number=1,
            description="Calculate Sharpe ratio",
            action=StepAction.CALCULATE,
            inputs={"ticker": "AAPL", "metric": "sharpe_ratio"},
            output=None,
            confidence=1.0
        )
        self.chain.add_step(step)

        result = self.chain.execute()

        assert result.success is True
        assert len(result.steps) == 1
        assert result.final_output is not None

    def test_execute_multi_step_chain(self):
        """Test executing chain with multiple steps."""
        steps = [
            ReasoningStep(1, "Calculate PE AAPL", StepAction.CALCULATE, {"ticker": "AAPL"}, None, 1.0),
            ReasoningStep(2, "Calculate PE MSFT", StepAction.CALCULATE, {"ticker": "MSFT"}, None, 1.0),
            ReasoningStep(3, "Compare PEs", StepAction.COMPARE, {}, None, 1.0),
            ReasoningStep(4, "Conclude", StepAction.CONCLUDE, {}, None, 1.0),
        ]

        for step in steps:
            self.chain.add_step(step)

        result = self.chain.execute()

        assert result.success is True
        assert len(result.steps) == 4
        assert result.final_output is not None

    # ========================================================================
    # Confidence Propagation
    # ========================================================================

    def test_confidence_propagation_perfect(self):
        """Test confidence when all steps have confidence 1.0."""
        steps = [
            ReasoningStep(1, "Step 1", StepAction.CALCULATE, {}, {"value": 10}, 1.0),
            ReasoningStep(2, "Step 2", StepAction.CALCULATE, {}, {"value": 20}, 1.0),
            ReasoningStep(3, "Step 3", StepAction.CONCLUDE, {}, {"result": "done"}, 1.0),
        ]

        for step in steps:
            self.chain.add_step(step)

        result = self.chain.execute()

        # Overall confidence should be 1.0 (minimum or average)
        assert result.overall_confidence == 1.0

    def test_confidence_propagation_degraded(self):
        """Test confidence degradation through chain."""
        steps = [
            ReasoningStep(1, "Step 1", StepAction.CALCULATE, {}, {"value": 10}, 0.9),
            ReasoningStep(2, "Step 2", StepAction.CALCULATE, {}, {"value": 20}, 0.8),
            ReasoningStep(3, "Step 3", StepAction.CONCLUDE, {}, {"result": "done"}, 0.95),
        ]

        for step in steps:
            self.chain.add_step(step)

        result = self.chain.execute()

        # Overall confidence should be minimum (0.8) or product
        assert result.overall_confidence <= 0.9
        assert result.overall_confidence > 0

    def test_confidence_minimum_propagation(self):
        """Test that confidence uses minimum strategy."""
        steps = [
            ReasoningStep(1, "High confidence", StepAction.CALCULATE, {}, {}, 0.95),
            ReasoningStep(2, "Low confidence", StepAction.CALCULATE, {}, {}, 0.5),  # Weak link
            ReasoningStep(3, "High confidence", StepAction.CONCLUDE, {}, {}, 0.9),
        ]

        for step in steps:
            self.chain.add_step(step)

        result = self.chain.execute()

        # Weakest link principle
        assert result.overall_confidence == 0.5

    # ========================================================================
    # Explanation Generation
    # ========================================================================

    def test_generate_explanation(self):
        """Test generating human-readable explanation."""
        steps = [
            ReasoningStep(1, "Fetch AAPL data", StepAction.CALCULATE, {"ticker": "AAPL"}, {"pe": 25}, 0.95),
            ReasoningStep(2, "Fetch MSFT data", StepAction.CALCULATE, {"ticker": "MSFT"}, {"pe": 30}, 0.95),
            ReasoningStep(3, "Compare valuations", StepAction.COMPARE, {}, {"winner": "AAPL"}, 0.9),
        ]

        for step in steps:
            self.chain.add_step(step)

        result = self.chain.execute()
        explanation = result.explanation

        assert explanation is not None
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        # Should contain step descriptions
        assert "Fetch AAPL data" in explanation or "Step 1" in explanation

    def test_explanation_includes_confidence(self):
        """Test that explanation includes confidence scores."""
        steps = [
            ReasoningStep(1, "Calculate metric", StepAction.CALCULATE, {}, {"value": 1.5}, 0.85),
        ]

        for step in steps:
            self.chain.add_step(step)

        result = self.chain.execute()
        explanation = result.explanation

        # Should mention confidence in some form
        assert "confidence" in explanation.lower() or "0.85" in explanation or "85%" in explanation


class TestReasoningChainBuilder:
    """Tests for ReasoningChainBuilder class."""

    def setup_method(self):
        """Setup test instance."""
        self.builder = ReasoningChainBuilder()

    # ========================================================================
    # Chain Building from Queries
    # ========================================================================

    def test_build_simple_calculation_chain(self):
        """Test building chain for simple calculation."""
        query = "What is the Sharpe ratio of AAPL?"

        chain = self.builder.build(query)

        assert chain is not None
        assert chain.query == query
        assert len(chain.steps) >= 1
        # Should have at least a calculation step
        assert any(step.action == StepAction.CALCULATE for step in chain.steps)

    def test_build_comparison_chain(self):
        """Test building chain for comparison query."""
        query = "Compare the P/E ratios of AAPL and MSFT"

        chain = self.builder.build(query)

        assert chain is not None
        assert len(chain.steps) >= 3
        # Should have: calculate AAPL, calculate MSFT, compare
        calc_steps = [s for s in chain.steps if s.action == StepAction.CALCULATE]
        compare_steps = [s for s in chain.steps if s.action == StepAction.COMPARE]

        assert len(calc_steps) >= 2
        assert len(compare_steps) >= 1

    def test_build_valuation_chain(self):
        """Test building chain for valuation question."""
        query = "Is AAPL undervalued compared to MSFT?"

        chain = self.builder.build(query)

        assert chain is not None
        assert len(chain.steps) >= 4
        # Should have: calculate, calculate, compare, conclude
        actions = [step.action for step in chain.steps]
        assert StepAction.CALCULATE in actions
        assert StepAction.COMPARE in actions
        assert StepAction.CONCLUDE in actions

    # ========================================================================
    # Template Matching
    # ========================================================================

    def test_template_matching_sharpe(self):
        """Test template matching for Sharpe ratio queries."""
        queries = [
            "Calculate Sharpe ratio for AAPL",
            "What is the Sharpe ratio of MSFT?",
            "Sharpe ratio TSLA"
        ]

        for query in queries:
            chain = self.builder.build(query)
            assert chain is not None
            assert len(chain.steps) >= 1

    def test_template_matching_comparison(self):
        """Test template matching for comparison queries."""
        queries = [
            "Compare AAPL and MSFT",
            "AAPL vs MSFT performance",
            "Which is better: AAPL or MSFT?"
        ]

        for query in queries:
            chain = self.builder.build(query)
            assert chain is not None
            assert len(chain.steps) >= 2

    # ========================================================================
    # Logical Flow Validation
    # ========================================================================

    def test_validates_logical_flow(self):
        """Test that builder validates logical flow of steps."""
        query = "Compare Sharpe ratios of AAPL and MSFT"

        chain = self.builder.build(query)

        # Steps should be in logical order:
        # 1. Calculate AAPL
        # 2. Calculate MSFT
        # 3. Compare results
        # Calculate steps should come before compare
        calc_indices = [i for i, s in enumerate(chain.steps) if s.action == StepAction.CALCULATE]
        compare_indices = [i for i, s in enumerate(chain.steps) if s.action == StepAction.COMPARE]

        if calc_indices and compare_indices:
            assert max(calc_indices) < min(compare_indices)

    def test_step_numbering_sequential(self):
        """Test that step numbers are sequential."""
        query = "Calculate Sharpe ratio for AAPL and MSFT, then compare"

        chain = self.builder.build(query)

        step_numbers = [step.step_number for step in chain.steps]
        assert step_numbers == list(range(1, len(chain.steps) + 1))


# ============================================================================
# Integration Tests
# ============================================================================

class TestReasoningChainIntegration:
    """Integration tests for reasoning chains."""

    def test_end_to_end_simple_query(self):
        """Test end-to-end: build chain, execute, get result."""
        builder = ReasoningChainBuilder()
        query = "What is the Sharpe ratio of AAPL?"

        # Build chain
        chain = builder.build(query)
        assert chain is not None

        # Execute chain
        result = chain.execute()
        assert result.success is True
        assert result.final_output is not None
        assert result.overall_confidence > 0

    def test_end_to_end_comparison_query(self):
        """Test end-to-end comparison query."""
        builder = ReasoningChainBuilder()
        query = "Compare Sharpe ratios of AAPL and MSFT"

        chain = builder.build(query)
        result = chain.execute()

        assert result.success is True
        assert len(result.steps) >= 3
        assert result.explanation is not None

    def test_chain_result_structure(self):
        """Test that ChainResult has correct structure."""
        builder = ReasoningChainBuilder()
        query = "Calculate P/E ratio for AAPL"

        chain = builder.build(query)
        result = chain.execute()

        # Verify result structure
        assert hasattr(result, 'success')
        assert hasattr(result, 'steps')
        assert hasattr(result, 'final_output')
        assert hasattr(result, 'overall_confidence')
        assert hasattr(result, 'explanation')
        assert hasattr(result, 'error')
