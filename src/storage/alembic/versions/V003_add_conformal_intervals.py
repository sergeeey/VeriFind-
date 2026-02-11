"""Add Conformal Prediction intervals to predictions table

Revision ID: 003
Revises: 002
Create Date: 2026-02-11

Week 13 Day 2: Add prediction intervals from Conformal Prediction.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Conformal Prediction interval columns."""
    # Add conformal prediction interval columns
    op.add_column('predictions', sa.Column('lower_bound', sa.Numeric(12, 4), nullable=True))
    op.add_column('predictions', sa.Column('upper_bound', sa.Numeric(12, 4), nullable=True))
    op.add_column('predictions', sa.Column('interval_width', sa.Numeric(12, 4), nullable=True))
    op.add_column('predictions', sa.Column('coverage_level', sa.Float, nullable=True, server_default='0.95'))
    op.add_column('predictions', sa.Column('conformal_method', sa.String(50), nullable=True))

    # Add CHECK constraint: lower_bound <= upper_bound
    op.create_check_constraint(
        'check_conformal_bounds',
        'predictions',
        'lower_bound IS NULL OR upper_bound IS NULL OR lower_bound <= upper_bound'
    )

    # Add CHECK constraint: coverage_level in (0, 1)
    op.create_check_constraint(
        'check_coverage_level_range',
        'predictions',
        'coverage_level IS NULL OR (coverage_level > 0 AND coverage_level < 1)'
    )

    # Create index for queries filtering by interval width
    op.create_index(
        'idx_predictions_interval_width',
        'predictions',
        ['interval_width'],
        postgresql_where=sa.text('interval_width IS NOT NULL')
    )


def downgrade() -> None:
    """Remove Conformal Prediction interval columns."""
    # Drop index
    op.drop_index('idx_predictions_interval_width', table_name='predictions')

    # Drop constraints
    op.drop_constraint('check_coverage_level_range', 'predictions', type_='check')
    op.drop_constraint('check_conformal_bounds', 'predictions', type_='check')

    # Drop columns
    op.drop_column('predictions', 'conformal_method')
    op.drop_column('predictions', 'coverage_level')
    op.drop_column('predictions', 'interval_width')
    op.drop_column('predictions', 'upper_bound')
    op.drop_column('predictions', 'lower_bound')
