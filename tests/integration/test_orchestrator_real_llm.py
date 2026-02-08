"""
Integration tests for Orchestrator with Real LLM API.

Week 11 Day 2: Test integration of real LLM providers with orchestrator.

Test strategy:
- Mock mode tests: Fast, no API calls, verify integration logic
- Real API tests: @pytest.mark.real_llm, require API keys, verify end-to-end flow
"""

import pytest
import os
from typing import Dict, Any

from src.orchestration.langgraph_orchestrator import LangGraphOrchestrator, StateStatus
from src.debate.real_llm_adapter import RealLLMDebateAdapter
from src.debate.schemas import DebateContext, Perspective


# Sample code for testing
SAMPLE_CODE = """
result = {
    "metric": "sharpe_ratio",
    "ticker": "AAPL",
    "value": 1.95,
    "year": 2023,
    "supporting_data": [
        "Annual return: 44.9%",
        "Annual volatility: 17.8%"
    ]
}
"""


class TestOrchestratorMockLLM:
    """Test orchestrator with mock LLM (fast tests, no API calls)."""

    def test_orchestrator_with_real_llm_disabled(self):
        """Test orchestrator works with real LLM disabled (mock mode)."""
        orchestrator = LangGraphOrchestrator(
            use_real_llm=False,  # Use mock agents
            enable_retry=False
        )

        # Run pipeline
        state = orchestrator.run(
            query_id="test_mock_1",
            query_text="What is AAPL Sharpe ratio?",
            direct_code=SAMPLE_CODE,
            use_plan=False
        )

        # Debug: Print error if failed
        if state.status != StateStatus.COMPLETED:
            print(f"\n❌ Test failed: {state.error_message}")
            print(f"   Nodes visited: {state.nodes_visited}")
            print(f"   Status: {state.status}")

        # Verify execution
        assert state.status == StateStatus.COMPLETED, f"Pipeline failed: {state.error_message}"
        assert state.verified_fact is not None
        assert state.debate_reports is not None
        assert len(state.debate_reports) == 3  # Bull, Bear, Neutral
        assert state.synthesis is not None

        # Verify perspectives
        perspectives = [r.perspective for r in state.debate_reports]
        assert Perspective.BULL in perspectives
        assert Perspective.BEAR in perspectives
        assert Perspective.NEUTRAL in perspectives

    def test_adapter_mock_mode_integration(self):
        """Test RealLLMDebateAdapter in mock mode (no API calls)."""
        # Create adapter in test mode (no LLM calls)
        adapter = RealLLMDebateAdapter(
            provider="deepseek",
            enable_debate=False  # Mock mode
        )

        # Create sample context
        context = DebateContext(
            fact_id="test_fact",
            extracted_values={"metric": "pe_ratio", "value": 25.5},
            source_code=SAMPLE_CODE,
            query_text="What is MSFT P/E ratio?",
            execution_metadata={}
        )

        # Generate debate
        reports, synthesis = adapter.generate_debate(
            context=context,
            original_confidence=0.85
        )

        # Verify structure
        assert len(reports) == 3
        assert synthesis is not None
        assert synthesis.fact_id == "test_fact"
        assert synthesis.original_confidence == 0.85

        # Verify test mode reports
        for report in reports:
            assert "Test mode" in report.overall_stance


class TestOrchestratorRealAPI:
    """Test orchestrator with real LLM API (requires API keys, costs money)."""

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_orchestrator_with_openai(self):
        """Test full pipeline with real OpenAI API."""
        # Skip if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")

        orchestrator = LangGraphOrchestrator(
            use_real_llm=True,
            llm_provider="openai",
            enable_retry=False
        )

        # Run pipeline
        state = orchestrator.run(
            query_id="test_openai_1",
            query_text="Analyze AAPL Sharpe ratio of 1.95",
            direct_code=SAMPLE_CODE,
            use_plan=False
        )

        # Verify execution
        assert state.status == StateStatus.COMPLETED
        assert state.verified_fact is not None
        assert state.debate_reports is not None
        assert len(state.debate_reports) == 3

        # Verify real LLM generated content
        for report in state.debate_reports:
            assert len(report.key_points) > 0
            assert len(report.overall_stance) > 10  # Real analysis is longer
            assert "Test mode" not in report.overall_stance

        # Verify synthesis
        assert state.synthesis is not None
        assert len(state.synthesis.balanced_view) > 50
        assert state.synthesis.adjusted_confidence > 0

        # Verify cost tracking
        stats = orchestrator.debate_adapter.get_stats()
        assert stats['total_calls'] >= 1
        assert stats['total_cost'] > 0

        print(f"\n✅ OpenAI pipeline complete")
        print(f"   Cost: ${stats['total_cost']:.6f}")
        print(f"   Confidence: {state.verified_fact.confidence_score:.2f}")

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_orchestrator_with_gemini(self):
        """Test full pipeline with real Gemini API."""
        # Skip if no API key
        if not os.getenv("GOOGLE_API_KEY"):
            pytest.skip("GOOGLE_API_KEY not set")

        orchestrator = LangGraphOrchestrator(
            use_real_llm=True,
            llm_provider="gemini",
            enable_retry=False
        )

        # Run pipeline
        state = orchestrator.run(
            query_id="test_gemini_1",
            query_text="Analyze MSFT P/E ratio",
            direct_code=SAMPLE_CODE.replace("AAPL", "MSFT"),
            use_plan=False
        )

        # Verify execution
        assert state.status == StateStatus.COMPLETED
        assert state.verified_fact is not None
        assert len(state.debate_reports) == 3

        # Verify real content
        for report in state.debate_reports:
            assert len(report.key_points) > 0

        # Verify stats
        stats = orchestrator.debate_adapter.get_stats()
        assert stats['total_calls'] >= 1

        print(f"\n✅ Gemini pipeline complete")
        print(f"   Cost: ${stats['total_cost']:.6f} (FREE during preview)")

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_orchestrator_with_deepseek(self):
        """Test full pipeline with real DeepSeek API (cheapest)."""
        # Skip if no API key
        if not os.getenv("DEEPSEEK_API_KEY"):
            pytest.skip("DEEPSEEK_API_KEY not set")

        orchestrator = LangGraphOrchestrator(
            use_real_llm=True,
            llm_provider="deepseek",  # Cheapest option
            enable_retry=False
        )

        # Run pipeline
        state = orchestrator.run(
            query_id="test_deepseek_1",
            query_text="Analyze correlation between SPY and QQQ",
            direct_code=SAMPLE_CODE.replace("AAPL", "SPY"),
            use_plan=False
        )

        # Verify execution
        assert state.status == StateStatus.COMPLETED
        assert state.verified_fact is not None
        assert len(state.debate_reports) == 3

        # Verify stats
        stats = orchestrator.debate_adapter.get_stats()
        assert stats['total_calls'] >= 1
        assert stats['total_cost'] > 0

        print(f"\n✅ DeepSeek pipeline complete")
        print(f"   Cost: ${stats['total_cost']:.6f}")
        print(f"   Input tokens: {stats['total_input_tokens']}")
        print(f"   Output tokens: {stats['total_output_tokens']}")

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_cost_comparison_across_providers(self):
        """Compare costs across all 3 providers for same query."""
        # Skip if any key missing
        if not all([
            os.getenv("OPENAI_API_KEY"),
            os.getenv("GOOGLE_API_KEY"),
            os.getenv("DEEPSEEK_API_KEY")
        ]):
            pytest.skip("Not all API keys are set")

        results = {}

        for provider in ["openai", "gemini", "deepseek"]:
            orchestrator = LangGraphOrchestrator(
                use_real_llm=True,
                llm_provider=provider,
                enable_retry=False
            )

            state = orchestrator.run(
                query_id=f"test_cost_{provider}",
                query_text="Analyze AAPL volatility",
                direct_code=SAMPLE_CODE,
                use_plan=False
            )

            stats = orchestrator.debate_adapter.get_stats()

            results[provider] = {
                'cost': stats['total_cost'],
                'input_tokens': stats['total_input_tokens'],
                'output_tokens': stats['total_output_tokens'],
                'status': state.status.value
            }

        # Print comparison
        print(f"\n{'='*60}")
        print("COST COMPARISON (same query to all providers)")
        print(f"{'='*60}")

        for provider, data in results.items():
            print(f"\n{provider.upper()}:")
            print(f"  Cost:          ${data['cost']:.6f}")
            print(f"  Input tokens:  {data['input_tokens']}")
            print(f"  Output tokens: {data['output_tokens']}")
            print(f"  Status:        {data['status']}")

        # Verify all completed successfully
        for provider, data in results.items():
            assert data['status'] == 'completed', f"{provider} failed"

        # Find cheapest
        cheapest = min(results.items(), key=lambda x: x[1]['cost'])
        print(f"\n🏆 WINNER: {cheapest[0].upper()} (${cheapest[1]['cost']:.6f})")


class TestRealLLMAdapter:
    """Direct tests of RealLLMAdapter (without full orchestrator)."""

    def test_adapter_mock_mode(self):
        """Test adapter in mock mode (no real API calls)."""
        adapter = RealLLMDebateAdapter(
            provider="deepseek",
            enable_debate=False  # Mock mode
        )

        # Create sample context
        context = DebateContext(
            fact_id="test_fact_1",
            extracted_values={"metric": "sharpe_ratio", "value": 1.95},
            source_code=SAMPLE_CODE,
            query_text="What is Sharpe ratio?",
            execution_metadata={}
        )

        # Generate debate
        reports, synthesis = adapter.generate_debate(
            context=context,
            original_confidence=0.85
        )

        # Verify structure
        assert len(reports) == 3
        assert synthesis is not None
        assert synthesis.fact_id == "test_fact_1"
        assert synthesis.original_confidence == 0.85

    @pytest.mark.integration
    @pytest.mark.real_llm
    def test_adapter_real_api(self):
        """Test adapter with real API call."""
        # Skip if no key
        if not os.getenv("DEEPSEEK_API_KEY"):
            pytest.skip("DEEPSEEK_API_KEY not set")

        adapter = RealLLMDebateAdapter(
            provider="deepseek",
            enable_debate=True  # Real API
        )

        # Create sample context
        context = DebateContext(
            fact_id="test_fact_real",
            extracted_values={
                "metric": "sharpe_ratio",
                "ticker": "AAPL",
                "value": 1.95,
                "year": 2023
            },
            source_code=SAMPLE_CODE,
            query_text="Analyze AAPL Sharpe ratio",
            execution_metadata={"execution_time_ms": 150}
        )

        # Generate debate
        reports, synthesis = adapter.generate_debate(
            context=context,
            original_confidence=0.85
        )

        # Verify real content
        assert len(reports) == 3
        for report in reports:
            assert len(report.key_points) > 0
            assert len(report.overall_stance) > 10
            assert report.average_confidence > 0

        # Verify synthesis
        assert len(synthesis.balanced_view) > 50
        assert len(synthesis.key_risks) > 0
        assert len(synthesis.key_opportunities) > 0

        # Verify stats
        stats = adapter.get_stats()
        assert stats['total_calls'] >= 1
        assert stats['total_cost'] > 0

        print(f"\n✅ Adapter real API test passed")
        print(f"   Cost: ${stats['total_cost']:.6f}")
        print(f"   Bull confidence: {reports[0].average_confidence:.2f}")
        print(f"   Bear confidence: {reports[1].average_confidence:.2f}")
        print(f"   Neutral confidence: {reports[2].average_confidence:.2f}")
        print(f"   Adjusted confidence: {synthesis.adjusted_confidence:.2f}")
