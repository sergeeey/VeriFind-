"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial tables."""
    # Verified facts table
    op.create_table(
        'verified_facts',
        sa.Column('fact_id', sa.String(36), primary_key=True),
        sa.Column('query_id', sa.String(36), nullable=False),
        sa.Column('plan_id', sa.String(36), nullable=False),
        sa.Column('code_hash', sa.String(64), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('extracted_values', postgresql.JSONB, default={}),
        sa.Column('execution_time_ms', sa.Integer),
        sa.Column('memory_used_mb', sa.Float),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('error_message', sa.Text),
        sa.Column('source_code', sa.Text),
        sa.Column('confidence_score', sa.Float, default=1.0),
        sa.Column('data_source', sa.String(50), default='yfinance'),
        sa.Column('data_freshness', sa.DateTime(timezone=True)),
    )
    
    # Indexes
    op.create_index('idx_verified_facts_query_id', 'verified_facts', ['query_id'])
    op.create_index('idx_verified_facts_created_at', 'verified_facts', ['created_at'])
    op.create_index('idx_verified_facts_data_source', 'verified_facts', ['data_source', 'created_at'])
    
    # API costs table
    op.create_table(
        'api_costs',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('query_id', sa.String(36), nullable=False),
        sa.Column('model', sa.String(50), nullable=False),
        sa.Column('input_tokens', sa.Integer),
        sa.Column('output_tokens', sa.Integer),
        sa.Column('total_tokens', sa.Integer),
        sa.Column('cost_usd', sa.Numeric(10, 6)),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    op.create_index('idx_api_costs_query_id', 'api_costs', ['query_id'])
    op.create_index('idx_api_costs_timestamp', 'api_costs', ['timestamp'])


def downgrade() -> None:
    """Drop tables."""
    op.drop_table('api_costs')
    op.drop_table('verified_facts')
