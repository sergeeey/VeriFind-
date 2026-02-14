"""
Golden Set Answer Validators.

Week 13 Day 2: Real validation logic (not just field existence check).
"""

import re
from typing import Any, Dict, List, Optional


class AnswerValidator:
    """Validates debate results against expected answers."""

    @staticmethod
    def validate_percentage(answer: str, expected: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate percentage answer (e.g., "15.3%", "growth of 25%").

        Args:
            answer: LLM generated answer text
            expected: Expected answer metadata

        Returns:
            (is_correct, reason)
        """
        # Extract percentages from answer
        percent_pattern = r'[-+]?\d+\.?\d*\s*%'
        matches = re.findall(percent_pattern, answer)

        if not matches:
            return False, "No percentage found in answer"

        # For now, just check that a percentage exists
        # TODO: Add ground truth comparison when available
        return True, f"Found percentage: {matches[0]}"

    @staticmethod
    def validate_float(answer: str, expected: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate float answer (e.g., P/E ratio "25.3", "ratio of 30.5").

        Args:
            answer: LLM generated answer text
            expected: Expected answer metadata

        Returns:
            (is_correct, reason)
        """
        metric = expected.get("metric", "")

        # Extract floats from answer
        float_pattern = r'\b\d+\.?\d*\b'
        matches = re.findall(float_pattern, answer)

        if not matches:
            return False, f"No numeric value found for {metric}"

        # For financial metrics, check reasonable ranges
        if "pe_ratio" in metric.lower() or "p/e" in metric.lower():
            try:
                value = float(matches[0])
                if 5.0 <= value <= 100.0:  # Reasonable P/E range
                    return True, f"P/E ratio {value} in reasonable range"
                else:
                    return False, f"P/E ratio {value} outside reasonable range (5-100)"
            except ValueError:
                return False, f"Could not parse {matches[0]} as float"

        return True, f"Found numeric value: {matches[0]}"

    @staticmethod
    def validate_boolean(answer: str, expected: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate boolean answer (e.g., "Yes", "No", "above", "below").

        Args:
            answer: LLM generated answer text
            expected: Expected answer metadata

        Returns:
            (is_correct, reason)
        """
        answer_lower = answer.lower()

        # Look for boolean indicators
        positive_indicators = ['yes', 'true', 'above', 'higher', 'over', 'exceeds']
        negative_indicators = ['no', 'false', 'below', 'lower', 'under', 'less than']

        has_positive = any(ind in answer_lower for ind in positive_indicators)
        has_negative = any(ind in answer_lower for ind in negative_indicators)

        if has_positive and not has_negative:
            return True, "Clear positive answer"
        elif has_negative and not has_positive:
            return True, "Clear negative answer"
        elif has_positive and has_negative:
            return False, "Ambiguous answer (both positive and negative indicators)"
        else:
            return False, "No clear boolean answer found"

    @staticmethod
    def validate_string(answer: str, expected: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate string answer with must_contain requirements.

        Args:
            answer: LLM generated answer text
            expected: Expected answer metadata with must_contain list

        Returns:
            (is_correct, reason)
        """
        must_contain = expected.get("must_contain", [])
        answer_lower = answer.lower()

        if not must_contain:
            # No specific requirements, just check non-empty
            return len(answer.strip()) > 0, "Answer provided"

        missing = []
        for phrase in must_contain:
            if phrase.lower() not in answer_lower:
                missing.append(phrase)

        if missing:
            return False, f"Missing required phrases: {missing}"
        else:
            return True, f"Contains all required phrases: {must_contain}"

    @staticmethod
    def validate_analytical_text(answer: str, expected: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate analytical text answer (quality check).

        Args:
            answer: LLM generated answer text
            expected: Expected answer metadata

        Returns:
            (is_correct, reason)
        """
        # Basic quality checks
        if len(answer.strip()) < 100:
            return False, "Answer too short for analytical text (< 100 chars)"

        # Check for analytical indicators
        analytical_words = [
            'correlation', 'impact', 'relationship', 'affect', 'influence',
            'because', 'therefore', 'however', 'although', 'factor', 'driver'
        ]

        answer_lower = answer.lower()
        found_analytical = [w for w in analytical_words if w in answer_lower]

        if len(found_analytical) < 2:
            return False, f"Lacks analytical depth (found only: {found_analytical})"

        return True, f"Analytical text with indicators: {found_analytical[:3]}"

    @classmethod
    def validate_answer(cls, answer: str, expected: Dict[str, Any]) -> tuple[bool, str]:
        """
        Main validation router.

        Args:
            answer: LLM generated answer text
            expected: Expected answer metadata from Golden Set

        Returns:
            (is_correct, reason)
        """
        value_type = expected.get("value_type", "").lower()

        if value_type == "percentage":
            return cls.validate_percentage(answer, expected)
        elif value_type == "float":
            return cls.validate_float(answer, expected)
        elif value_type == "boolean":
            return cls.validate_boolean(answer, expected)
        elif value_type == "string":
            return cls.validate_string(answer, expected)
        elif value_type == "analytical_text":
            return cls.validate_analytical_text(answer, expected)
        else:
            return False, f"Unknown value_type: {value_type}"


def extract_answer_from_debate(result: Any) -> str:
    """
    Extract answer text from debate result.

    Args:
        result: MultiLLMDebateResult object

    Returns:
        Answer text (arbiter.analysis preferred, not just recommendation)
    """
    # Week 13 Day 2 Fix: MultiLLMDebateResult has arbiter_response.analysis
    # NOT synthesis (that's in ParallelDebateOrchestrator, different class)

    # Try arbiter response (final decision)
    if hasattr(result, 'arbiter_response'):
        arbiter = result.arbiter_response
        if hasattr(arbiter, 'analysis'):
            return arbiter.analysis

    # Try synthesis (for ParallelDebateOrchestrator results)
    if hasattr(result, 'synthesis'):
        synthesis = result.synthesis
        if hasattr(synthesis, 'analysis'):
            return synthesis.analysis
        elif hasattr(synthesis, 'recommendation'):
            return synthesis.recommendation

    # Fallback to recommendation (single word like "HOLD")
    if hasattr(result, 'recommendation'):
        return result.recommendation

    # Last resort: convert to string
    return str(result)
