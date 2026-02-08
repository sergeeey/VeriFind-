"""
Temporal Integrity Checker - Prevents look-ahead bias in backtesting.

Week 4 Day 3: Core TIM implementation.

Architecture:
1. Parse Python code AST for temporal violations
2. Detect patterns: .shift(-N), future dates, suspicious iloc
3. Generate violation reports with severity levels
4. Integration points: VEE (pre-execution), Gate (post-validation)

Example violations:
- df['future'] = df['Close'].shift(-5)  # Look-ahead bias
- yf.download('SPY', end='2025-12-31')  # Future date when query is 2024-01-15
- df.iloc[-1] without date filtering    # Might access future data

Valid patterns:
- df['lagged'] = df['Close'].shift(5)   # Lagged features OK
- df['ma'] = df['Close'].rolling(20).mean()  # Backward rolling OK
"""

import ast
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from datetime import datetime, UTC
import logging


class ViolationType(str, Enum):
    """Types of temporal violations."""
    LOOK_AHEAD_SHIFT = 'look_ahead_shift'        # .shift(-N)
    FUTURE_DATE_ACCESS = 'future_date_access'    # Date > query_date
    SUSPICIOUS_ILOC = 'suspicious_iloc'          # df.iloc[-1] without filter
    CENTERED_ROLLING = 'centered_rolling'        # rolling(center=True)
    UNKNOWN = 'unknown'


@dataclass
class TemporalViolation:
    """Single temporal violation detected in code."""

    violation_type: ViolationType
    line_number: Optional[int]
    description: str
    severity: str  # 'warning' or 'critical'
    code_snippet: Optional[str] = None

    def __str__(self):
        return f"[{self.severity.upper()}] Line {self.line_number}: {self.description}"


@dataclass
class TemporalCheckResult:
    """Result of temporal integrity check."""

    has_violations: bool
    violations: List[TemporalViolation]
    report: str
    query_date: datetime

    def get_critical_violations(self) -> List[TemporalViolation]:
        """Get only critical violations."""
        return [v for v in self.violations if v.severity == 'critical']

    def get_warnings(self) -> List[TemporalViolation]:
        """Get only warnings."""
        return [v for v in self.violations if v.severity == 'warning']


class TemporalIntegrityChecker:
    """
    Temporal Integrity Checker (TIM).

    Validates code for temporal violations that cause look-ahead bias.

    Usage:
        tim = TemporalIntegrityChecker(enable_checks=True)
        result = tim.check_code(code, query_date=datetime(2024, 1, 15))

        if result.has_violations:
            for violation in result.violations:
                print(violation)
    """

    def __init__(self, enable_checks: bool = True):
        """
        Initialize TIM.

        Args:
            enable_checks: Enable temporal validation (disable for testing)
        """
        self.enable_checks = enable_checks
        self.logger = logging.getLogger(__name__)

    def check_code(
        self,
        code: str,
        query_date: datetime,
        context: Optional[dict] = None
    ) -> TemporalCheckResult:
        """
        Check code for temporal violations.

        Args:
            code: Python code to validate
            query_date: Query timestamp (code should not use data after this)
            context: Optional context (tickers, date ranges, etc.)

        Returns:
            TemporalCheckResult with violations and report
        """
        if not self.enable_checks:
            return TemporalCheckResult(
                has_violations=False,
                violations=[],
                report="Temporal checks disabled",
                query_date=query_date
            )

        violations = []

        # Check 1: Look-ahead shift patterns
        violations.extend(self._check_shift_patterns(code))

        # Check 2: Future date access
        violations.extend(self._check_date_ranges(code, query_date))

        # Check 3: Suspicious iloc usage
        violations.extend(self._check_iloc_patterns(code))

        # Check 4: Centered rolling windows
        violations.extend(self._check_rolling_patterns(code))

        # Generate report
        report = self._generate_report(violations, query_date)

        return TemporalCheckResult(
            has_violations=len(violations) > 0,
            violations=violations,
            report=report,
            query_date=query_date
        )

    def _check_shift_patterns(self, code: str) -> List[TemporalViolation]:
        """
        Detect .shift(-N) patterns (look-ahead bias).

        Pattern: df['col'].shift(-5)  # VIOLATION
        Valid:   df['col'].shift(5)   # OK (lagged)
        """
        violations = []

        # Regex: .shift( -N ) or .shift(-N)
        shift_pattern = re.compile(r'\.shift\s*\(\s*-\s*(\d+)\s*\)')

        for line_num, line in enumerate(code.split('\n'), start=1):
            matches = shift_pattern.findall(line)
            for shift_value in matches:
                violations.append(TemporalViolation(
                    violation_type=ViolationType.LOOK_AHEAD_SHIFT,
                    line_number=line_num,
                    description=f"Look-ahead bias: .shift(-{shift_value}) accesses future data",
                    severity='critical',
                    code_snippet=line.strip()
                ))

        return violations

    def _check_date_ranges(
        self,
        code: str,
        query_date: datetime
    ) -> List[TemporalViolation]:
        """
        Detect date ranges exceeding query_date.

        Pattern: yf.download('SPY', end='2025-12-31')  # VIOLATION if query_date < 2025-12-31
        """
        violations = []

        # Regex: end='YYYY-MM-DD' or end="YYYY-MM-DD"
        date_pattern = re.compile(r"end\s*=\s*['\"](\d{4}-\d{2}-\d{2})['\"]")

        for line_num, line in enumerate(code.split('\n'), start=1):
            matches = date_pattern.findall(line)
            for date_str in matches:
                try:
                    end_date = datetime.fromisoformat(date_str)

                    # Compare dates (ignore timezone for simplicity)
                    if end_date.replace(tzinfo=None) > query_date.replace(tzinfo=None):
                        violations.append(TemporalViolation(
                            violation_type=ViolationType.FUTURE_DATE_ACCESS,
                            line_number=line_num,
                            description=f"Future date access: end='{date_str}' is after query_date ({query_date.date()})",
                            severity='critical',
                            code_snippet=line.strip()
                        ))
                except ValueError:
                    # Invalid date format, skip
                    pass

        return violations

    def _check_iloc_patterns(self, code: str) -> List[TemporalViolation]:
        """
        Detect suspicious df.iloc[-1] usage.

        Pattern: df.iloc[-1]  # WARNING: Might be future data
        Safe:    df[df.index <= date].iloc[-1]  # OK: Filtered first
        """
        violations = []

        # Regex: .iloc[-N] or .iloc[- N]
        iloc_pattern = re.compile(r'\.iloc\s*\[\s*-\s*\d+\s*\]')

        # Heuristic: Check if date filtering appears before iloc in code
        has_date_filter = bool(re.search(r'df\[.*<=.*\]|df\.loc\[.*<=.*\]', code))

        for line_num, line in enumerate(code.split('\n'), start=1):
            if iloc_pattern.search(line):
                # If no date filtering detected, flag as warning
                if not has_date_filter:
                    violations.append(TemporalViolation(
                        violation_type=ViolationType.SUSPICIOUS_ILOC,
                        line_number=line_num,
                        description="Suspicious iloc[-N]: May access future data if DataFrame not filtered by date",
                        severity='warning',  # Warning, not critical (might be OK)
                        code_snippet=line.strip()
                    ))

        return violations

    def _check_rolling_patterns(self, code: str) -> List[TemporalViolation]:
        """
        Detect centered rolling windows.

        Pattern: .rolling(window=10, center=True)  # VIOLATION: Uses future data
        Valid:   .rolling(window=10)               # OK: Backward only
        """
        violations = []

        # Regex: .rolling(..., center=True, ...)
        rolling_pattern = re.compile(r'\.rolling\([^)]*center\s*=\s*True[^)]*\)')

        for line_num, line in enumerate(code.split('\n'), start=1):
            if rolling_pattern.search(line):
                violations.append(TemporalViolation(
                    violation_type=ViolationType.CENTERED_ROLLING,
                    line_number=line_num,
                    description="Centered rolling window uses future data (center=True)",
                    severity='critical',
                    code_snippet=line.strip()
                ))

        return violations

    def _generate_report(
        self,
        violations: List[TemporalViolation],
        query_date: datetime
    ) -> str:
        """Generate detailed temporal integrity report."""
        if not violations:
            return f"✅ No temporal violations detected (query_date: {query_date.date()})"

        critical = [v for v in violations if v.severity == 'critical']
        warnings = [v for v in violations if v.severity == 'warning']

        report = f"""❌ Temporal Integrity Violations Detected
Query Date: {query_date.date()}

CRITICAL ({len(critical)}):
"""
        for v in critical:
            report += f"  - Line {v.line_number}: {v.description}\n"
            if v.code_snippet:
                report += f"    Code: {v.code_snippet}\n"

        if warnings:
            report += f"\nWARNINGS ({len(warnings)}):\n"
            for v in warnings:
                report += f"  - Line {v.line_number}: {v.description}\n"

        report += f"\nRecommendations:\n"
        if any(v.violation_type == ViolationType.LOOK_AHEAD_SHIFT for v in violations):
            report += "  • Use .shift(+N) for lagged features (not .shift(-N))\n"
        if any(v.violation_type == ViolationType.FUTURE_DATE_ACCESS for v in violations):
            report += f"  • Ensure date ranges end before {query_date.date()}\n"
        if any(v.violation_type == ViolationType.SUSPICIOUS_ILOC for v in violations):
            report += "  • Filter DataFrames by date before using .iloc[-N]\n"

        return report
