"""
CSV Snapshot Adapter — Last resort fallback for market data.

Week 13 Day 3: Production fallback when all external APIs fail.

Use case:
- YFinance down
- Finnhub free tier = no historical data
- Alpha Vantage requires separate registration

Solution:
- Pre-downloaded CSV snapshots in data/snapshots/
- Updated manually or via cron job
- Logged as "USING CACHED DATA" warning

Trade-offs:
- ✅ System never returns empty data
- ✅ No external dependencies
- ⚠️  Data may be stale (document freshness)
- ⚠️  Limited tickers (add as needed)

Production plan:
- Beta: Acceptable (documented limitation)
- Production: Migrate to paid API (Polygon.io $199/mo)
"""

import pandas as pd
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CSVSnapshotAdapter:
    """Fallback adapter reading pre-downloaded CSV snapshots."""

    def __init__(self, snapshots_dir: Optional[Path] = None):
        """
        Initialize CSV snapshot adapter.

        Args:
            snapshots_dir: Directory containing CSV snapshots
                           Default: project_root/data/snapshots/
        """
        if snapshots_dir is None:
            # Default to data/snapshots relative to project root
            project_root = Path(__file__).parent.parent.parent
            snapshots_dir = project_root / 'data' / 'snapshots'

        self.snapshots_dir = Path(snapshots_dir)

        if not self.snapshots_dir.exists():
            logger.warning(f"Snapshots directory not found: {self.snapshots_dir}")

    def fetch_ohlcv(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        interval: str = '1d'
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV from CSV snapshot.

        Args:
            ticker: Stock ticker
            start_date: Start date (YYYY-MM-DD) — used for filtering
            end_date: End date (YYYY-MM-DD) — used for filtering
            interval: Ignored (snapshots are daily only)

        Returns:
            DataFrame with OHLCV data (or None if not found)
        """
        csv_path = self.snapshots_dir / f"{ticker}_snapshot.csv"

        if not csv_path.exists():
            logger.warning(f"CSV snapshot not found for {ticker}: {csv_path}")
            return None

        try:
            logger.warning(
                f"⚠️  USING CACHED DATA for {ticker} from CSV snapshot. "
                f"Data may be stale. Check {csv_path.name} for last update."
            )

            df = pd.read_csv(csv_path)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df.sort_index(inplace=True)

            # Filter by date range (if provided)
            # BUT if no rows match, return ALL data (better than nothing)
            if start_date and end_date:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                filtered = df[(df.index >= start_dt) & (df.index <= end_dt)]

                if filtered.empty:
                    logger.warning(
                        f"CSV snapshot for {ticker}: No data in requested range "
                        f"({start_date} to {end_date}). Returning ALL snapshot data."
                    )
                else:
                    df = filtered

            logger.info(f"CSV snapshot loaded for {ticker}: {len(df)} rows")
            return df

        except Exception as e:
            logger.error(f"Failed to load CSV snapshot for {ticker}: {e}")
            return None

    def get_available_tickers(self) -> list[str]:
        """
        List available ticker snapshots.

        Returns:
            List of ticker symbols with available snapshots
        """
        if not self.snapshots_dir.exists():
            return []

        tickers = []
        for csv_file in self.snapshots_dir.glob("*_snapshot.csv"):
            ticker = csv_file.stem.replace("_snapshot", "")
            tickers.append(ticker)

        return sorted(tickers)
