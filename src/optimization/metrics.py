"""
Quality metrics for PLAN Node optimization.

Week 5 Day 1: DSPy evaluation metrics.

Metrics:
1. ExecutabilityMetric - Can the code execute without errors?
2. CodeQualityMetric - Does the code follow best practices?
3. TemporalValidityMetric - No look-ahead bias?
"""

from dataclasses import dataclass
from typing import Optional
import ast
import re

from ..orchestration.schemas.plan_output import AnalysisPlan
from ..temporal.integrity_checker import TemporalIntegrityChecker


@dataclass
class MetricResult:
    """Result of a metric evaluation."""
    score: float  # 0.0 to 1.0
    passed: bool
    reasoning: str
    details: Optional[dict] = None


class ExecutabilityMetric:
    """
    Metric: Can the generated code execute?

    Checks:
    - Valid Python syntax (AST parse)
    - No obviously broken code (undefined variables in simple cases)
    - Imports are standard library or approved packages
    """

    def __init__(self):
        self.approved_packages = [
            'yfinance', 'pandas', 'numpy', 'json', 'datetime',
            'math', 'statistics', 'typing'
        ]

    def evaluate(self, plan: AnalysisPlan) -> MetricResult:
        """
        Evaluate if plan code is executable.

        Args:
            plan: AnalysisPlan to evaluate

        Returns:
            MetricResult with executability score
        """
        score = 1.0
        issues = []

        for block in plan.code_blocks:
            # Check 1: Valid Python syntax
            try:
                ast.parse(block.code)
            except SyntaxError as e:
                score -= 0.3
                issues.append(f"Step {block.step_id}: Syntax error - {str(e)}")

            # Check 2: Imports are approved
            imports = self._extract_imports(block.code)
            for imp in imports:
                if imp not in self.approved_packages:
                    score -= 0.1
                    issues.append(f"Step {block.step_id}: Unapproved import '{imp}'")

            # Check 3: No obvious undefined references (basic heuristic)
            if 'undefined_var' in block.code or 'TODO' in block.code:
                score -= 0.2
                issues.append(f"Step {block.step_id}: Undefined or placeholder code")

        score = max(0.0, score)
        passed = score >= 0.7  # 70% threshold

        reasoning = f"Executability score: {score:.2f}. "
        if issues:
            reasoning += f"Issues: {', '.join(issues[:3])}"
        else:
            reasoning += "No executability issues found."

        return MetricResult(
            score=score,
            passed=passed,
            reasoning=reasoning,
            details={'issues': issues}
        )

    def _extract_imports(self, code: str) -> list[str]:
        """Extract import statements from code."""
        imports = []
        for line in code.split('\n'):
            line = line.strip()
            if line.startswith('import '):
                # Extract: import foo or import foo as bar
                match = re.match(r'import\s+(\w+)', line)
                if match:
                    imports.append(match.group(1))
            elif line.startswith('from '):
                # Extract: from foo import bar
                match = re.match(r'from\s+(\w+)', line)
                if match:
                    imports.append(match.group(1))
        return imports


class CodeQualityMetric:
    """
    Metric: Does code follow best practices?

    Checks:
    - No raw numbers (LLM generates code, not numbers)
    - Proper variable naming
    - Has print/output statements
    - No commented-out code
    """

    def evaluate(self, plan: AnalysisPlan) -> MetricResult:
        """
        Evaluate code quality.

        Args:
            plan: AnalysisPlan to evaluate

        Returns:
            MetricResult with quality score
        """
        score = 1.0
        issues = []

        for block in plan.code_blocks:
            # Check 1: No raw numerical assignments (Truth Boundary violation)
            if self._has_raw_numbers(block.code):
                score -= 0.4
                issues.append(
                    f"Step {block.step_id}: Contains raw number assignments "
                    "(violates Truth Boundary - LLM should generate code, not numbers)"
                )

            # Check 2: Has output statement (print, return, etc.)
            if not self._has_output(block.code):
                score -= 0.2
                issues.append(f"Step {block.step_id}: No output statement (print/return)")

            # Check 3: No commented-out code (indicates incomplete work)
            if '# ' in block.code and len([l for l in block.code.split('\n') if l.strip().startswith('#')]) > 2:
                score -= 0.1
                issues.append(f"Step {block.step_id}: Excessive commented code")

        score = max(0.0, score)
        passed = score >= 0.6  # 60% threshold for quality

        reasoning = f"Code quality score: {score:.2f}. "
        if issues:
            reasoning += f"Issues: {', '.join(issues[:3])}"
        else:
            reasoning += "Code follows best practices."

        return MetricResult(
            score=score,
            passed=passed,
            reasoning=reasoning,
            details={'issues': issues}
        )

    def _has_raw_numbers(self, code: str) -> bool:
        """Check if code has raw numerical assignments."""
        # Pattern: variable = 123.45 (not from calculation)
        pattern = r'^\s*\w+\s*=\s*-?\d+\.?\d*\s*$'
        for line in code.split('\n'):
            if re.match(pattern, line.strip()):
                return True
        return False

    def _has_output(self, code: str) -> bool:
        """Check if code has output statement."""
        return any(keyword in code for keyword in ['print(', 'return ', 'json.dumps('])


class TemporalValidityMetric:
    """
    Metric: No temporal violations (look-ahead bias)?

    Uses TemporalIntegrityChecker to validate.
    """

    def __init__(self):
        self.tim = TemporalIntegrityChecker(enable_checks=True)

    def evaluate(self, plan: AnalysisPlan, query_date: Optional[str] = None) -> MetricResult:
        """
        Evaluate temporal validity.

        Args:
            plan: AnalysisPlan to evaluate
            query_date: Optional query date for temporal validation

        Returns:
            MetricResult with temporal validity score
        """
        if not query_date:
            # No query_date provided - skip temporal checks
            return MetricResult(
                score=1.0,
                passed=True,
                reasoning="No query_date provided - temporal checks skipped"
            )

        # Parse query_date
        from datetime import datetime
        try:
            qd = datetime.fromisoformat(query_date)
        except ValueError:
            return MetricResult(
                score=0.5,
                passed=False,
                reasoning=f"Invalid query_date format: {query_date}"
            )

        score = 1.0
        all_violations = []

        for block in plan.code_blocks:
            tim_result = self.tim.check_code(block.code, query_date=qd)

            if tim_result.has_violations:
                critical_violations = tim_result.get_critical_violations()
                if critical_violations:
                    score -= 0.5  # Critical violation = major penalty
                    all_violations.extend(critical_violations)
                else:
                    score -= 0.1  # Warning = minor penalty
                    all_violations.extend(tim_result.violations)

        score = max(0.0, score)
        passed = score >= 0.8  # 80% threshold for temporal

        reasoning = f"Temporal validity score: {score:.2f}. "
        if all_violations:
            reasoning += f"Found {len(all_violations)} violation(s): "
            reasoning += ', '.join(v.description for v in all_violations[:2])
        else:
            reasoning += "No temporal violations detected."

        return MetricResult(
            score=score,
            passed=passed,
            reasoning=reasoning,
            details={'violations': [v.description for v in all_violations]}
        )


class CompositeMetric:
    """
    Combines multiple metrics into a single score.

    Default weights:
    - Executability: 50%
    - Code Quality: 30%
    - Temporal Validity: 20%
    """

    def __init__(
        self,
        weights: Optional[dict[str, float]] = None
    ):
        self.executability_metric = ExecutabilityMetric()
        self.quality_metric = CodeQualityMetric()
        self.temporal_metric = TemporalValidityMetric()

        self.weights = weights or {
            'executability': 0.5,
            'quality': 0.3,
            'temporal': 0.2
        }

    def evaluate(
        self,
        plan: AnalysisPlan,
        query_date: Optional[str] = None
    ) -> MetricResult:
        """
        Evaluate plan using all metrics.

        Args:
            plan: AnalysisPlan to evaluate
            query_date: Optional query date for temporal checks

        Returns:
            Composite MetricResult
        """
        exec_result = self.executability_metric.evaluate(plan)
        quality_result = self.quality_metric.evaluate(plan)
        temporal_result = self.temporal_metric.evaluate(plan, query_date)

        # Weighted average
        composite_score = (
            exec_result.score * self.weights['executability'] +
            quality_result.score * self.weights['quality'] +
            temporal_result.score * self.weights['temporal']
        )

        # All must pass for composite to pass
        all_passed = (
            exec_result.passed and
            quality_result.passed and
            temporal_result.passed
        )

        reasoning = (
            f"Composite score: {composite_score:.2f}. "
            f"Executability: {exec_result.score:.2f}, "
            f"Quality: {quality_result.score:.2f}, "
            f"Temporal: {temporal_result.score:.2f}"
        )

        return MetricResult(
            score=composite_score,
            passed=all_passed,
            reasoning=reasoning,
            details={
                'executability': exec_result.score,
                'quality': quality_result.score,
                'temporal': temporal_result.score
            }
        )
