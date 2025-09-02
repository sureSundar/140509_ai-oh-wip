"""initial schema

Revision ID: 0001_init
Revises: 
Create Date: 2025-08-28 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'transactions',
        sa.Column('transaction_id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_id', sa.String(50), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('merchant_id', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('latitude', sa.Numeric(10, 8)),
        sa.Column('longitude', sa.Numeric(11, 8)),
        sa.Column('device_fingerprint', sa.String(256)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('idx_transactions_customer_id', 'transactions', ['customer_id', 'timestamp'], unique=False)
    op.create_index('idx_transactions_merchant_id', 'transactions', ['merchant_id', 'timestamp'], unique=False)

    op.create_table(
        'decisions',
        sa.Column('transaction_id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('decision', sa.String(20), nullable=False),
        sa.Column('risk_score', sa.Integer, nullable=False),
        sa.Column('explanation', sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.transaction_id'], name='fk_decisions_tx'),
    )


def downgrade() -> None:
    op.drop_table('decisions')
    op.drop_index('idx_transactions_merchant_id', table_name='transactions')
    op.drop_index('idx_transactions_customer_id', table_name='transactions')
    op.drop_table('transactions')

