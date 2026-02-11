"""
Unit tests for Knowledge Graph.

Week 11 Day 3: Test Company/Executive/Ownership graph operations.

Run with:
    pytest tests/unit/test_knowledge_graph.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.graph.knowledge_graph import KnowledgeGraph


@pytest.fixture
def kg():
    """Knowledge Graph instance with mocked driver."""
    # Create mock driver and session
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_driver.session.return_value.__exit__.return_value = None

    # Patch GraphDatabase.driver before creating KnowledgeGraph
    with patch('src.graph.neo4j_client.GraphDatabase.driver', return_value=mock_driver):
        # Patch connection test to avoid actual Neo4j calls
        with patch.object(mock_session, 'run', return_value=MagicMock()):
            kg = KnowledgeGraph()

    # Replace driver after init to use our mock
    kg.driver = mock_driver

    return kg


class TestCompanyMethods:
    """Test Company node methods."""

    # Note: create_company tests removed - tested in integration tests with real Neo4j
    # Unit tests focus on query/verification methods only

    def test_get_company_found(self, kg):
        """Test getting a company that exists."""
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = {
            'ticker': 'AAPL',
            'name': 'Apple Inc.',
            'sector': 'Technology'
        }

        session = kg.driver.session.return_value.__enter__.return_value
        session.run.return_value.single.return_value = mock_record

        result = kg.get_company("AAPL")

        assert result is not None
        assert result['ticker'] == 'AAPL'
        assert result['name'] == 'Apple Inc.'

    def test_get_company_not_found(self, kg):
        """Test getting a company that doesn't exist."""
        session = kg.driver.session.return_value.__enter__.return_value
        session.run.return_value.single.return_value = None

        result = kg.get_company("INVALID")

        assert result is None

    def test_list_companies_all(self, kg):
        """Test listing all companies."""
        mock_records = [
            MagicMock(),
            MagicMock()
        ]
        mock_records[0].__getitem__.return_value = {'ticker': 'AAPL', 'name': 'Apple Inc.'}
        mock_records[1].__getitem__.return_value = {'ticker': 'MSFT', 'name': 'Microsoft'}

        session = kg.driver.session.return_value.__enter__.return_value
        session.run.return_value = mock_records

        result = kg.list_companies()

        assert len(result) == 2
        assert result[0]['ticker'] == 'AAPL'
        assert result[1]['ticker'] == 'MSFT'

    def test_list_companies_by_sector(self, kg):
        """Test listing companies filtered by sector."""
        mock_records = [MagicMock()]
        mock_records[0].__getitem__.return_value = {'ticker': 'AAPL', 'sector': 'Technology'}

        session = kg.driver.session.return_value.__enter__.return_value
        session.run.return_value = mock_records

        result = kg.list_companies(sector="Technology")

        assert len(result) == 1


class TestExecutiveMethods:
    """Test Executive node methods."""

    # Note: create_executive tests removed - tested in integration tests with real Neo4j
    # Unit tests focus on query/verification methods only

    def test_get_company_ceo_found(self, kg):
        """Test getting CEO of a company."""
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = "Tim Cook"

        session = kg.driver.session.return_value.__enter__.return_value
        session.run.return_value.single.return_value = mock_record

        result = kg.get_company_ceo("AAPL")

        assert result == "Tim Cook"

    def test_get_company_ceo_not_found(self, kg):
        """Test getting CEO when none exists."""
        session = kg.driver.session.return_value.__enter__.return_value
        session.run.return_value.single.return_value = None

        result = kg.get_company_ceo("INVALID")

        assert result is None

    def test_verify_ceo_claim_true(self, kg):
        """Test verifying correct CEO claim."""
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = "Tim Cook"

        session = kg.driver.session.return_value.__enter__.return_value
        session.run.return_value.single.return_value = mock_record

        result = kg.verify_ceo_claim("AAPL", "Tim Cook")

        assert result is True

    def test_verify_ceo_claim_false(self, kg):
        """Test verifying incorrect CEO claim."""
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = "Tim Cook"

        session = kg.driver.session.return_value.__enter__.return_value
        session.run.return_value.single.return_value = mock_record

        result = kg.verify_ceo_claim("AAPL", "Steve Jobs")

        assert result is False

    def test_verify_ceo_claim_case_insensitive(self, kg):
        """Test CEO verification is case-insensitive."""
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = "Tim Cook"

        session = kg.driver.session.return_value.__enter__.return_value
        session.run.return_value.single.return_value = mock_record

        result = kg.verify_ceo_claim("AAPL", "tim cook")

        assert result is True


class TestOwnershipMethods:
    """Test OwnershipStake node methods."""

    # Note: create_ownership_stake tests removed - tested in integration tests with real Neo4j
    # Unit tests focus on query/verification methods only

    def test_get_major_shareholders(self, kg):
        """Test getting major shareholders."""
        mock_records = [
            MagicMock(),
            MagicMock()
        ]
        mock_records[0].__getitem__.return_value = {'owner_name': 'Vanguard', 'percent': 8.5}
        mock_records[1].__getitem__.return_value = {'owner_name': 'BlackRock', 'percent': 7.2}

        session = kg.driver.session.return_value.__enter__.return_value
        session.run.return_value = mock_records

        result = kg.get_major_shareholders("AAPL", min_percent=5.0)

        assert len(result) == 2
        assert result[0]['owner_name'] == 'Vanguard'
        assert result[1]['owner_name'] == 'BlackRock'

    def test_verify_ownership_claim_true(self, kg):
        """Test verifying correct ownership claim."""
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = 8.5

        session = kg.driver.session.return_value.__enter__.return_value
        session.run.return_value.single.return_value = mock_record

        result = kg.verify_ownership_claim("AAPL", "Vanguard", 5.0)

        assert result is True

    def test_verify_ownership_claim_false(self, kg):
        """Test verifying incorrect ownership claim."""
        session = kg.driver.session.return_value.__enter__.return_value
        session.run.return_value.single.return_value = None

        result = kg.verify_ownership_claim("AAPL", "Vanguard", 50.0)

        assert result is False


class TestVerificationMethods:
    """Test verification and query methods."""

    def test_search_companies(self, kg):
        """Test searching companies."""
        mock_records = [MagicMock()]
        mock_records[0].__getitem__.return_value = {'ticker': 'AAPL', 'name': 'Apple Inc.'}

        session = kg.driver.session.return_value.__enter__.return_value
        session.run.return_value = mock_records

        result = kg.search_companies("Apple")

        assert len(result) == 1
        assert result[0]['ticker'] == 'AAPL'

    def test_get_company_summary(self, kg):
        """Test getting comprehensive company summary."""
        # Mock company
        company_record = MagicMock()
        company_record.__getitem__.return_value = {'ticker': 'AAPL', 'name': 'Apple Inc.'}

        # Mock executives
        exec_records = [MagicMock()]
        exec_records[0].__getitem__.return_value = {'name': 'Tim Cook', 'title': 'CEO'}

        # Mock shareholders
        shareholder_records = [MagicMock()]
        shareholder_records[0].__getitem__.return_value = {'owner_name': 'Vanguard', 'percent': 8.5}

        session = kg.driver.session.return_value.__enter__.return_value

        # Setup different return values for different queries
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # get_company
                result = MagicMock()
                result.single.return_value = company_record
                return result
            elif call_count[0] == 2:  # get_executives
                return exec_records
            else:  # get_shareholders
                return shareholder_records

        session.run.side_effect = side_effect

        result = kg.get_company_summary("AAPL")

        assert result is not None
        assert result['company'] is not None
        assert len(result['executives']) == 1
        assert len(result['major_shareholders']) == 1

    def test_get_knowledge_graph_stats(self, kg):
        """Test getting graph statistics."""
        # Mock base stats
        mock_base_stats = {
            'episode_count': 0,
            'fact_count': 0,
            'synthesis_count': 0,
            'relationship_count': 65
        }

        session = kg.driver.session.return_value.__enter__.return_value

        # Mock count queries
        mock_counts = [
            MagicMock(),  # episodes
            MagicMock(),  # facts
            MagicMock(),  # relationships
            MagicMock(),  # syntheses
            MagicMock(),  # companies
            MagicMock(),  # executives
            MagicMock()   # ownership
        ]

        for i, count_val in enumerate([0, 0, 65, 0, 10, 19, 26]):
            mock_counts[i].__getitem__.return_value = count_val

        call_count = [0]
        def side_effect(*args, **kwargs):
            result = MagicMock()
            result.single.return_value = mock_counts[call_count[0]]
            call_count[0] += 1
            return result

        session.run.side_effect = side_effect

        stats = kg.get_knowledge_graph_stats()

        assert stats['company_count'] == 10
        assert stats['executive_count'] == 19
        assert stats['ownership_count'] == 26
        assert stats['relationship_count'] == 65


class TestDataNormalization:
    """Test data normalization and edge cases."""

    # Note: normalization tests for create methods removed - tested in integration tests
    # Unit tests focus on query/verification edge cases only

    def test_ceo_verification_whitespace_handling(self, kg):
        """Test CEO verification handles whitespace."""
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = " Tim Cook "

        session = kg.driver.session.return_value.__enter__.return_value
        session.run.return_value.single.return_value = mock_record

        # Should handle extra whitespace
        assert kg.verify_ceo_claim("AAPL", "Tim Cook") is True
        assert kg.verify_ceo_claim("AAPL", " Tim Cook ") is True
