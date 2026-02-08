"""
Debater Agent - Generates arguments from specific perspective.

Week 5 Day 2: Multi-perspective analysis agent.

Design:
- Takes VerifiedFact + perspective (Bull/Bear/Neutral)
- Generates arguments supporting that perspective
- Returns DebateReport with structured arguments

Role-based prompting:
- Bull: Focus on positive aspects, growth, opportunities
- Bear: Focus on risks, weaknesses, concerns
- Neutral: Balanced analysis, both pros and cons
"""

from typing import Optional, Dict, Any, List
import logging

from .schemas import (
    Perspective,
    Argument,
    ArgumentStrength,
    DebateReport,
    DebateContext
)


class DebaterAgent:
    """
    Debater agent that generates arguments from a specific perspective.

    Usage:
        debater = DebaterAgent(perspective=Perspective.BULL)
        report = debater.debate(context)
    """

    def __init__(
        self,
        perspective: Perspective,
        enable_debate: bool = True
    ):
        """
        Initialize debater agent.

        Args:
            perspective: Which perspective to argue from (Bull/Bear/Neutral)
            enable_debate: Enable debate generation (disable for testing)
        """
        self.perspective = perspective
        self.enable_debate = enable_debate
        self.logger = logging.getLogger(__name__)

        # Perspective-specific prompts
        self.role_prompts = {
            Perspective.BULL: (
                "You are a BULL analyst - optimistic perspective. "
                "Focus on: growth potential, positive trends, opportunities, "
                "strengths, upside scenarios. Be constructive but not unrealistic."
            ),
            Perspective.BEAR: (
                "You are a BEAR analyst - pessimistic perspective. "
                "Focus on: risks, weaknesses, concerns, downside scenarios, "
                "threats, overvaluation. Be critical but fair."
            ),
            Perspective.NEUTRAL: (
                "You are a NEUTRAL analyst - balanced perspective. "
                "Focus on: objective analysis, both pros and cons, "
                "realistic assessment, data-driven conclusions. "
                "Avoid extreme optimism or pessimism."
            )
        }

    def debate(
        self,
        context: DebateContext
    ) -> DebateReport:
        """
        Generate debate report from this perspective.

        Args:
            context: DebateContext with VerifiedFact data

        Returns:
            DebateReport with arguments
        """
        if not self.enable_debate:
            return self._empty_report(context.fact_id)

        # Generate arguments based on perspective
        arguments = self._generate_arguments(context)

        # Compute statistics
        strong_args = [a for a in arguments if a.strength == ArgumentStrength.STRONG]
        avg_confidence = (
            sum(a.confidence for a in arguments) / len(arguments)
            if arguments else 0.0
        )

        # Generate key points
        key_points = self._extract_key_points(arguments)

        # Generate overall stance
        overall_stance = self._generate_stance(context, arguments)

        return DebateReport(
            perspective=self.perspective,
            fact_id=context.fact_id,
            arguments=arguments,
            key_points=key_points,
            overall_stance=overall_stance,
            num_strong_arguments=len(strong_args),
            average_confidence=avg_confidence
        )

    def _generate_arguments(
        self,
        context: DebateContext
    ) -> List[Argument]:
        """
        Generate arguments based on extracted values and perspective.

        This is a rule-based implementation. For production,
        this would call an LLM with perspective-specific prompts.

        Args:
            context: DebateContext with data

        Returns:
            List of Argument objects
        """
        arguments = []
        values = context.extracted_values

        # Argument generation based on perspective
        if self.perspective == Perspective.BULL:
            arguments.extend(self._generate_bull_arguments(values, context))
        elif self.perspective == Perspective.BEAR:
            arguments.extend(self._generate_bear_arguments(values, context))
        else:  # NEUTRAL
            arguments.extend(self._generate_neutral_arguments(values, context))

        return arguments

    def _generate_bull_arguments(
        self,
        values: Dict[str, Any],
        context: DebateContext
    ) -> List[Argument]:
        """Generate optimistic arguments."""
        arguments = []

        # Check for positive correlation
        if 'correlation' in values:
            corr = values['correlation']
            if corr > 0.5:
                arguments.append(Argument(
                    perspective=Perspective.BULL,
                    claim=f"Strong positive correlation ({corr:.2f}) indicates reliable relationship",
                    evidence=[
                        f"Correlation coefficient: {corr:.2f}",
                        f"Sample size: {values.get('sample_size', 'N/A')}"
                    ],
                    strength=ArgumentStrength.STRONG if abs(corr) > 0.7 else ArgumentStrength.MODERATE,
                    confidence=min(abs(corr), 0.95)
                ))

        # Check for p-value significance
        if 'p_value' in values:
            p_val = values['p_value']
            if p_val < 0.05:
                arguments.append(Argument(
                    perspective=Perspective.BULL,
                    claim="Statistically significant result supports reliability",
                    evidence=[
                        f"p-value: {p_val:.4f} (< 0.05 threshold)",
                        "Result unlikely to be due to chance"
                    ],
                    strength=ArgumentStrength.STRONG if p_val < 0.01 else ArgumentStrength.MODERATE,
                    confidence=1.0 - p_val if p_val < 1.0 else 0.5
                ))

        # Check for large sample size
        if 'sample_size' in values:
            n = values['sample_size']
            if n >= 100:
                arguments.append(Argument(
                    perspective=Perspective.BULL,
                    claim=f"Large sample size (n={n}) provides statistical robustness",
                    evidence=[
                        f"Sample size: {n}",
                        "Reduces random noise, increases reliability"
                    ],
                    strength=ArgumentStrength.STRONG if n >= 250 else ArgumentStrength.MODERATE,
                    confidence=min(0.5 + (n / 1000), 0.95)
                ))

        # Default argument if no specific patterns
        if not arguments:
            arguments.append(Argument(
                perspective=Perspective.BULL,
                claim="Analysis completed successfully with valid results",
                evidence=["Code executed without errors", "Results extracted successfully"],
                strength=ArgumentStrength.WEAK,
                confidence=0.6
            ))

        return arguments

    def _generate_bear_arguments(
        self,
        values: Dict[str, Any],
        context: DebateContext
    ) -> List[Argument]:
        """Generate pessimistic arguments."""
        arguments = []

        # Check for suspicious high correlation
        if 'correlation' in values:
            corr = values['correlation']
            if abs(corr) > 0.95:
                arguments.append(Argument(
                    perspective=Perspective.BEAR,
                    claim=f"Extremely high correlation ({corr:.2f}) may indicate overfitting",
                    evidence=[
                        f"Correlation: {corr:.2f} (> 0.95 threshold)",
                        "May not generalize to new data"
                    ],
                    strength=ArgumentStrength.STRONG,
                    counterarguments=["Could be genuine strong relationship"],
                    confidence=0.8
                ))

        # Check for small sample size
        if 'sample_size' in values:
            n = values['sample_size']
            if n < 30:
                arguments.append(Argument(
                    perspective=Perspective.BEAR,
                    claim=f"Small sample size (n={n}) limits statistical reliability",
                    evidence=[
                        f"Sample size: {n} (< 30 minimum)",
                        "Vulnerable to outliers and noise"
                    ],
                    strength=ArgumentStrength.STRONG if n < 10 else ArgumentStrength.MODERATE,
                    confidence=max(0.9 - (n / 100), 0.5)
                ))

        # Check for missing p-value
        if 'correlation' in values and 'p_value' not in values:
            arguments.append(Argument(
                perspective=Perspective.BEAR,
                claim="Missing statistical significance test (p-value)",
                evidence=[
                    "No p-value provided",
                    "Cannot assess if result is statistically significant"
                ],
                strength=ArgumentStrength.MODERATE,
                confidence=0.7
            ))

        # Check for fast execution (suspicious)
        if context.execution_metadata:
            exec_time = context.execution_metadata.get('execution_time_ms', 1000)
            if exec_time < 10:
                arguments.append(Argument(
                    perspective=Perspective.BEAR,
                    claim=f"Suspiciously fast execution ({exec_time}ms) may indicate hardcoded values",
                    evidence=[
                        f"Execution time: {exec_time}ms",
                        "Real analysis typically takes longer"
                    ],
                    strength=ArgumentStrength.WEAK,
                    confidence=0.6
                ))

        # Default bear argument
        if not arguments:
            arguments.append(Argument(
                perspective=Perspective.BEAR,
                claim="Limited evidence provided for robust validation",
                evidence=["Need more comprehensive metrics"],
                strength=ArgumentStrength.WEAK,
                confidence=0.5
            ))

        return arguments

    def _generate_neutral_arguments(
        self,
        values: Dict[str, Any],
        context: DebateContext
    ) -> List[Argument]:
        """Generate balanced arguments."""
        arguments = []

        # Objective assessment of correlation
        if 'correlation' in values:
            corr = values['correlation']
            arguments.append(Argument(
                perspective=Perspective.NEUTRAL,
                claim=f"Correlation of {corr:.2f} indicates {'strong' if abs(corr) > 0.7 else 'moderate' if abs(corr) > 0.3 else 'weak'} relationship",
                evidence=[
                    f"Correlation coefficient: {corr:.2f}",
                    "Interpretation depends on context and use case"
                ],
                strength=ArgumentStrength.MODERATE,
                confidence=0.75
            ))

        # Sample size assessment
        if 'sample_size' in values:
            n = values['sample_size']
            quality = "good" if n >= 100 else "adequate" if n >= 30 else "limited"
            arguments.append(Argument(
                perspective=Perspective.NEUTRAL,
                claim=f"Sample size of {n} provides {quality} statistical basis",
                evidence=[
                    f"Sample size: {n}",
                    f"{'Sufficient' if n >= 30 else 'Below recommended minimum'} for robust analysis"
                ],
                strength=ArgumentStrength.MODERATE,
                confidence=min(0.5 + (n / 200), 0.9)
            ))

        # Default neutral argument
        if not arguments:
            arguments.append(Argument(
                perspective=Perspective.NEUTRAL,
                claim="Analysis provides baseline results for further investigation",
                evidence=["Results available but require context for interpretation"],
                strength=ArgumentStrength.MODERATE,
                confidence=0.7
            ))

        return arguments

    def _extract_key_points(self, arguments: List[Argument]) -> List[str]:
        """Extract top key points from arguments."""
        # Sort by strength and confidence
        sorted_args = sorted(
            arguments,
            key=lambda a: (
                {'strong': 3, 'moderate': 2, 'weak': 1}[a.strength.value],
                a.confidence
            ),
            reverse=True
        )

        # Take top 3-5 arguments as key points
        return [arg.claim for arg in sorted_args[:5]]

    def _generate_stance(
        self,
        context: DebateContext,
        arguments: List[Argument]
    ) -> str:
        """Generate overall stance based on arguments."""
        if not arguments:
            return f"From {self.perspective.value} perspective: Insufficient data for assessment."

        # Count strong arguments
        strong_count = sum(1 for a in arguments if a.strength == ArgumentStrength.STRONG)
        avg_conf = sum(a.confidence for a in arguments) / len(arguments)

        if self.perspective == Perspective.BULL:
            if strong_count >= 2:
                return (
                    f"From BULL perspective: Strong case with {strong_count} compelling arguments. "
                    f"Results appear reliable and indicate positive potential. "
                    f"Average confidence: {avg_conf:.2f}."
                )
            else:
                return (
                    f"From BULL perspective: Moderate positive case. "
                    f"Some promising aspects but would benefit from additional evidence."
                )

        elif self.perspective == Perspective.BEAR:
            if strong_count >= 2:
                return (
                    f"From BEAR perspective: Significant concerns identified with {strong_count} key issues. "
                    f"Results should be interpreted cautiously. "
                    f"Average confidence in concerns: {avg_conf:.2f}."
                )
            else:
                return (
                    f"From BEAR perspective: Some areas of concern noted. "
                    f"Risk factors exist but may be manageable."
                )

        else:  # NEUTRAL
            return (
                f"From NEUTRAL perspective: Balanced assessment with {len(arguments)} factors considered. "
                f"Results show both strengths and limitations. "
                f"Recommendation: Use with appropriate context and validation."
            )

    def _empty_report(self, fact_id: str) -> DebateReport:
        """Generate empty report when debate is disabled."""
        return DebateReport(
            perspective=self.perspective,
            fact_id=fact_id,
            arguments=[],
            key_points=["Debate disabled"],
            overall_stance="Debate generation disabled for testing",
            num_strong_arguments=0,
            average_confidence=0.0
        )
