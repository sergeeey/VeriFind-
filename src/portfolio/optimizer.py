"""
Portfolio Optimization for APE 2026.

Week 10 Day 4: Modern Portfolio Theory (MPT) implementation.

Features:
- Maximum Sharpe ratio portfolio
- Minimum volatility portfolio
- Efficient frontier generation
- Constraint handling (min/max weights)
"""

import numpy as np
import pandas as pd
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Portfolio:
    """
    Portfolio with weights and metrics.

    Attributes:
        weights: Dict of ticker -> weight
        expected_return: Annualized expected return
        volatility: Annualized volatility (std dev)
        sharpe_ratio: Sharpe ratio (return - rf) / volatility
    """
    weights: Dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float


@dataclass
class OptimizationConstraints:
    """
    Constraints for portfolio optimization.

    Attributes:
        min_weight: Minimum weight per asset (default: 0.0 = long-only)
        max_weight: Maximum weight per asset (default: 1.0)
        sum_weights: Sum of weights constraint (default: 1.0 = fully invested)
    """
    min_weight: float = 0.0
    max_weight: float = 1.0
    sum_weights: float = 1.0


# ============================================================================
# Portfolio Optimizer
# ============================================================================

class PortfolioOptimizer:
    """
    Modern Portfolio Theory optimizer.

    Features:
    - Maximum Sharpe ratio portfolio
    - Minimum volatility portfolio
    - Constraint handling
    - Efficient frontier generation
    """

    def __init__(self, returns: pd.DataFrame):
        """
        Initialize optimizer.

        Args:
            returns: DataFrame of asset returns (rows=dates, cols=tickers)
        """
        self.returns = returns
        self.tickers = list(returns.columns)
        self.n_assets = len(self.tickers)

        # Pre-compute mean returns and covariance matrix (annualized)
        self.mean_returns = returns.mean() * 252  # Annualize daily returns
        self.cov_matrix = returns.cov() * 252     # Annualize covariance

    def max_sharpe_ratio(
        self,
        rf_rate: float = 0.0,
        constraints: Optional[OptimizationConstraints] = None
    ) -> Portfolio:
        """
        Compute maximum Sharpe ratio portfolio.

        Args:
            rf_rate: Risk-free rate (annualized)
            constraints: Optimization constraints

        Returns:
            Portfolio with maximum Sharpe ratio
        """
        if constraints is None:
            constraints = OptimizationConstraints()

        # Validate constraints
        self._validate_constraints(constraints)

        # Objective: Minimize negative Sharpe ratio
        def neg_sharpe_ratio(weights):
            portfolio_return = np.dot(weights, self.mean_returns)
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))

            if portfolio_vol == 0:
                return 1e10  # Avoid division by zero

            sharpe = (portfolio_return - rf_rate) / portfolio_vol
            return -sharpe  # Minimize negative = maximize positive

        # Initial guess: equal weights
        x0 = np.array([1.0 / self.n_assets] * self.n_assets)

        # Constraints
        cons = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - constraints.sum_weights}  # Sum = 1
        ]

        # Bounds
        bounds = tuple((constraints.min_weight, constraints.max_weight) for _ in range(self.n_assets))

        # Optimize
        result = minimize(
            neg_sharpe_ratio,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=cons,
            options={'maxiter': 1000}
        )

        if not result.success:
            logger.warning(f"Optimization did not converge: {result.message}")

        # Build portfolio
        weights_dict = {ticker: float(w) for ticker, w in zip(self.tickers, result.x)}
        return self._compute_portfolio_metrics(weights_dict, rf_rate)

    def min_volatility(
        self,
        constraints: Optional[OptimizationConstraints] = None
    ) -> Portfolio:
        """
        Compute minimum volatility portfolio.

        Args:
            constraints: Optimization constraints

        Returns:
            Portfolio with minimum volatility
        """
        if constraints is None:
            constraints = OptimizationConstraints()

        # Validate constraints
        self._validate_constraints(constraints)

        # Objective: Minimize volatility
        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))

        # Initial guess
        x0 = np.array([1.0 / self.n_assets] * self.n_assets)

        # Constraints
        cons = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - constraints.sum_weights}
        ]

        # Bounds
        bounds = tuple((constraints.min_weight, constraints.max_weight) for _ in range(self.n_assets))

        # Optimize
        result = minimize(
            portfolio_volatility,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=cons,
            options={'maxiter': 1000}
        )

        if not result.success:
            logger.warning(f"Optimization did not converge: {result.message}")

        # Build portfolio
        weights_dict = {ticker: float(w) for ticker, w in zip(self.tickers, result.x)}
        return self._compute_portfolio_metrics(weights_dict, rf_rate=0.0)

    def _compute_portfolio_metrics(
        self,
        weights: Dict[str, float],
        rf_rate: float = 0.0
    ) -> Portfolio:
        """
        Compute portfolio metrics from weights.

        Args:
            weights: Dict of ticker -> weight
            rf_rate: Risk-free rate

        Returns:
            Portfolio with computed metrics
        """
        # Convert weights to array
        weights_array = np.array([weights[ticker] for ticker in self.tickers])

        # Expected return
        expected_return = float(np.dot(weights_array, self.mean_returns))

        # Volatility
        volatility = float(np.sqrt(np.dot(weights_array.T, np.dot(self.cov_matrix, weights_array))))

        # Sharpe ratio
        if volatility > 0:
            sharpe_ratio = (expected_return - rf_rate) / volatility
        else:
            sharpe_ratio = 0.0

        return Portfolio(
            weights=weights,
            expected_return=expected_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio
        )

    def _validate_constraints(self, constraints: OptimizationConstraints):
        """
        Validate optimization constraints.

        Args:
            constraints: Constraints to validate

        Raises:
            ValueError: If constraints are invalid
        """
        if constraints.min_weight > constraints.max_weight:
            raise ValueError(
                f"min_weight ({constraints.min_weight}) > max_weight ({constraints.max_weight})"
            )

        if constraints.min_weight * self.n_assets > constraints.sum_weights:
            raise ValueError(
                f"Infeasible: min_weight * n_assets ({constraints.min_weight * self.n_assets}) "
                f"> sum_weights ({constraints.sum_weights})"
            )

        if constraints.max_weight * self.n_assets < constraints.sum_weights:
            raise ValueError(
                f"Infeasible: max_weight * n_assets ({constraints.max_weight * self.n_assets}) "
                f"< sum_weights ({constraints.sum_weights})"
            )


# ============================================================================
# Efficient Frontier
# ============================================================================

def compute_efficient_frontier(
    returns: pd.DataFrame,
    n_points: int = 100,
    rf_rate: float = 0.0,
    constraints: Optional[OptimizationConstraints] = None
) -> List[Portfolio]:
    """
    Compute efficient frontier.

    Strategy: Generate portfolios with target returns from min to max,
    minimizing volatility for each target return.

    Args:
        returns: DataFrame of asset returns
        n_points: Number of points on frontier
        rf_rate: Risk-free rate
        constraints: Optimization constraints

    Returns:
        List of Portfolio objects on efficient frontier
    """
    optimizer = PortfolioOptimizer(returns)

    if constraints is None:
        constraints = OptimizationConstraints()

    # Get min volatility and max Sharpe portfolios as bounds
    min_vol_portfolio = optimizer.min_volatility(constraints)
    max_sharpe_portfolio = optimizer.max_sharpe_ratio(rf_rate, constraints)

    # Target returns range from min vol return to max Sharpe return
    min_return = min_vol_portfolio.expected_return
    max_return = max_sharpe_portfolio.expected_return

    # If max < min (shouldn't happen), swap
    if max_return < min_return:
        min_return, max_return = max_return, min_return

    target_returns = np.linspace(min_return, max_return, n_points)

    frontier = []

    for target_return in target_returns:
        # Objective: Minimize volatility
        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(optimizer.cov_matrix, weights)))

        # Initial guess
        x0 = np.array([1.0 / optimizer.n_assets] * optimizer.n_assets)

        # Constraints: sum = 1 AND return = target
        cons = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - constraints.sum_weights},
            {'type': 'eq', 'fun': lambda w: np.dot(w, optimizer.mean_returns) - target_return}
        ]

        # Bounds
        bounds = tuple((constraints.min_weight, constraints.max_weight) for _ in range(optimizer.n_assets))

        # Optimize
        result = minimize(
            portfolio_volatility,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=cons,
            options={'maxiter': 1000}
        )

        if result.success:
            weights_dict = {ticker: float(w) for ticker, w in zip(optimizer.tickers, result.x)}
            portfolio = optimizer._compute_portfolio_metrics(weights_dict, rf_rate)
            frontier.append(portfolio)

    return frontier
