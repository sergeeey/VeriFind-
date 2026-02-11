"""
Domain Constraints Validator for APE 2026.

Ensures queries are financial in nature before processing.
Rejects non-financial queries to prevent wasting resources on out-of-scope requests.

Week 9 Day 3: Production Readiness - Domain Validation
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class DomainCategory(str, Enum):
    """Domain category classification."""
    FINANCIAL = "financial"
    NON_FINANCIAL = "non_financial"
    AMBIGUOUS = "ambiguous"


@dataclass
class DomainValidationResult:
    """Result of domain validation."""
    is_valid: bool
    domain_category: DomainCategory
    confidence_score: float  # 0.0 to 1.0
    detected_language: str = "unknown"  # ru, en, unknown
    confidence_penalty: float = 0.0  # Penalty for ambiguous cases
    rejection_reason: Optional[str] = None
    detected_entities: List[Dict[str, str]] = field(default_factory=list)


class DomainConstraintsValidator:
    """
    Validates that queries are within the financial domain.

    Design:
    - Keyword-based detection (fast, deterministic)
    - Pattern matching for financial entities (tickers, metrics)
    - Multi-signal scoring for edge cases
    - Clear rejection messages with guidance
    """

    # Financial keywords (strong indicators)
    FINANCIAL_KEYWORDS = {
        # Markets & Instruments
        'stock', 'stocks', 'bond', 'bonds', 'etf', 'index', 'indices',
        'portfolio', 'asset', 'assets', 'security', 'securities',
        'share', 'shares', 'equity', 'equities', 'option', 'options',
        'future', 'futures', 'derivative', 'derivatives',

        # Metrics & Analysis
        'sharpe', 'beta', 'alpha', 'volatility', 'correlation',
        'return', 'returns', 'yield', 'dividend', 'price',
        'ratio', 'valuation', 'performance', 'risk',
        'drawdown', 'var', 'cvar', 'sortino', 'treynor',

        # Actions & Operations
        'trade', 'trading', 'buy', 'sell', 'invest', 'investment',
        'analyze', 'analysis', 'calculate', 'compute',
        'portfolio', 'allocation', 'hedge', 'hedge',

        # Sectors & Industries
        'technology', 'tech', 'sector', 'industry',

        # Common Companies (case-insensitive)
        'apple', 'microsoft', 'google', 'amazon', 'tesla',
        'meta', 'netflix', 'nvidia', 'intel', 'amd',

        # Market Terms
        'market', 'markets', 'exchange', 'nasdaq', 'nyse',
        'dow', 's&p', 'russell', 'msci',
        'bull', 'bear', 'rally', 'correction', 'crash',

        # Financial Entities
        'ticker', 'symbol', 'quote', 'ohlc', 'candlestick',
        'earnings', 'revenue', 'profit', 'loss', 'eps',
        'pe', 'pb', 'roe', 'roa', 'margin',

        # Time & Data
        'historical', 'backtest', 'forecast', 'trend',
        'moving average', 'ma', 'ema', 'rsi', 'macd'
    }

    # Non-financial keywords (rejection signals)
    NON_FINANCIAL_KEYWORDS = {
        # Sports
        'football', 'basketball', 'baseball', 'soccer', 'hockey',
        'game', 'match', 'team', 'player', 'score', 'championship',
        'super bowl', 'world cup', 'olympics',

        # Politics
        'election', 'vote', 'president', 'senator', 'congress',
        'government', 'policy', 'law', 'regulation', 'bill',
        'democrat', 'republican', 'party', 'campaign',

        # Weather
        'weather', 'temperature', 'rain', 'snow', 'storm',
        'forecast', 'climate', 'sunny', 'cloudy', 'hurricane',

        # Entertainment
        'movie', 'film', 'actor', 'actress', 'director',
        'music', 'song', 'album', 'concert', 'band',
        'tv', 'show', 'series', 'episode', 'netflix',

        # General
        'recipe', 'food', 'restaurant', 'travel', 'hotel',
        'health', 'doctor', 'medicine', 'disease', 'treatment'
    }

    # Financial metrics (for entity detection)
    FINANCIAL_METRICS = {
        'sharpe ratio', 'beta', 'alpha', 'volatility', 'correlation',
        'return', 'yield', 'drawdown', 'var', 'cvar',
        'sortino ratio', 'treynor ratio', 'information ratio',
        'calmar ratio', 'omega ratio', 'kurtosis', 'skewness'
    }

    def __init__(self, threshold: float = 0.4, penalty_factor: float = 0.2):
        """
        Initialize domain validator.

        Args:
            threshold: Minimum confidence score to accept query (default 0.4)
            penalty_factor: Confidence penalty for ambiguous cases (default 0.2)
        """
        self.threshold = threshold
        self.penalty_factor = penalty_factor

    def validate(self, query: str) -> DomainValidationResult:
        """
        Validate that query is within financial domain.

        Args:
            query: User query text

        Returns:
            DomainValidationResult with validation outcome
        """
        detected_language = self._detect_language(query)

        # Check for empty query
        if not query or not query.strip():
            return DomainValidationResult(
                is_valid=False,
                domain_category=DomainCategory.NON_FINANCIAL,
                confidence_score=0.0,
                detected_language=detected_language,
                rejection_reason="Query is empty. Please provide a financial analysis query."
            )

        query_lower = query.lower()

        # Detect financial entities
        detected_entities = self._detect_entities(query)

        # Calculate domain scores
        financial_score = self._calculate_financial_score(query_lower, detected_entities)
        non_financial_score = self._calculate_non_financial_score(query_lower)

        # Determine category
        # If both scores are high (mixed query), prioritize financial if it's strong enough
        if non_financial_score > 0.5 and financial_score < 0.4:
            # Strong non-financial signals without financial context
            return DomainValidationResult(
                is_valid=False,
                domain_category=DomainCategory.NON_FINANCIAL,
                confidence_score=1.0 - non_financial_score,
                detected_language=detected_language,
                rejection_reason=self._generate_rejection_message(query_lower),
                detected_entities=detected_entities
            )

        elif financial_score >= 0.6:
            # Strong financial signals
            return DomainValidationResult(
                is_valid=True,
                domain_category=DomainCategory.FINANCIAL,
                confidence_score=financial_score,
                detected_language=detected_language,
                confidence_penalty=0.0,
                detected_entities=detected_entities
            )

        elif financial_score >= self.threshold:
            # Moderate financial signals - accept with penalty
            penalty = self.penalty_factor * (1.0 - financial_score)
            adjusted_score = financial_score - penalty

            return DomainValidationResult(
                is_valid=True,
                domain_category=DomainCategory.AMBIGUOUS,
                confidence_score=adjusted_score,
                detected_language=detected_language,
                confidence_penalty=penalty,
                detected_entities=detected_entities
            )

        else:
            # Weak financial signals - reject
            return DomainValidationResult(
                is_valid=False,
                domain_category=DomainCategory.NON_FINANCIAL,
                confidence_score=financial_score,
                detected_language=detected_language,
                rejection_reason=self._generate_rejection_message(query_lower),
                detected_entities=detected_entities
            )

    def _calculate_financial_score(self, query_lower: str, entities: List[Dict]) -> float:
        """Calculate financial relevance score."""
        score = 0.0

        # Check financial keywords
        financial_keyword_count = sum(
            1 for keyword in self.FINANCIAL_KEYWORDS
            if keyword in query_lower
        )

        # Base score from keywords (up to 0.6)
        keyword_score = min(financial_keyword_count * 0.15, 0.6)
        score += keyword_score

        # Bonus for detected entities (up to 0.5)
        if entities:
            ticker_count = sum(1 for e in entities if e['type'] == 'ticker')
            metric_count = sum(1 for e in entities if e['type'] == 'metric')

            entity_score = min((ticker_count * 0.3) + (metric_count * 0.1), 0.5)
            score += entity_score

        return min(score, 1.0)

    def _calculate_non_financial_score(self, query_lower: str) -> float:
        """Calculate non-financial relevance score."""
        non_financial_count = sum(
            1 for keyword in self.NON_FINANCIAL_KEYWORDS
            if keyword in query_lower
        )

        # Each non-financial keyword increases score
        return min(non_financial_count * 0.3, 1.0)

    def _detect_language(self, query: str) -> str:
        """Detect language using script balance (safe heuristic)."""
        if not query:
            return "unknown"

        cyrillic_count = len(re.findall(r"[А-Яа-яЁё]", query))
        latin_count = len(re.findall(r"[A-Za-z]", query))

        if cyrillic_count == 0 and latin_count == 0:
            return "unknown"
        if cyrillic_count > latin_count:
            return "ru"
        if latin_count > cyrillic_count:
            return "en"
        return "unknown"

    def _detect_entities(self, query: str) -> List[Dict[str, str]]:
        """Detect financial entities in query."""
        entities = []

        # Detect ticker symbols (3-5 uppercase letters)
        ticker_pattern = r'\b[A-Z]{2,5}\b'
        tickers = re.findall(ticker_pattern, query)

        for ticker in tickers:
            # Filter out common English words that might match pattern
            if ticker not in {'THE', 'AND', 'FOR', 'ARE', 'FROM', 'TO', 'IS', 'AS'}:
                entities.append({
                    'type': 'ticker',
                    'value': ticker
                })

        # Detect financial metrics
        query_lower = query.lower()
        for metric in self.FINANCIAL_METRICS:
            if metric in query_lower:
                entities.append({
                    'type': 'metric',
                    'value': metric
                })

        return entities

    def _generate_rejection_message(self, query_lower: str) -> str:
        """Generate helpful rejection message."""
        # Detect what non-financial topic was mentioned
        topic = None

        if any(keyword in query_lower for keyword in ['football', 'basketball', 'baseball', 'super bowl', 'game', 'match']):
            topic = "sports"
        elif any(keyword in query_lower for keyword in ['election', 'president', 'government', 'politics']):
            topic = "politics"
        elif any(keyword in query_lower for keyword in ['weather', 'temperature', 'rain', 'forecast']):
            topic = "weather"
        elif any(keyword in query_lower for keyword in ['movie', 'music', 'show', 'entertainment']):
            topic = "entertainment"

        base_message = "This query appears to be outside the financial domain."

        if topic:
            base_message += f" It seems to be about {topic}."

        base_message += (
            " This system is designed for financial analysis queries only. "
            "Please ask questions about stocks, portfolios, market metrics, or financial analysis. "
            "For example: 'Calculate the Sharpe ratio for AAPL' or "
            "'What is the correlation between SPY and QQQ?'"
        )

        return base_message
