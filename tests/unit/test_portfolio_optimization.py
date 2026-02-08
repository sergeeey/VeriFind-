"""
Unit tests for Portfolio Optimization.

Week 10 Day 4: Modern Portfolio Theory (MPT) implementation.

Tests validate that:
1. Portfolio optimizer computes max Sharpe correctly
2. Min variance portfolio computed correctly
3. Efficient frontier generated
4. Constraints respected
5. Black-Litterman integration works
"""

import pytest
import numpy as np
import pandas as pd
from src.portfolio.optimizer import (
    Portfolio,
    OptimizationConstraints,
    PortfolioOptimizer,
    compute_efficient_frontier
)


class TestPortfolio:
    """Tests for Portfolio dataclass."""

    def test_create_portfolio(self):
        """Test creating a portfolio."""
        weights = {"AAPL": 0.4, "MSFT": 0.3, "GOOGL": 0.3}
        portfolio = Portfolio(
            weights=weights,
            expected_return=0.15,
            volatility=0.20,
            sharpe_ratio=0.75
        )

        assert portfolio.weights == weights
        assert portfolio.expected_return == 0.15
        assert portfolio.volatility == 0.20
        assert portfolio.sharpe_ratio == 0.75

    def test_weights_sum_to_one(self):
        """Test that weights sum to 1.0."""
        weights = {"AAPL": 0.5, "MSFT": 0.5}
        portfolio = Portfolio(weights=weights, expected_return=0.1, volatility=0.15, sharpe_ratio=0.67)

        total_weight = sum(portfolio.weights.values())
        assert abs(total_weight - 1.0) < 1e-6


class TestOptimizationConstraints:
    """Tests for OptimizationConstraints dataclass."""

    def test_create_default_constraints(self):
        """Test creating constraints with defaults."""
        constraints = OptimizationConstraints()

        assert constraints.min_weight == 0.0
        assert constraints.max_weight == 1.0
        assert constraints.sum_weights == 1.0

    def test_create_custom_constraints(self):
        """Test creating custom constraints."""
        constraints = OptimizationConstraints(
            min_weight=0.05,
            max_weight=0.40,
            sum_weights=1.0
        )

        assert constraints.min_weight == 0.05
        assert constraints.max_weight == 0.40


class TestPortfolioOptimizer:
    """Tests for PortfolioOptimizer class."""

    def setup_method(self):
        """Setup test data."""
        # Generate sample returns data (3 assets, 252 days)
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=252, freq='D')

        # Correlated returns for realistic behavior
        returns = pd.DataFrame({
            'AAPL': np.random.normal(0.0005, 0.02, 252),
            'MSFT': np.random.normal(0.0006, 0.015, 252),
            'GOOGL': np.random.normal(0.0004, 0.018, 252)
        }, index=dates)

        self.returns = returns
        self.optimizer = PortfolioOptimizer(returns)

    # ========================================================================
    # Max Sharpe Ratio
    # ========================================================================

    def test_max_sharpe_portfolio(self):
        """Test computing maximum Sharpe ratio portfolio."""
        portfolio = self.optimizer.max_sharpe_ratio(rf_rate=0.05)

        assert portfolio is not None
        assert isinstance(portfolio, Portfolio)

        # Weights sum to 1
        total_weight = sum(portfolio.weights.values())
        assert abs(total_weight - 1.0) < 1e-4

        # All weights non-negative (long-only)
        assert all(w >= -1e-6 for w in portfolio.weights.values())

        # Sharpe ratio is positive
        assert portfolio.sharpe_ratio > 0

    def test_max_sharpe_with_constraints(self):
        """Test max Sharpe with custom constraints."""
        constraints = OptimizationConstraints(
            min_weight=0.1,  # At least 10% per asset
            max_weight=0.5   # At most 50% per asset
        )

        portfolio = self.optimizer.max_sharpe_ratio(rf_rate=0.05, constraints=constraints)

        # Check constraints respected
        for weight in portfolio.weights.values():
            assert weight >= 0.1 - 1e-6
            assert weight <= 0.5 + 1e-6

    def test_max_sharpe_different_rf_rates(self):
        """Test that different risk-free rates affect Sharpe ratio."""
        portfolio1 = self.optimizer.max_sharpe_ratio(rf_rate=0.03)
        portfolio2 = self.optimizer.max_sharpe_ratio(rf_rate=0.05)

        # Higher rf_rate should result in lower Sharpe (same numerator, higher denominator effect)
        # Weights might differ
        assert portfolio1.sharpe_ratio != portfolio2.sharpe_ratio

    # ========================================================================
    # Min Volatility
    # ========================================================================

    def test_min_volatility_portfolio(self):
        """Test computing minimum volatility portfolio."""
        portfolio = self.optimizer.min_volatility()

        assert portfolio is not None

        # Weights sum to 1
        total_weight = sum(portfolio.weights.values())
        assert abs(total_weight - 1.0) < 1e-4

        # Volatility is positive
        assert portfolio.volatility > 0

    def test_min_vol_has_lowest_volatility(self):
        """Test that min vol portfolio has lowest risk."""
        min_vol_portfolio = self.optimizer.min_volatility()
        max_sharpe_portfolio = self.optimizer.max_sharpe_ratio(rf_rate=0.05)

        # Min vol should have lower or equal volatility
        assert min_vol_portfolio.volatility <= max_sharpe_portfolio.volatility + 1e-4

    def test_min_volatility_with_constraints(self):
        """Test min volatility with constraints."""
        constraints = OptimizationConstraints(min_weight=0.2, max_weight=0.6)

        portfolio = self.optimizer.min_volatility(constraints=constraints)

        # Check constraints
        for weight in portfolio.weights.values():
            assert weight >= 0.2 - 1e-6
            assert weight <= 0.6 + 1e-6

    # ========================================================================
    # Efficient Frontier
    # ========================================================================

    def test_efficient_frontier_generation(self):
        """Test generating efficient frontier."""
        frontier = compute_efficient_frontier(self.returns, n_points=10, rf_rate=0.05)

        assert frontier is not None
        assert len(frontier) == 10
        assert all(isinstance(p, Portfolio) for p in frontier)

    def test_frontier_monotonic_risk_return(self):
        """Test that frontier shows monotonic risk-return relationship."""
        frontier = compute_efficient_frontier(self.returns, n_points=20, rf_rate=0.05)

        # Sort by volatility
        frontier_sorted = sorted(frontier, key=lambda p: p.volatility)

        # Returns should generally increase with risk (may have small violations)
        returns = [p.expected_return for p in frontier_sorted]

        # Check that return trend is mostly increasing
        increasing_count = sum(1 for i in range(len(returns)-1) if returns[i+1] >= returns[i] - 1e-6)
        assert increasing_count >= len(returns) * 0.8  # 80% monotonic

    def test_frontier_contains_min_vol(self):
        """Test that efficient frontier contains min volatility portfolio."""
        min_vol = self.optimizer.min_volatility()
        frontier = compute_efficient_frontier(self.returns, n_points=20, rf_rate=0.05)

        # Min vol should be approximately on frontier (within tolerance)
        min_frontier_vol = min(p.volatility for p in frontier)

        assert abs(min_vol.volatility - min_frontier_vol) < 0.05  # Within 5% tolerance

    # ========================================================================
    # Expected Return & Volatility Calculation
    # ========================================================================

    def test_portfolio_metrics_calculation(self):
        """Test that portfolio metrics are calculated correctly."""
        # Equal weight portfolio
        weights = {"AAPL": 1/3, "MSFT": 1/3, "GOOGL": 1/3}

        portfolio = self.optimizer._compute_portfolio_metrics(weights, rf_rate=0.05)

        assert portfolio.expected_return > 0
        assert portfolio.volatility > 0
        assert portfolio.sharpe_ratio is not None

    def test_metrics_match_manual_calculation(self):
        """Test metrics match manual calculation."""
        # Simple case: 100% in first asset
        weights = {"AAPL": 1.0, "MSFT": 0.0, "GOOGL": 0.0}

        portfolio = self.optimizer._compute_portfolio_metrics(weights, rf_rate=0.05)

        # Manual calculation
        mean_return = self.returns['AAPL'].mean() * 252
        volatility = self.returns['AAPL'].std() * np.sqrt(252)

        assert abs(portfolio.expected_return - mean_return) < 1e-6
        assert abs(portfolio.volatility - volatility) < 1e-6

    # ========================================================================
    # Constraint Validation
    # ========================================================================

    def test_validates_constraints(self):
        """Test that constraints are validated."""
        # Invalid constraints (min > max)
        constraints = OptimizationConstraints(min_weight=0.5, max_weight=0.3)

        with pytest.raises(ValueError):
            self.optimizer.max_sharpe_ratio(rf_rate=0.05, constraints=constraints)

    def test_sum_weights_constraint(self):
        """Test that weights always sum to constraint value."""
        portfolio = self.optimizer.max_sharpe_ratio(rf_rate=0.05)

        total = sum(portfolio.weights.values())
        assert abs(total - 1.0) < 1e-4

    # ========================================================================
    # Edge Cases
    # ========================================================================

    def test_handles_single_asset(self):
        """Test handling of single asset portfolio."""
        # Single asset returns
        single_returns = pd.DataFrame({
            'AAPL': np.random.normal(0.001, 0.02, 252)
        })

        optimizer = PortfolioOptimizer(single_returns)
        portfolio = optimizer.max_sharpe_ratio(rf_rate=0.05)

        # Should have 100% in single asset
        assert abs(portfolio.weights['AAPL'] - 1.0) < 1e-6

    def test_handles_negative_returns(self):
        """Test handling when assets have negative returns."""
        # Create returns with negative mean
        negative_returns = pd.DataFrame({
            'A': np.random.normal(-0.001, 0.02, 252),
            'B': np.random.normal(-0.0005, 0.015, 252),
            'C': np.random.normal(0.0001, 0.01, 252)  # One positive
        })

        optimizer = PortfolioOptimizer(negative_returns)
        portfolio = optimizer.max_sharpe_ratio(rf_rate=0.05)

        # Should still find solution (might be all in least negative asset)
        assert portfolio is not None
        assert sum(portfolio.weights.values()) <= 1.0 + 1e-4


# ============================================================================
# Integration Tests
# ============================================================================

class TestPortfolioIntegration:
    """Integration tests for portfolio optimization."""

    def test_real_world_portfolio(self):
        """Test optimization with realistic market data."""
        # Simulate realistic returns (based on historical means/vols)
        np.random.seed(123)
        dates = pd.date_range('2023-01-01', periods=252, freq='D')

        returns = pd.DataFrame({
            'SPY': np.random.normal(0.0004, 0.01, 252),   # S&P 500
            'QQQ': np.random.normal(0.0006, 0.015, 252),  # Nasdaq
            'GLD': np.random.normal(0.0001, 0.012, 252),  # Gold
            'TLT': np.random.normal(0.0002, 0.008, 252)   # Bonds
        }, index=dates)

        optimizer = PortfolioOptimizer(returns)

        # Compute portfolios
        max_sharpe = optimizer.max_sharpe_ratio(rf_rate=0.05)
        min_vol = optimizer.min_volatility()
        frontier = compute_efficient_frontier(returns, n_points=10, rf_rate=0.05)

        # Sanity checks
        assert max_sharpe.sharpe_ratio >= min_vol.sharpe_ratio - 1e-6
        assert min_vol.volatility <= max_sharpe.volatility + 1e-4
        assert len(frontier) == 10

    def test_optimization_reproducibility(self):
        """Test that optimization is reproducible."""
        np.random.seed(456)
        returns = pd.DataFrame({
            'A': np.random.normal(0.001, 0.02, 252),
            'B': np.random.normal(0.0008, 0.015, 252)
        })

        optimizer = PortfolioOptimizer(returns)

        portfolio1 = optimizer.max_sharpe_ratio(rf_rate=0.05)
        portfolio2 = optimizer.max_sharpe_ratio(rf_rate=0.05)

        # Should get identical results
        for ticker in portfolio1.weights:
            assert abs(portfolio1.weights[ticker] - portfolio2.weights[ticker]) < 1e-6
