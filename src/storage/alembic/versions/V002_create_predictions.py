"""Create predictions table

Revision ID: 002
Revises: 001
Create Date: 2026-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create predictions table with TimescaleDB hypertable."""
    # Create predictions table
    op.create_table(
        'predictions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),

        # Ticker & Exchange
        sa.Column('ticker', sa.String(20), nullable=False),
        sa.Column('exchange', sa.String(20), nullable=False, server_default='US'),

        # Prediction metadata
        sa.Column('horizon_days', sa.Integer, nullable=False),
        sa.Column('target_date', sa.Date, nullable=False),

        # Price corridor (at creation)
        sa.Column('price_at_creation', sa.Numeric(12, 4), nullable=False),
        sa.Column('price_low', sa.Numeric(12, 4), nullable=False),
        sa.Column('price_base', sa.Numeric(12, 4), nullable=False),
        sa.Column('price_high', sa.Numeric(12, 4), nullable=False),

        # Reasoning & metadata
        sa.Column('reasoning', postgresql.JSONB, nullable=False),
        sa.Column('verification_score', sa.Float, nullable=False),
        sa.Column('model_used', sa.String(50), nullable=False),
        sa.Column('pipeline_cost', sa.Numeric(10, 6), nullable=False),

        # Actual results (filled later)
        sa.Column('actual_price', sa.Numeric(12, 4), nullable=True),
        sa.Column('actual_date', sa.Date, nullable=True),
        sa.Column('accuracy_band', sa.String(10), nullable=True),
        sa.Column('error_pct', sa.Float, nullable=True),
        sa.Column('error_direction', sa.String(10), nullable=True),

        # Calibration
        sa.Column('was_calibrated', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('calibration_adj', sa.Float, nullable=True),

        # CHECK constraints
        sa.CheckConstraint('price_low <= price_base', name='check_low_lte_base'),
        sa.CheckConstraint('price_base <= price_high', name='check_base_lte_high'),
        sa.CheckConstraint('horizon_days > 0', name='check_positive_horizon'),
        sa.CheckConstraint('verification_score >= 0 AND verification_score <= 1', name='check_verification_score_range'),
        sa.CheckConstraint(
            "accuracy_band IS NULL OR accuracy_band IN ('HIT', 'NEAR', 'MISS')",
            name='check_accuracy_band_values'
        ),
        sa.CheckConstraint(
            "error_direction IS NULL OR error_direction IN ('OVER', 'UNDER', 'EXACT')",
            name='check_error_direction_values'
        ),
    )

    # Create indexes (before hypertable conversion)
    op.create_index('idx_predictions_ticker_created', 'predictions', ['ticker', sa.text('created_at DESC')])
    op.create_index('idx_predictions_target_pending', 'predictions', ['target_date'], postgresql_where=sa.text('actual_price IS NULL'))
    op.create_index('idx_predictions_exchange', 'predictions', ['exchange'])
    op.create_index('idx_predictions_model', 'predictions', ['model_used'])

    # Convert to TimescaleDB hypertable
    op.execute("""
        SELECT create_hypertable(
            'predictions',
            'created_at',
            chunk_time_interval => INTERVAL '1 month',
            if_not_exists => TRUE
        );
    """)


def downgrade() -> None:
    """Drop predictions table."""
    # Drop hypertable (will also drop chunks)
    op.execute("DROP TABLE IF EXISTS predictions CASCADE;")
