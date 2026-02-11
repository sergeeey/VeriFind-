"""
Knowledge Graph Data Seeding Script.

Week 11 Day 3: Populate Neo4j with Top 10 S&P 500 companies.

Data includes:
- Company information (ticker, name, sector, market cap)
- Current CEOs and key executives
- Major institutional shareholders (>5%)

Usage:
    python scripts/seed_knowledge_graph.py

Data is current as of Q1 2026.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.graph.knowledge_graph import KnowledgeGraph
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Top 10 S&P 500 Companies (by Market Cap, Q1 2026)
# ============================================================================

COMPANIES = [
    {
        'ticker': 'AAPL',
        'name': 'Apple Inc.',
        'sector': 'Technology',
        'industry': 'Consumer Electronics',
        'market_cap': 3_500_000_000_000,  # $3.5T
        'founded_year': 1976,
        'headquarters': 'Cupertino, California',
        'employees': 164000,
        'website': 'https://www.apple.com'
    },
    {
        'ticker': 'MSFT',
        'name': 'Microsoft Corporation',
        'sector': 'Technology',
        'industry': 'Software',
        'market_cap': 3_200_000_000_000,  # $3.2T
        'founded_year': 1975,
        'headquarters': 'Redmond, Washington',
        'employees': 228000,
        'website': 'https://www.microsoft.com'
    },
    {
        'ticker': 'NVDA',
        'name': 'NVIDIA Corporation',
        'sector': 'Technology',
        'industry': 'Semiconductors',
        'market_cap': 2_800_000_000_000,  # $2.8T
        'founded_year': 1993,
        'headquarters': 'Santa Clara, California',
        'employees': 29600,
        'website': 'https://www.nvidia.com'
    },
    {
        'ticker': 'GOOGL',
        'name': 'Alphabet Inc.',
        'sector': 'Technology',
        'industry': 'Internet Services',
        'market_cap': 2_100_000_000_000,  # $2.1T
        'founded_year': 1998,
        'headquarters': 'Mountain View, California',
        'employees': 190000,
        'website': 'https://abc.xyz'
    },
    {
        'ticker': 'AMZN',
        'name': 'Amazon.com Inc.',
        'sector': 'Consumer Discretionary',
        'industry': 'E-commerce',
        'market_cap': 1_900_000_000_000,  # $1.9T
        'founded_year': 1994,
        'headquarters': 'Seattle, Washington',
        'employees': 1608000,
        'website': 'https://www.amazon.com'
    },
    {
        'ticker': 'META',
        'name': 'Meta Platforms Inc.',
        'sector': 'Technology',
        'industry': 'Social Media',
        'market_cap': 1_400_000_000_000,  # $1.4T
        'founded_year': 2004,
        'headquarters': 'Menlo Park, California',
        'employees': 86482,
        'website': 'https://www.meta.com'
    },
    {
        'ticker': 'TSLA',
        'name': 'Tesla Inc.',
        'sector': 'Consumer Discretionary',
        'industry': 'Automotive',
        'market_cap': 1_100_000_000_000,  # $1.1T
        'founded_year': 2003,
        'headquarters': 'Austin, Texas',
        'employees': 140473,
        'website': 'https://www.tesla.com'
    },
    {
        'ticker': 'BRK.B',
        'name': 'Berkshire Hathaway Inc.',
        'sector': 'Financials',
        'industry': 'Conglomerate',
        'market_cap': 950_000_000_000,  # $950B
        'founded_year': 1839,
        'headquarters': 'Omaha, Nebraska',
        'employees': 383000,
        'website': 'https://www.berkshirehathaway.com'
    },
    {
        'ticker': 'LLY',
        'name': 'Eli Lilly and Company',
        'sector': 'Healthcare',
        'industry': 'Pharmaceuticals',
        'market_cap': 850_000_000_000,  # $850B
        'founded_year': 1876,
        'headquarters': 'Indianapolis, Indiana',
        'employees': 43000,
        'website': 'https://www.lilly.com'
    },
    {
        'ticker': 'V',
        'name': 'Visa Inc.',
        'sector': 'Financials',
        'industry': 'Payment Processing',
        'market_cap': 620_000_000_000,  # $620B
        'founded_year': 1958,
        'headquarters': 'San Francisco, California',
        'employees': 30800,
        'website': 'https://www.visa.com'
    }
]


# ============================================================================
# Executive Leadership (current as of Q1 2026)
# ============================================================================

EXECUTIVES = [
    # Apple
    {'name': 'Tim Cook', 'title': 'CEO', 'company_ticker': 'AAPL', 'start_date': '2011-08-24'},
    {'name': 'Luca Maestri', 'title': 'CFO', 'company_ticker': 'AAPL', 'start_date': '2014-05-05'},

    # Microsoft
    {'name': 'Satya Nadella', 'title': 'CEO', 'company_ticker': 'MSFT', 'start_date': '2014-02-04'},
    {'name': 'Amy Hood', 'title': 'CFO', 'company_ticker': 'MSFT', 'start_date': '2013-11-18'},

    # NVIDIA
    {'name': 'Jensen Huang', 'title': 'CEO', 'company_ticker': 'NVDA', 'start_date': '1993-04-05'},
    {'name': 'Colette Kress', 'title': 'CFO', 'company_ticker': 'NVDA', 'start_date': '2013-09-01'},

    # Alphabet
    {'name': 'Sundar Pichai', 'title': 'CEO', 'company_ticker': 'GOOGL', 'start_date': '2015-10-02'},
    {'name': 'Ruth Porat', 'title': 'CFO', 'company_ticker': 'GOOGL', 'start_date': '2015-05-26'},

    # Amazon
    {'name': 'Andy Jassy', 'title': 'CEO', 'company_ticker': 'AMZN', 'start_date': '2021-07-05'},
    {'name': 'Brian Olsavsky', 'title': 'CFO', 'company_ticker': 'AMZN', 'start_date': '2015-06-30'},

    # Meta
    {'name': 'Mark Zuckerberg', 'title': 'CEO', 'company_ticker': 'META', 'start_date': '2004-02-04'},
    {'name': 'Susan Li', 'title': 'CFO', 'company_ticker': 'META', 'start_date': '2022-11-01'},

    # Tesla
    {'name': 'Elon Musk', 'title': 'CEO', 'company_ticker': 'TSLA', 'start_date': '2008-10-01'},
    {'name': 'Vaibhav Taneja', 'title': 'CFO', 'company_ticker': 'TSLA', 'start_date': '2023-08-14'},

    # Berkshire Hathaway
    {'name': 'Warren Buffett', 'title': 'CEO', 'company_ticker': 'BRK.B', 'start_date': '1965-05-10'},

    # Eli Lilly
    {'name': 'David Ricks', 'title': 'CEO', 'company_ticker': 'LLY', 'start_date': '2017-01-01'},
    {'name': 'Anat Ashkenazi', 'title': 'CFO', 'company_ticker': 'LLY', 'start_date': '2021-07-01'},

    # Visa
    {'name': 'Ryan McInerney', 'title': 'CEO', 'company_ticker': 'V', 'start_date': '2023-02-01'},
    {'name': 'Vasant Prabhu', 'title': 'CFO', 'company_ticker': 'V', 'start_date': '2015-12-01'}
]


# ============================================================================
# Major Institutional Shareholders (>5% ownership)
# ============================================================================

OWNERSHIP_STAKES = [
    # Apple
    {'owner_name': 'Vanguard Group', 'owner_type': 'Institutional', 'ticker': 'AAPL', 'percent': 8.5, 'as_of_date': '2025-12-31'},
    {'owner_name': 'BlackRock', 'owner_type': 'Institutional', 'ticker': 'AAPL', 'percent': 7.2, 'as_of_date': '2025-12-31'},

    # Microsoft
    {'owner_name': 'Vanguard Group', 'owner_type': 'Institutional', 'ticker': 'MSFT', 'percent': 8.8, 'as_of_date': '2025-12-31'},
    {'owner_name': 'BlackRock', 'owner_type': 'Institutional', 'ticker': 'MSFT', 'percent': 7.5, 'as_of_date': '2025-12-31'},

    # NVIDIA
    {'owner_name': 'Vanguard Group', 'owner_type': 'Institutional', 'ticker': 'NVDA', 'percent': 8.1, 'as_of_date': '2025-12-31'},
    {'owner_name': 'BlackRock', 'owner_type': 'Institutional', 'ticker': 'NVDA', 'percent': 6.9, 'as_of_date': '2025-12-31'},
    {'owner_name': 'Jensen Huang', 'owner_type': 'Insider', 'ticker': 'NVDA', 'percent': 3.5, 'as_of_date': '2025-12-31'},

    # Alphabet
    {'owner_name': 'Vanguard Group', 'owner_type': 'Institutional', 'ticker': 'GOOGL', 'percent': 7.9, 'as_of_date': '2025-12-31'},
    {'owner_name': 'BlackRock', 'owner_type': 'Institutional', 'ticker': 'GOOGL', 'percent': 6.8, 'as_of_date': '2025-12-31'},
    {'owner_name': 'Larry Page', 'owner_type': 'Insider', 'ticker': 'GOOGL', 'percent': 5.8, 'as_of_date': '2025-12-31'},
    {'owner_name': 'Sergey Brin', 'owner_type': 'Insider', 'ticker': 'GOOGL', 'percent': 5.6, 'as_of_date': '2025-12-31'},

    # Amazon
    {'owner_name': 'Vanguard Group', 'owner_type': 'Institutional', 'ticker': 'AMZN', 'percent': 7.3, 'as_of_date': '2025-12-31'},
    {'owner_name': 'BlackRock', 'owner_type': 'Institutional', 'ticker': 'AMZN', 'percent': 6.1, 'as_of_date': '2025-12-31'},
    {'owner_name': 'Jeff Bezos', 'owner_type': 'Insider', 'ticker': 'AMZN', 'percent': 9.2, 'as_of_date': '2025-12-31'},

    # Meta
    {'owner_name': 'Mark Zuckerberg', 'owner_type': 'Insider', 'ticker': 'META', 'percent': 13.5, 'as_of_date': '2025-12-31'},
    {'owner_name': 'Vanguard Group', 'owner_type': 'Institutional', 'ticker': 'META', 'percent': 7.8, 'as_of_date': '2025-12-31'},
    {'owner_name': 'BlackRock', 'owner_type': 'Institutional', 'ticker': 'META', 'percent': 6.4, 'as_of_date': '2025-12-31'},

    # Tesla
    {'owner_name': 'Elon Musk', 'owner_type': 'Insider', 'ticker': 'TSLA', 'percent': 20.5, 'as_of_date': '2025-12-31'},
    {'owner_name': 'Vanguard Group', 'owner_type': 'Institutional', 'ticker': 'TSLA', 'percent': 6.9, 'as_of_date': '2025-12-31'},
    {'owner_name': 'BlackRock', 'owner_type': 'Institutional', 'ticker': 'TSLA', 'percent': 5.8, 'as_of_date': '2025-12-31'},

    # Berkshire Hathaway
    {'owner_name': 'Warren Buffett', 'owner_type': 'Insider', 'ticker': 'BRK.B', 'percent': 15.8, 'as_of_date': '2025-12-31'},
    {'owner_name': 'Vanguard Group', 'owner_type': 'Institutional', 'ticker': 'BRK.B', 'percent': 9.2, 'as_of_date': '2025-12-31'},

    # Eli Lilly
    {'owner_name': 'Vanguard Group', 'owner_type': 'Institutional', 'ticker': 'LLY', 'percent': 8.9, 'as_of_date': '2025-12-31'},
    {'owner_name': 'BlackRock', 'owner_type': 'Institutional', 'ticker': 'LLY', 'percent': 7.6, 'as_of_date': '2025-12-31'},

    # Visa
    {'owner_name': 'Vanguard Group', 'owner_type': 'Institutional', 'ticker': 'V', 'percent': 8.3, 'as_of_date': '2025-12-31'},
    {'owner_name': 'BlackRock', 'owner_type': 'Institutional', 'ticker': 'V', 'percent': 7.1, 'as_of_date': '2025-12-31'}
]


def seed_knowledge_graph():
    """Populate Knowledge Graph with Top 10 S&P 500 data."""
    logger.info("Starting Knowledge Graph data seeding...")

    try:
        # Connect to Neo4j
        kg = KnowledgeGraph()
        logger.info("Connected to Neo4j")

        # Clear existing Company/Executive/Ownership data (optional, for clean slate)
        with kg.driver.session() as session:
            session.run("MATCH (c:Company) DETACH DELETE c")
            session.run("MATCH (e:Executive) DETACH DELETE e")
            session.run("MATCH (o:OwnershipStake) DETACH DELETE o")
        logger.info("Cleared existing knowledge graph data")

        # Seed companies
        logger.info(f"Seeding {len(COMPANIES)} companies...")
        for company in COMPANIES:
            kg.create_company(**company)
        logger.info(f"✅ Created {len(COMPANIES)} companies")

        # Seed executives
        logger.info(f"Seeding {len(EXECUTIVES)} executives...")
        for exec_data in EXECUTIVES:
            kg.create_executive(**exec_data)
        logger.info(f"✅ Created {len(EXECUTIVES)} executives")

        # Seed ownership stakes
        logger.info(f"Seeding {len(OWNERSHIP_STAKES)} ownership stakes...")
        for stake in OWNERSHIP_STAKES:
            kg.create_ownership_stake(**stake)
        logger.info(f"✅ Created {len(OWNERSHIP_STAKES)} ownership stakes")

        # Get stats
        stats = kg.get_knowledge_graph_stats()
        logger.info("\n" + "="*50)
        logger.info("Knowledge Graph Statistics:")
        logger.info(f"  Companies: {stats['company_count']}")
        logger.info(f"  Executives: {stats['executive_count']}")
        logger.info(f"  Ownership Stakes: {stats['ownership_count']}")
        logger.info(f"  Total Nodes: {stats['company_count'] + stats['executive_count'] + stats['ownership_count']}")
        logger.info(f"  Total Relationships: {stats['relationship_count']}")
        logger.info("="*50)

        # Verification examples
        logger.info("\nVerification Examples:")
        logger.info("-" * 50)

        # Test CEO verification
        test_ceos = [
            ('AAPL', 'Tim Cook'),
            ('TSLA', 'Elon Musk'),
            ('NVDA', 'Jensen Huang')
        ]

        for ticker, ceo in test_ceos:
            is_valid = kg.verify_ceo_claim(ticker, ceo)
            status = "✅ VERIFIED" if is_valid else "❌ FAILED"
            logger.info(f"  {status}: {ceo} is CEO of {ticker}")

        # Test ownership verification
        test_ownership = [
            ('AAPL', 'Vanguard', 5.0),
            ('TSLA', 'Elon Musk', 15.0),
            ('META', 'Mark Zuckerberg', 10.0)
        ]

        for ticker, owner, min_pct in test_ownership:
            is_valid = kg.verify_ownership_claim(ticker, owner, min_pct)
            status = "✅ VERIFIED" if is_valid else "❌ FAILED"
            logger.info(f"  {status}: {owner} owns ≥{min_pct}% of {ticker}")

        logger.info("-" * 50)
        logger.info("\n🎉 Knowledge Graph seeding complete!")

        kg.close()

    except Exception as e:
        logger.error(f"Error seeding knowledge graph: {e}")
        raise


if __name__ == '__main__':
    seed_knowledge_graph()
