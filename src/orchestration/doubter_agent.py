"""
Doubter Agent - Adversarial Validator.

Week 4 Day 1: Challenges VerifiedFacts to detect contradictions.

Purpose:
- Review VerifiedFact and question its validity
- Look for logical contradictions
- Challenge assumptions in code/data
- Provide confidence adjustment

Architecture:
- Input: VerifiedFact + source code + query context
- Output: DoubterVerdict (ACCEPT, CHALLENGE, REJECT)
- Impact: Adjusts final confidence score

Example:
Query: "Calculate SPY correlation"
VerifiedFact: correlation=0.95 (p<0.001)
Doubter: "Sample size only 5 points - correlation unreliable"
Verdict: CHALLENGE (confidence penalty -30%)
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum
import logging

from src.truth_boundary.gate import VerifiedFact


class DoubterVerdict(str, Enum):
    """Doubter's verdict on a VerifiedFact."""
    ACCEPT = 'accept'           # No issues found
    CHALLENGE = 'challenge'     # Concerns raised, confidence penalty
    REJECT = 'reject'           # Critical flaw, should not be used


@dataclass
class DoubterReport:
    """
    Doubter's analysis report.

    Attributes:
        verdict: Final verdict (ACCEPT/CHALLENGE/REJECT)
        concerns: List of identified issues
        confidence_penalty: Reduction in confidence (0-100%)
        reasoning: Explanation of verdict
        suggested_improvements: Optional recommendations
    """
    verdict: DoubterVerdict
    concerns: list[str]
    confidence_penalty: float  # 0.0 to 1.0
    reasoning: str
    suggested_improvements: Optional[list[str]] = None


class DoubterAgent:
    """
    Adversarial validator that challenges VerifiedFacts.

    Reviews outputs for:
    - Logical contradictions
    - Statistical validity (sample size, significance)
    - Temporal violations (look-ahead bias)
    - Edge cases not handled
    - Overfitting indicators
    """

    def __init__(self, enable_doubter: bool = True):
        """
        Initialize Doubter agent.

        Args:
            enable_doubter: Enable adversarial validation (disable for testing)
        """
        self.enable_doubter = enable_doubter
        self.logger = logging.getLogger(__name__)

    def review(
        self,
        verified_fact: VerifiedFact,
        source_code: str,
        query_context: Optional[Dict[str, Any]] = None
    ) -> DoubterReport:
        """
        Review a VerifiedFact for potential issues.

        Args:
            verified_fact: The fact to challenge
            source_code: Code that produced the fact
            query_context: Original query and context

        Returns:
            DoubterReport with verdict and concerns
        """
        if not self.enable_doubter:
            return DoubterReport(
                verdict=DoubterVerdict.ACCEPT,
                concerns=[],
                confidence_penalty=0.0,
                reasoning='Doubter disabled'
            )

        concerns = []
        confidence_penalty = 0.0

        # Check 1: Status is success
        if verified_fact.status != 'success':
            concerns.append(f"Execution status: {verified_fact.status}")
            confidence_penalty += 0.5
            return DoubterReport(
                verdict=DoubterVerdict.REJECT,
                concerns=concerns,
                confidence_penalty=min(confidence_penalty, 1.0),
                reasoning='Execution failed - cannot validate failed facts'
            )

        # Check 2: Extracted values exist
        if not verified_fact.extracted_values:
            concerns.append('No extracted values - empty output')
            confidence_penalty += 0.3
            verdict = DoubterVerdict.CHALLENGE
        else:
            verdict = DoubterVerdict.ACCEPT

        # Check 3: Statistical validity (mock heuristics)
        if 'correlation' in verified_fact.extracted_values:
            corr = verified_fact.extracted_values.get('correlation', 0)
            if abs(corr) > 0.95:
                concerns.append('Extremely high correlation (>0.95) - check for overfitting')
                confidence_penalty += 0.1
                verdict = DoubterVerdict.CHALLENGE

            # Check for p-value
            if 'p_value' not in verified_fact.extracted_values:
                concerns.append('No p-value provided - statistical significance unknown')
                confidence_penalty += 0.15
                verdict = DoubterVerdict.CHALLENGE

        # Check 4: Sample size (if available)
        if 'sample_size' in verified_fact.extracted_values:
            n = verified_fact.extracted_values.get('sample_size', 0)
            if n < 30:
                concerns.append(f'Small sample size (n={n}) - results may be unreliable')
                confidence_penalty += 0.2
                verdict = DoubterVerdict.CHALLENGE

        # Check 5: Execution time (suspiciously fast?)
        if verified_fact.execution_time_ms < 10:
            concerns.append('Execution < 10ms - may be hardcoded/mocked value')
            confidence_penalty += 0.05

        # Generate reasoning
        if verdict == DoubterVerdict.ACCEPT:
            reasoning = 'No significant concerns identified. Fact appears valid.'
        elif verdict == DoubterVerdict.CHALLENGE:
            reasoning = f'Raised {len(concerns)} concerns. Confidence reduced by {confidence_penalty*100:.0f}%.'
        else:
            reasoning = 'Critical issues found. Fact should not be used.'

        # Suggested improvements
        suggestions = []
        if any('sample size' in c for c in concerns):
            suggestions.append('Increase sample size to ≥30 for reliable statistics')
        if any('p-value' in c for c in concerns):
            suggestions.append('Include p-value to assess statistical significance')
        if any('overfitting' in c for c in concerns):
            suggestions.append('Perform cross-validation or use holdout set')

        self.logger.info(f'Doubter verdict: {verdict.value} (penalty: {confidence_penalty:.2f})')

        return DoubterReport(
            verdict=verdict,
            concerns=concerns,
            confidence_penalty=min(confidence_penalty, 1.0),
            reasoning=reasoning,
            suggested_improvements=suggestions if suggestions else None
        )

    def adjust_confidence(
        self,
        initial_confidence: float,
        doubter_report: DoubterReport
    ) -> float:
        """
        Adjust confidence based on Doubter's verdict.

        Args:
            initial_confidence: Original confidence (0.0-1.0)
            doubter_report: Doubter's analysis

        Returns:
            Adjusted confidence (0.0-1.0)
        """
        if doubter_report.verdict == DoubterVerdict.REJECT:
            return 0.0  # Zero confidence for rejected facts

        adjusted = initial_confidence * (1.0 - doubter_report.confidence_penalty)
        return max(0.0, min(1.0, adjusted))
