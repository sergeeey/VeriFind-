"""
Neo4j Adapter for VEE (Verifiable Execution Environment).

Week 11 Day 3: Knowledge Graph fact verification adapter.

This adapter provides VEE-compliant functions for querying the Knowledge Graph
to verify claims about companies, executives, and ownership.

Available Functions (can be called from LLM-generated code):
- get_company_ceo(ticker: str) -> str | None
- verify_ceo_claim(ticker: str, claimed_name: str) -> bool
- get_company_info(ticker: str) -> dict | None
- get_major_shareholders(ticker: str, min_percent: float = 5.0) -> list[dict]
- verify_ownership_claim(ticker: str, owner_name: str, min_percent: float) -> bool

Usage in VEE code:
    from adapters.neo4j_adapter import get_company_ceo

    ceo = get_company_ceo("AAPL")
    print(f"Apple CEO: {ceo}")  # "Tim Cook"
"""

from typing import Optional, Dict, Any, List
import logging
import os

from src.graph.knowledge_graph import KnowledgeGraph


logger = logging.getLogger(__name__)

# Global KnowledgeGraph instance (lazy-initialized)
_kg: Optional[KnowledgeGraph] = None


def _get_kg() -> KnowledgeGraph:
    """Get or create KnowledgeGraph instance."""
    global _kg
    if _kg is None:
        try:
            _kg = KnowledgeGraph()
            logger.info("Neo4j adapter initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j adapter: {e}")
            raise RuntimeError(
                "Neo4j adapter unavailable. Ensure Neo4j is running "
                "and NEO4J_PASSWORD is set."
            )
    return _kg


# ============================================================================
# VEE-Compliant Functions (callable from LLM-generated code)
# ============================================================================

def get_company_ceo(ticker: str) -> Optional[str]:
    """
    Get current CEO of a company.

    Args:
        ticker: Company ticker symbol (e.g., "AAPL")

    Returns:
        CEO name or None if not found

    Example:
        >>> get_company_ceo("AAPL")
        "Tim Cook"

        >>> get_company_ceo("TSLA")
        "Elon Musk"
    """
    kg = _get_kg()
    ceo = kg.get_company_ceo(ticker.upper())
    logger.info(f"get_company_ceo({ticker}) -> {ceo}")
    return ceo


def verify_ceo_claim(ticker: str, claimed_name: str) -> bool:
    """
    Verify if a person is the CEO of a company.

    Args:
        ticker: Company ticker symbol
        claimed_name: Claimed CEO name

    Returns:
        True if claim is verified, False otherwise

    Example:
        >>> verify_ceo_claim("AAPL", "Tim Cook")
        True

        >>> verify_ceo_claim("AAPL", "Steve Jobs")
        False
    """
    kg = _get_kg()
    result = kg.verify_ceo_claim(ticker.upper(), claimed_name)
    logger.info(f"verify_ceo_claim({ticker}, {claimed_name}) -> {result}")
    return result


def get_company_info(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Get company information.

    Args:
        ticker: Company ticker symbol

    Returns:
        Dictionary with company data or None

    Example:
        >>> info = get_company_info("AAPL")
        >>> info["name"]
        "Apple Inc."
        >>> info["sector"]
        "Technology"
    """
    kg = _get_kg()
    company = kg.get_company(ticker.upper())
    logger.info(f"get_company_info({ticker}) -> {company is not None}")
    return company


def get_major_shareholders(
    ticker: str,
    min_percent: float = 5.0
) -> List[Dict[str, Any]]:
    """
    Get major shareholders (>= min_percent).

    Args:
        ticker: Company ticker symbol
        min_percent: Minimum ownership percentage (default: 5.0)

    Returns:
        List of ownership stake dictionaries

    Example:
        >>> shareholders = get_major_shareholders("AAPL", min_percent=5.0)
        >>> len(shareholders)
        2
        >>> shareholders[0]["owner_name"]
        "Vanguard Group"
        >>> shareholders[0]["percent"]
        8.5
    """
    kg = _get_kg()
    stakes = kg.get_major_shareholders(ticker.upper(), min_percent=min_percent)
    logger.info(f"get_major_shareholders({ticker}, {min_percent}) -> {len(stakes)} results")
    return stakes


def verify_ownership_claim(
    ticker: str,
    owner_name: str,
    min_percent: float
) -> bool:
    """
    Verify if an owner holds at least min_percent of a company.

    Args:
        ticker: Company ticker symbol
        owner_name: Owner name (can be partial match)
        min_percent: Minimum claimed percentage

    Returns:
        True if claim is verified, False otherwise

    Example:
        >>> verify_ownership_claim("TSLA", "Elon Musk", 15.0)
        True

        >>> verify_ownership_claim("AAPL", "Vanguard", 5.0)
        True

        >>> verify_ownership_claim("AAPL", "Vanguard", 50.0)
        False
    """
    kg = _get_kg()
    result = kg.verify_ownership_claim(ticker.upper(), owner_name, min_percent)
    logger.info(f"verify_ownership_claim({ticker}, {owner_name}, {min_percent}) -> {result}")
    return result


def get_company_executives(ticker: str, current_only: bool = True) -> List[Dict[str, Any]]:
    """
    Get all executives for a company.

    Args:
        ticker: Company ticker symbol
        current_only: Only return current executives (default: True)

    Returns:
        List of executive dictionaries

    Example:
        >>> execs = get_company_executives("AAPL")
        >>> len(execs)
        2
        >>> execs[0]["name"]
        "Tim Cook"
        >>> execs[0]["title"]
        "CEO"
    """
    kg = _get_kg()
    executives = kg.get_company_executives(ticker.upper(), current_only=current_only)
    logger.info(f"get_company_executives({ticker}, {current_only}) -> {len(executives)} results")
    return executives


def search_companies(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search companies by name or ticker.

    Args:
        query: Search query (name or ticker)
        limit: Maximum results (default: 10)

    Returns:
        List of matching company dictionaries

    Example:
        >>> companies = search_companies("Apple")
        >>> len(companies)
        1
        >>> companies[0]["ticker"]
        "AAPL"

        >>> companies = search_companies("Tech")
        >>> len(companies) > 1
        True
    """
    kg = _get_kg()
    results = kg.search_companies(query, limit=limit)
    logger.info(f"search_companies({query}, {limit}) -> {len(results)} results")
    return results


def get_company_summary(ticker: str) -> Dict[str, Any]:
    """
    Get comprehensive company summary (company + executives + ownership).

    Args:
        ticker: Company ticker symbol

    Returns:
        Dictionary with company, executives, and major shareholders

    Example:
        >>> summary = get_company_summary("AAPL")
        >>> summary["company"]["name"]
        "Apple Inc."
        >>> len(summary["executives"])
        2
        >>> len(summary["major_shareholders"])
        2
    """
    kg = _get_kg()
    summary = kg.get_company_summary(ticker.upper())
    logger.info(f"get_company_summary({ticker}) -> {summary['company'] is not None}")
    return summary


# ============================================================================
# Adapter Metadata
# ============================================================================

ADAPTER_METADATA = {
    "name": "neo4j_adapter",
    "description": "Knowledge Graph fact verification adapter",
    "version": "1.0.0",
    "functions": [
        {
            "name": "get_company_ceo",
            "description": "Get current CEO of a company",
            "parameters": ["ticker: str"],
            "returns": "str | None"
        },
        {
            "name": "verify_ceo_claim",
            "description": "Verify if a person is the CEO of a company",
            "parameters": ["ticker: str", "claimed_name: str"],
            "returns": "bool"
        },
        {
            "name": "get_company_info",
            "description": "Get company information",
            "parameters": ["ticker: str"],
            "returns": "dict | None"
        },
        {
            "name": "get_major_shareholders",
            "description": "Get major shareholders (>= min_percent)",
            "parameters": ["ticker: str", "min_percent: float = 5.0"],
            "returns": "list[dict]"
        },
        {
            "name": "verify_ownership_claim",
            "description": "Verify ownership claim",
            "parameters": ["ticker: str", "owner_name: str", "min_percent: float"],
            "returns": "bool"
        },
        {
            "name": "get_company_executives",
            "description": "Get all executives for a company",
            "parameters": ["ticker: str", "current_only: bool = True"],
            "returns": "list[dict]"
        },
        {
            "name": "search_companies",
            "description": "Search companies by name or ticker",
            "parameters": ["query: str", "limit: int = 10"],
            "returns": "list[dict]"
        },
        {
            "name": "get_company_summary",
            "description": "Get comprehensive company summary",
            "parameters": ["ticker: str"],
            "returns": "dict"
        }
    ],
    "requires": ["Neo4j", "KnowledgeGraph"],
    "safety_level": "READ_ONLY"  # No mutations allowed
}


def get_adapter_metadata() -> Dict[str, Any]:
    """Get adapter metadata for VEE registration."""
    return ADAPTER_METADATA


# ============================================================================
# Cleanup
# ============================================================================

def close_adapter():
    """Close Neo4j connection (called on VEE shutdown)."""
    global _kg
    if _kg is not None:
        _kg.close()
        _kg = None
        logger.info("Neo4j adapter closed")
