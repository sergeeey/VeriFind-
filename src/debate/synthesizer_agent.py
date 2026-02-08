"""
Synthesizer Agent - Combines multiple perspectives into balanced synthesis.

Week 5 Day 2: Multi-perspective synthesis agent.

Design:
- Takes multiple DebateReports (from Bull, Bear, Neutral)
- Identifies areas of agreement and disagreement
- Generates balanced synthesis
- Adjusts confidence based on debate quality

Key principle: Synthesizer is MORE CONSERVATIVE than any individual perspective.
"""

from typing import List, Dict, Any
import logging

from .schemas import (
    Perspective,
    ArgumentStrength,
    DebateReport,
    Synthesis
)


class SynthesizerAgent:
    """
    Synthesizer agent that combines multiple debate perspectives.

    Usage:
        synthesizer = SynthesizerAgent()
        synthesis = synthesizer.synthesize(debate_reports, original_confidence=0.9)
    """

    def __init__(self, enable_synthesis: bool = True):
        """
        Initialize synthesizer agent.

        Args:
            enable_synthesis: Enable synthesis generation (disable for testing)
        """
        self.enable_synthesis = enable_synthesis
        self.logger = logging.getLogger(__name__)

    def synthesize(
        self,
        debate_reports: List[DebateReport],
        original_confidence: float,
        fact_id: str
    ) -> Synthesis:
        """
        Synthesize multiple debate reports into balanced view.

        Args:
            debate_reports: List of DebateReport from different perspectives
            original_confidence: Original VerifiedFact confidence (before debate)
            fact_id: VerifiedFact ID being synthesized

        Returns:
            Synthesis with balanced view and adjusted confidence
        """
        if not self.enable_synthesis:
            return self._empty_synthesis(fact_id, original_confidence)

        if not debate_reports:
            raise ValueError("Cannot synthesize without debate reports")

        # Extract perspectives
        perspectives = [r.perspective for r in debate_reports]

        # Identify agreement and disagreement
        agreement = self._find_agreement(debate_reports)
        disagreement = self._find_disagreement(debate_reports)

        # Extract risks and opportunities
        risks = self._extract_risks(debate_reports)
        opportunities = self._extract_opportunities(debate_reports)

        # Generate balanced view
        balanced_view = self._generate_balanced_view(debate_reports)

        # Generate recommendation
        recommendation = self._generate_recommendation(debate_reports, risks, opportunities)

        # Adjust confidence
        adjusted_conf, rationale = self._adjust_confidence(
            debate_reports,
            original_confidence
        )

        # Calculate debate quality
        quality_score = self._calculate_debate_quality(debate_reports)

        return Synthesis(
            fact_id=fact_id,
            perspectives_reviewed=perspectives,
            balanced_view=balanced_view,
            key_risks=risks,
            key_opportunities=opportunities,
            areas_of_agreement=agreement,
            areas_of_disagreement=disagreement,
            recommendation=recommendation,
            original_confidence=original_confidence,
            adjusted_confidence=adjusted_conf,
            confidence_rationale=rationale,
            debate_quality_score=quality_score
        )

    def _find_agreement(self, reports: List[DebateReport]) -> List[str]:
        """
        Find areas where all perspectives agree.

        Looks for common themes across Bull, Bear, Neutral arguments.
        """
        if len(reports) < 2:
            return []

        agreement_points = []

        # Look for common key points
        all_key_points = [kp.lower() for r in reports for kp in r.key_points]

        # Find overlapping themes (simple keyword matching)
        keywords = ['statistical', 'significant', 'sample', 'correlation', 'reliable']
        for keyword in keywords:
            matches = [kp for kp in all_key_points if keyword in kp]
            if len(matches) >= 2:  # At least 2 perspectives mention it
                agreement_points.append(f"Multiple perspectives acknowledge {keyword} aspects")

        # Check if all perspectives have similar average confidence
        avg_confidences = [r.average_confidence for r in reports]
        if max(avg_confidences) - min(avg_confidences) < 0.2:
            agreement_points.append(
                "All perspectives show similar confidence levels in their arguments"
            )

        return agreement_points if agreement_points else ["Limited explicit agreement found"]

    def _find_disagreement(self, reports: List[DebateReport]) -> List[str]:
        """
        Find areas of significant disagreement between perspectives.
        """
        if len(reports) < 2:
            return []

        disagreement_points = []

        # Check confidence divergence
        avg_confidences = [r.average_confidence for r in reports]
        if max(avg_confidences) - min(avg_confidences) > 0.3:
            disagreement_points.append(
                f"Significant confidence divergence: {min(avg_confidences):.2f} to {max(avg_confidences):.2f}"
            )

        # Check for strong vs weak argument counts
        strong_counts = [r.num_strong_arguments for r in reports]
        if max(strong_counts) - min(strong_counts) >= 2:
            disagreement_points.append(
                f"Different strength assessments: {min(strong_counts)} to {max(strong_counts)} strong arguments"
            )

        # Bull vs Bear stance differences
        bull_reports = [r for r in reports if r.perspective == Perspective.BULL]
        bear_reports = [r for r in reports if r.perspective == Perspective.BEAR]

        if bull_reports and bear_reports:
            bull_avg = sum(r.average_confidence for r in bull_reports) / len(bull_reports)
            bear_avg = sum(r.average_confidence for r in bear_reports) / len(bear_reports)

            if abs(bull_avg - bear_avg) > 0.2:
                disagreement_points.append(
                    f"Bull and Bear perspectives diverge significantly (Δ={abs(bull_avg - bear_avg):.2f})"
                )

        return disagreement_points if disagreement_points else ["Perspectives generally aligned"]

    def _extract_risks(self, reports: List[DebateReport]) -> List[str]:
        """Extract top risks from Bear and Neutral perspectives."""
        risks = []

        # Prioritize Bear arguments
        bear_reports = [r for r in reports if r.perspective == Perspective.BEAR]
        neutral_reports = [r for r in reports if r.perspective == Perspective.NEUTRAL]

        for report in bear_reports:
            # Get strong and moderate arguments
            strong_args = [
                a for a in report.arguments
                if a.strength in [ArgumentStrength.STRONG, ArgumentStrength.MODERATE]
            ]
            risks.extend([a.claim for a in strong_args[:3]])  # Top 3

        # Add neutral perspective risks
        for report in neutral_reports:
            # Look for arguments mentioning risks/concerns
            risk_args = [
                a for a in report.arguments
                if any(word in a.claim.lower() for word in ['risk', 'concern', 'limitation'])
            ]
            risks.extend([a.claim for a in risk_args[:2]])  # Top 2

        # Deduplicate and limit
        unique_risks = list(dict.fromkeys(risks))  # Preserve order, remove duplicates
        return unique_risks[:5]  # Top 5 risks

    def _extract_opportunities(self, reports: List[DebateReport]) -> List[str]:
        """Extract top opportunities from Bull and Neutral perspectives."""
        opportunities = []

        # Prioritize Bull arguments
        bull_reports = [r for r in reports if r.perspective == Perspective.BULL]
        neutral_reports = [r for r in reports if r.perspective == Perspective.NEUTRAL]

        for report in bull_reports:
            strong_args = [
                a for a in report.arguments
                if a.strength in [ArgumentStrength.STRONG, ArgumentStrength.MODERATE]
            ]
            opportunities.extend([a.claim for a in strong_args[:3]])  # Top 3

        # Add neutral perspective opportunities
        for report in neutral_reports:
            positive_args = [
                a for a in report.arguments
                if any(word in a.claim.lower() for word in ['strong', 'positive', 'reliable'])
            ]
            opportunities.extend([a.claim for a in positive_args[:2]])  # Top 2

        # Deduplicate and limit
        unique_opps = list(dict.fromkeys(opportunities))
        return unique_opps[:5]  # Top 5 opportunities

    def _generate_balanced_view(self, reports: List[DebateReport]) -> str:
        """Generate balanced synthesis combining all perspectives."""
        perspectives_str = ', '.join([r.perspective.value for r in reports])

        # Count total arguments and strong arguments
        total_args = sum(len(r.arguments) for r in reports)
        total_strong = sum(r.num_strong_arguments for r in reports)

        # Average confidence across all perspectives
        all_confidences = [r.average_confidence for r in reports]
        avg_conf = sum(all_confidences) / len(all_confidences)

        return (
            f"Synthesis of {len(reports)} perspectives ({perspectives_str}): "
            f"{total_args} total arguments reviewed, {total_strong} strong. "
            f"Average confidence across perspectives: {avg_conf:.2f}. "
            f"Analysis shows {'converging' if max(all_confidences) - min(all_confidences) < 0.2 else 'diverging'} views, "
            f"suggesting {'moderate' if avg_conf < 0.7 else 'high'} overall reliability with "
            f"{'significant' if max(all_confidences) - min(all_confidences) > 0.3 else 'limited'} uncertainty."
        )

    def _generate_recommendation(
        self,
        reports: List[DebateReport],
        risks: List[str],
        opportunities: List[str]
    ) -> str:
        """Generate final recommendation based on debate."""
        # Count perspectives
        has_bull = any(r.perspective == Perspective.BULL for r in reports)
        has_bear = any(r.perspective == Perspective.BEAR for r in reports)

        # Overall confidence
        avg_conf = sum(r.average_confidence for r in reports) / len(reports)

        if not has_bear or avg_conf > 0.8:
            return (
                f"Results appear reliable based on debate. "
                f"{'However, ' + risks[0] if risks else 'No major concerns identified'}. "
                f"Proceed with {'standard' if avg_conf > 0.8 else 'elevated'} caution."
            )
        elif not has_bull or avg_conf < 0.5:
            return (
                f"Significant concerns raised in debate. "
                f"{'Key risk: ' + risks[0] if risks else 'Multiple limitations noted'}. "
                f"Recommend additional validation before use."
            )
        else:
            return (
                f"Mixed signals from debate. "
                f"Balance identified risks ({len(risks)}) with opportunities ({len(opportunities)}). "
                f"Use results with appropriate context and validation."
            )

    def _adjust_confidence(
        self,
        reports: List[DebateReport],
        original_confidence: float
    ) -> tuple[float, str]:
        """
        Adjust confidence based on debate quality and consensus.

        Principle: Synthesizer is MORE CONSERVATIVE.
        - High agreement + strong arguments → increase confidence (max +10%)
        - Disagreement or weak arguments → decrease confidence (-10% to -30%)

        Args:
            reports: Debate reports
            original_confidence: Original confidence before debate

        Returns:
            (adjusted_confidence, rationale)
        """
        # Calculate debate metrics
        avg_conf = sum(r.average_confidence for r in reports) / len(reports)
        conf_range = max(r.average_confidence for r in reports) - min(r.average_confidence for r in reports)
        total_strong = sum(r.num_strong_arguments for r in reports)
        total_args = sum(len(r.arguments) for r in reports)

        # Adjustment logic
        adjustment = 0.0
        rationale_parts = []

        # Factor 1: Confidence consensus
        if conf_range < 0.15:  # High consensus
            adjustment += 0.05
            rationale_parts.append("high consensus across perspectives (+5%)")
        elif conf_range > 0.35:  # High disagreement
            adjustment -= 0.15
            rationale_parts.append("significant disagreement between perspectives (-15%)")

        # Factor 2: Strong argument ratio
        strong_ratio = total_strong / total_args if total_args > 0 else 0
        if strong_ratio > 0.5:
            adjustment += 0.05
            rationale_parts.append(f"majority strong arguments ({strong_ratio:.0%}) (+5%)")
        elif strong_ratio < 0.2:
            adjustment -= 0.10
            rationale_parts.append(f"few strong arguments ({strong_ratio:.0%}) (-10%)")

        # Factor 3: Number of perspectives
        if len(reports) >= 3:
            adjustment += 0.03
            rationale_parts.append("comprehensive multi-perspective review (+3%)")

        # Conservative bias: if debate raises concerns, reduce confidence more
        bear_reports = [r for r in reports if r.perspective == Perspective.BEAR]
        if bear_reports and bear_reports[0].num_strong_arguments >= 2:
            adjustment -= 0.10
            rationale_parts.append("strong Bear concerns identified (-10%)")

        # Apply adjustment (with bounds)
        adjusted = max(0.0, min(1.0, original_confidence + adjustment))

        # Generate rationale
        if adjustment > 0:
            rationale = f"Confidence increased by {adjustment:.1%}: {'; '.join(rationale_parts)}"
        elif adjustment < 0:
            rationale = f"Confidence decreased by {abs(adjustment):.1%}: {'; '.join(rationale_parts)}"
        else:
            rationale = "Confidence unchanged: debate provides balanced validation"

        return adjusted, rationale

    def _calculate_debate_quality(self, reports: List[DebateReport]) -> float:
        """
        Calculate quality score for debate (0-1).

        Quality factors:
        - Diversity: Multiple perspectives represented
        - Depth: Number of arguments
        - Evidence: Strong argument ratio
        """
        score = 0.0

        # Diversity (0-0.4): More perspectives = better
        unique_perspectives = len(set(r.perspective for r in reports))
        score += min(unique_perspectives / 3, 0.4)  # Max 3 perspectives

        # Depth (0-0.3): More arguments = better (diminishing returns)
        total_args = sum(len(r.arguments) for r in reports)
        score += min(total_args / 20, 0.3)  # Cap at 20 arguments

        # Evidence (0-0.3): Higher strong argument ratio = better
        total_strong = sum(r.num_strong_arguments for r in reports)
        strong_ratio = total_strong / total_args if total_args > 0 else 0
        score += strong_ratio * 0.3

        return min(score, 1.0)

    def _empty_synthesis(
        self,
        fact_id: str,
        original_confidence: float
    ) -> Synthesis:
        """Generate empty synthesis when disabled."""
        return Synthesis(
            fact_id=fact_id,
            perspectives_reviewed=[],
            balanced_view="Synthesis disabled for testing",
            key_risks=["N/A"],
            key_opportunities=["N/A"],
            areas_of_agreement=[],
            areas_of_disagreement=[],
            recommendation="Synthesis generation disabled",
            original_confidence=original_confidence,
            adjusted_confidence=original_confidence,
            confidence_rationale="Synthesis disabled",
            debate_quality_score=0.0
        )
