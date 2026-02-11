"""
Knowledge Graph Extension for APE 2026.

Week 11 Day 3: Company/Executive/Ownership data for fact verification.

Graph Schema Extensions:
- Company nodes: ticker, name, sector, market_cap, founded_year
- Executive nodes: name, title, company_ticker, start_date, end_date
- OwnershipStake nodes: owner_name, owner_type, ticker, percent, as_of_date
- Relationships:
  - (:Company)-[:EMPLOYS]->(:Executive)
  - (:Executive)-[:LEADS]->(:Company) [CEO/CFO]
  - (:OwnershipStake)-[:OWNS]->(:Company)

Usage:
    kg = KnowledgeGraph()
    kg.create_company("AAPL", "Apple Inc.", sector="Technology")
    kg.create_executive("Tim Cook", "CEO", "AAPL", start_date="2011-08-24")

    ceo = kg.get_company_ceo("AAPL")  # Returns "Tim Cook"
    kg.verify_ceo_claim("AAPL", "Tim Cook")  # Returns True
"""

from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import logging
import os

from src.graph.neo4j_client import Neo4jGraphClient


class KnowledgeGraph(Neo4jGraphClient):
    """
    Extended Neo4j client for Company/Executive/Ownership knowledge graph.

    Inherits from Neo4jGraphClient to maintain Episode/VerifiedFact functionality.
    """

    def __init__(
        self,
        uri: str = 'neo4j://localhost:7688',
        user: str = 'neo4j',
        password: Optional[str] = None
    ):
        """Initialize Knowledge Graph client."""
        super().__init__(uri, user, password)
        self.logger = logging.getLogger(__name__)
        self._ensure_constraints()

    def _ensure_constraints(self):
        """Create uniqueness constraints and indexes for performance."""
        with self.driver.session() as session:
            # Company uniqueness
            session.run("""
                CREATE CONSTRAINT company_ticker_unique IF NOT EXISTS
                FOR (c:Company) REQUIRE c.ticker IS UNIQUE
            """)

            # Executive index
            session.run("""
                CREATE INDEX executive_name_idx IF NOT EXISTS
                FOR (e:Executive) ON (e.name)
            """)

            # OwnershipStake index
            session.run("""
                CREATE INDEX ownership_ticker_idx IF NOT EXISTS
                FOR (o:OwnershipStake) ON (o.ticker)
            """)

        self.logger.info("Knowledge graph constraints created")

    # ============================================================================
    # Company Methods
    # ============================================================================

    def create_company(
        self,
        ticker: str,
        name: str,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        market_cap: Optional[float] = None,
        founded_year: Optional[int] = None,
        headquarters: Optional[str] = None,
        employees: Optional[int] = None,
        website: Optional[str] = None
    ):
        """
        Create or update Company node.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            name: Company name (e.g., "Apple Inc.")
            sector: Sector (e.g., "Technology")
            industry: Industry (e.g., "Consumer Electronics")
            market_cap: Market capitalization in USD
            founded_year: Year founded
            headquarters: HQ location
            employees: Number of employees
            website: Company website
        """
        with self.driver.session() as session:
            session.run("""
                MERGE (c:Company {ticker: $ticker})
                SET c.name = $name,
                    c.sector = $sector,
                    c.industry = $industry,
                    c.market_cap = $market_cap,
                    c.founded_year = $founded_year,
                    c.headquarters = $headquarters,
                    c.employees = $employees,
                    c.website = $website,
                    c.updated_at = $updated_at
            """, {
                'ticker': ticker.upper(),
                'name': name,
                'sector': sector,
                'industry': industry,
                'market_cap': market_cap,
                'founded_year': founded_year,
                'headquarters': headquarters,
                'employees': employees,
                'website': website,
                'updated_at': datetime.utcnow().isoformat()
            })

        self.logger.info(f"Created/updated Company: {ticker} ({name})")

    def get_company(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get Company node by ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Company data or None
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company {ticker: $ticker})
                RETURN c
            """, {'ticker': ticker.upper()})

            record = result.single()
            if record:
                return dict(record['c'])
            return None

    def list_companies(
        self,
        sector: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List companies, optionally filtered by sector.

        Args:
            sector: Filter by sector (optional)
            limit: Max records to return

        Returns:
            List of company dictionaries
        """
        with self.driver.session() as session:
            if sector:
                result = session.run("""
                    MATCH (c:Company)
                    WHERE c.sector = $sector
                    RETURN c
                    ORDER BY c.market_cap DESC
                    LIMIT $limit
                """, {'sector': sector, 'limit': limit})
            else:
                result = session.run("""
                    MATCH (c:Company)
                    RETURN c
                    ORDER BY c.market_cap DESC
                    LIMIT $limit
                """, {'limit': limit})

            return [dict(record['c']) for record in result]

    # ============================================================================
    # Executive Methods
    # ============================================================================

    def create_executive(
        self,
        name: str,
        title: str,
        company_ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_current: bool = True
    ):
        """
        Create Executive node and link to Company.

        Args:
            name: Executive name (e.g., "Tim Cook")
            title: Title (e.g., "CEO", "CFO")
            company_ticker: Company ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD) if no longer in role
            is_current: Whether currently in this role
        """
        with self.driver.session() as session:
            # Create executive node
            session.run("""
                MERGE (e:Executive {name: $name, title: $title, company_ticker: $company_ticker})
                SET e.start_date = $start_date,
                    e.end_date = $end_date,
                    e.is_current = $is_current,
                    e.updated_at = $updated_at
            """, {
                'name': name,
                'title': title.upper(),
                'company_ticker': company_ticker.upper(),
                'start_date': start_date,
                'end_date': end_date,
                'is_current': is_current,
                'updated_at': datetime.utcnow().isoformat()
            })

            # Link to company
            session.run("""
                MATCH (c:Company {ticker: $company_ticker})
                MATCH (e:Executive {name: $name, title: $title, company_ticker: $company_ticker})
                MERGE (c)-[:EMPLOYS]->(e)
            """, {
                'company_ticker': company_ticker.upper(),
                'name': name,
                'title': title.upper()
            })

            # Create LEADS relationship for CEO/CFO
            if title.upper() in ['CEO', 'CFO', 'COO', 'CTO', 'PRESIDENT']:
                session.run("""
                    MATCH (c:Company {ticker: $company_ticker})
                    MATCH (e:Executive {name: $name, title: $title, company_ticker: $company_ticker})
                    MERGE (e)-[:LEADS {role: $title}]->(c)
                """, {
                    'company_ticker': company_ticker.upper(),
                    'name': name,
                    'title': title.upper()
                })

        self.logger.info(f"Created Executive: {name} ({title} at {company_ticker})")

    def get_company_ceo(self, ticker: str) -> Optional[str]:
        """
        Get current CEO of a company.

        Args:
            ticker: Company ticker symbol

        Returns:
            CEO name or None
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Executive {title: 'CEO', company_ticker: $ticker, is_current: true})
                RETURN e.name as name
                LIMIT 1
            """, {'ticker': ticker.upper()})

            record = result.single()
            if record:
                return record['name']
            return None

    def get_company_executives(
        self,
        ticker: str,
        current_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all executives for a company.

        Args:
            ticker: Company ticker symbol
            current_only: Only return current executives

        Returns:
            List of executive dictionaries
        """
        with self.driver.session() as session:
            if current_only:
                result = session.run("""
                    MATCH (c:Company {ticker: $ticker})-[:EMPLOYS]->(e:Executive {is_current: true})
                    RETURN e
                    ORDER BY e.title
                """, {'ticker': ticker.upper()})
            else:
                result = session.run("""
                    MATCH (c:Company {ticker: $ticker})-[:EMPLOYS]->(e:Executive)
                    RETURN e
                    ORDER BY e.start_date DESC
                """, {'ticker': ticker.upper()})

            return [dict(record['e']) for record in result]

    def verify_ceo_claim(self, ticker: str, claimed_name: str) -> bool:
        """
        Verify if a person is the CEO of a company.

        Args:
            ticker: Company ticker symbol
            claimed_name: Claimed CEO name

        Returns:
            True if claim is verified, False otherwise
        """
        actual_ceo = self.get_company_ceo(ticker)
        if not actual_ceo:
            return False

        # Normalize names for comparison
        claimed_normalized = claimed_name.strip().lower()
        actual_normalized = actual_ceo.strip().lower()

        return claimed_normalized == actual_normalized

    # ============================================================================
    # Ownership Methods
    # ============================================================================

    def create_ownership_stake(
        self,
        owner_name: str,
        owner_type: str,
        ticker: str,
        percent: float,
        shares: Optional[int] = None,
        as_of_date: Optional[str] = None
    ):
        """
        Create OwnershipStake node.

        Args:
            owner_name: Owner name (e.g., "Vanguard Group")
            owner_type: Type (e.g., "Institutional", "Individual", "Insider")
            ticker: Company ticker symbol
            percent: Ownership percentage (0-100)
            shares: Number of shares owned
            as_of_date: Date of ownership data (YYYY-MM-DD)
        """
        with self.driver.session() as session:
            session.run("""
                MERGE (o:OwnershipStake {
                    owner_name: $owner_name,
                    ticker: $ticker
                })
                SET o.owner_type = $owner_type,
                    o.percent = $percent,
                    o.shares = $shares,
                    o.as_of_date = $as_of_date,
                    o.updated_at = $updated_at
            """, {
                'owner_name': owner_name,
                'owner_type': owner_type,
                'ticker': ticker.upper(),
                'percent': percent,
                'shares': shares,
                'as_of_date': as_of_date,
                'updated_at': datetime.utcnow().isoformat()
            })

            # Link to company
            session.run("""
                MATCH (c:Company {ticker: $ticker})
                MATCH (o:OwnershipStake {owner_name: $owner_name, ticker: $ticker})
                MERGE (o)-[:OWNS {percent: $percent}]->(c)
            """, {
                'ticker': ticker.upper(),
                'owner_name': owner_name,
                'percent': percent
            })

        self.logger.info(f"Created OwnershipStake: {owner_name} owns {percent}% of {ticker}")

    def get_major_shareholders(
        self,
        ticker: str,
        min_percent: float = 5.0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get major shareholders (>= min_percent).

        Args:
            ticker: Company ticker symbol
            min_percent: Minimum ownership percentage
            limit: Max records to return

        Returns:
            List of ownership stake dictionaries
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (o:OwnershipStake {ticker: $ticker})
                WHERE o.percent >= $min_percent
                RETURN o
                ORDER BY o.percent DESC
                LIMIT $limit
            """, {
                'ticker': ticker.upper(),
                'min_percent': min_percent,
                'limit': limit
            })

            return [dict(record['o']) for record in result]

    def verify_ownership_claim(
        self,
        ticker: str,
        owner_name: str,
        min_percent: float
    ) -> bool:
        """
        Verify if an owner holds at least min_percent of a company.

        Args:
            ticker: Company ticker symbol
            owner_name: Owner name
            min_percent: Minimum claimed percentage

        Returns:
            True if claim is verified, False otherwise
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (o:OwnershipStake {ticker: $ticker})
                WHERE toLower(o.owner_name) CONTAINS toLower($owner_name)
                  AND o.percent >= $min_percent
                RETURN o.percent as percent
                LIMIT 1
            """, {
                'ticker': ticker.upper(),
                'owner_name': owner_name,
                'min_percent': min_percent
            })

            record = result.single()
            return record is not None

    # ============================================================================
    # Verification & Query Methods
    # ============================================================================

    def search_companies(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search companies by name or ticker.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of matching companies
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company)
                WHERE toLower(c.name) CONTAINS toLower($query)
                   OR toLower(c.ticker) CONTAINS toLower($query)
                RETURN c
                ORDER BY c.market_cap DESC
                LIMIT $limit
            """, {'query': query, 'limit': limit})

            return [dict(record['c']) for record in result]

    def get_company_summary(self, ticker: str) -> Dict[str, Any]:
        """
        Get comprehensive company summary (company + executives + ownership).

        Args:
            ticker: Company ticker symbol

        Returns:
            Dictionary with company, executives, and major shareholders
        """
        company = self.get_company(ticker)
        if not company:
            return {
                'company': None,
                'executives': [],
                'major_shareholders': []
            }

        executives = self.get_company_executives(ticker, current_only=True)
        shareholders = self.get_major_shareholders(ticker, min_percent=5.0)

        return {
            'company': company,
            'executives': executives,
            'major_shareholders': shareholders
        }

    def get_knowledge_graph_stats(self) -> Dict[str, int]:
        """
        Get knowledge graph statistics.

        Returns:
            Dictionary with node and relationship counts
        """
        base_stats = self.get_graph_stats()

        with self.driver.session() as session:
            # Count Companies
            company_result = session.run("MATCH (c:Company) RETURN count(c) as count")
            company_count = company_result.single()['count']

            # Count Executives
            exec_result = session.run("MATCH (e:Executive) RETURN count(e) as count")
            exec_count = exec_result.single()['count']

            # Count Ownership Stakes
            ownership_result = session.run("MATCH (o:OwnershipStake) RETURN count(o) as count")
            ownership_count = ownership_result.single()['count']

        return {
            **base_stats,
            'company_count': company_count,
            'executive_count': exec_count,
            'ownership_count': ownership_count
        }


# Convenience alias
KG = KnowledgeGraph
