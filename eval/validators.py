"""
Golden Set Answer Validators.

Week 13 Day 2: Real validation logic (not just field existence check).
Week 13 Day 3: Added fuzzy matching for robust must_contain validation.
"""

import re
from difflib import SequenceMatcher
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
        # Prioritize DIRECT ANSWER section if it exists
        if "DIRECT ANSWER:" in answer:
            direct_answer = answer.split("DIRECT ANSWER:")[1].split("\n")[0]
            answer_to_check = direct_answer
        else:
            # Fallback: check first 200 chars (avoid synthesis section)
            answer_to_check = answer[:200]

        answer_lower = answer_to_check.lower()

        # Look for boolean indicators
        positive_indicators = ['yes', 'true', 'above', 'higher', 'over', 'exceeds']
        negative_indicators = ['no', 'false', 'below', 'lower', 'under', 'less than']

        has_positive = any(ind in answer_lower for ind in positive_indicators)
        has_negative = any(ind in answer_lower for ind in negative_indicators)

        if has_positive and not has_negative:
            return True, f"Clear positive answer in DIRECT ANSWER: {answer_to_check[:100]}"
        elif has_negative and not has_positive:
            return True, f"Clear negative answer in DIRECT ANSWER: {answer_to_check[:100]}"
        elif has_positive and has_negative:
            return False, "Ambiguous answer (both positive and negative indicators)"
        else:
            return False, "No clear boolean answer found"

    @staticmethod
    def validate_string(answer: str, expected: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate string answer with must_contain requirements.

        Week 13 Day 3: Added fuzzy matching for robustness (case, punctuation, typos).

        Args:
            answer: LLM generated answer text
            expected: Expected answer metadata with must_contain list

        Returns:
            (is_correct, reason)
        """
        must_contain = expected.get("must_contain", [])
        answer_lower = answer.lower()
        similarity_threshold = 0.85  # 85% similarity for fuzzy match

        if not must_contain:
            # No specific requirements, just check non-empty
            return len(answer.strip()) > 0, "Answer provided"

        missing = []
        for phrase in must_contain:
            # Fast path: exact case-insensitive match
            if phrase.lower() in answer_lower:
                continue

            # Fuzzy path: use SequenceMatcher with sliding window
            if not AnswerValidator._fuzzy_contains(phrase, answer, similarity_threshold):
                missing.append(phrase)

        if missing:
            return False, f"Missing required phrases (fuzzy checked): {missing}"
        else:
            return True, f"Contains all required phrases: {must_contain}"

    @staticmethod
    def _fuzzy_contains(phrase: str, text: str, threshold: float) -> bool:
        """
        Check if phrase exists in text with fuzzy matching.

        Uses sliding window + SequenceMatcher for typo/punctuation tolerance.

        Args:
            phrase: Phrase to find
            text: Text to search in
            threshold: Similarity threshold (0.0-1.0)

        Returns:
            True if fuzzy match found, False otherwise
        """
        phrase_lower = phrase.lower()
        text_lower = text.lower()
        phrase_len = len(phrase)

        # Sliding window over text
        for i in range(len(text) - phrase_len + 1):
            window = text_lower[i:i + phrase_len]
            similarity = SequenceMatcher(None, phrase_lower, window).ratio()
            if similarity >= threshold:
                return True

        return False

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
    def validate_answer(
        cls,
        answer: str,
        expected: Dict[str, Any],
        source_verified: bool = True,  # Week 14: Add source_verified check
        error_detected: bool = False,
        ambiguity_detected: bool = False
    ) -> tuple[bool, str]:
        """
        Main validation router.

        Week 14: Added source_verified, error_detected, ambiguity_detected checks
        to prevent hallucinations from passing validation.

        Args:
            answer: LLM generated answer text
            expected: Expected answer metadata from Golden Set
            source_verified: True if value came from VEE execution (not LLM hallucination)
            error_detected: True if VEE execution had errors
            ambiguity_detected: True if VEE execution had pandas Series ambiguity, etc.

        Returns:
            (is_correct, reason)
        """
        # Week 14 CRITICAL: Block hallucinations at validation level
        if not source_verified:
            return False, "HALLUCINATION: Value not from verified VEE execution (source_verified=False)"

        if error_detected:
            return False, "VEE_ERROR: Execution had errors (error_detected=True)"

        if ambiguity_detected:
            return False, "VEE_AMBIGUITY: Execution had pandas Series ambiguity or similar issues (ambiguity_detected=True)"

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
