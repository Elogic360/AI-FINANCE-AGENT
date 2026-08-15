"""initial_schema_all_12_tables

Revision ID: 5a03996fd887
Revises: 
Create Date: 2026-08-15 14:06:39.538705
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '5a03996fd887'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Parent tables (no FK dependencies) ───────────────────────────
    op.create_table(
        'businesses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('country', sa.String(length=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── 2. Direct children of businesses ────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.Text(), nullable=False),
        sa.Column('hashed_password', sa.Text(), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_users_business_id', 'users', ['business_id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table(
        'chart_of_accounts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('account_type', sa.Text(), nullable=False),
        sa.Column('parent_id', sa.UUID(), nullable=True),
        sa.CheckConstraint("account_type IN ('asset','liability','equity','revenue','expense')"),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_chart_of_accounts_business_id', 'chart_of_accounts', ['business_id'])

    op.create_table(
        'documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('file_type', sa.Text(), nullable=False),
        sa.Column('storage_url', sa.Text(), nullable=False),
        sa.Column('original_filename', sa.Text(), nullable=False),
        sa.Column('parsed_by', sa.Text(), nullable=True),
        sa.Column('parse_status', sa.Text(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint("parse_status IN ('pending','parsed','failed','needs_review')"),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_documents_business_id', 'documents', ['business_id'])

    op.create_table(
        'customers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_customers_business_id', 'customers', ['business_id'])

    op.create_table(
        'vendors',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_vendors_business_id', 'vendors', ['business_id'])

    op.create_table(
        'transactions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=True),
        sa.Column('txn_date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('counterparty', sa.Text(), nullable=True),
        sa.Column('ai_category', sa.Text(), nullable=True),
        sa.Column('ai_confidence', sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('pending','categorized','posted','flagged')"),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_transactions_business_id', 'transactions', ['business_id'])

    op.create_table(
        'forecasts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('forecast_type', sa.Text(), nullable=False),
        sa.Column('horizon_days', sa.Integer(), nullable=False),
        sa.Column('input_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence', sa.Text(), nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint("confidence IN ('high','medium','low')"),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_forecasts_business_id', 'forecasts', ['business_id'])

    op.create_table(
        'alerts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('severity', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('detail', sa.Text(), nullable=False),
        sa.Column('source_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('acknowledged', sa.Boolean(), nullable=False),
        sa.CheckConstraint("severity IN ('info','warning','critical')"),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_alerts_business_id', 'alerts', ['business_id'])

    op.create_table(
        'audit_log',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('actor', sa.Text(), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('target_table', sa.Text(), nullable=True),
        sa.Column('target_id', sa.UUID(), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_audit_log_business_id', 'audit_log', ['business_id'])

    # ── 3. Second-level children ────────────────────────────────────────
    op.create_table(
        'extracted_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('record_type', sa.Text(), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column('validation_status', sa.Text(), nullable=False),
        sa.Column('validation_notes', sa.Text(), nullable=True),
        sa.CheckConstraint("validation_status IN ('unvalidated','valid','inconsistent','needs_human_review')"),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_extracted_records_document_id', 'extracted_records', ['document_id'])

    op.create_table(
        'invoices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('customer_id', sa.UUID(), nullable=True),
        sa.Column('document_id', sa.UUID(), nullable=True),
        sa.Column('invoice_number', sa.Text(), nullable=True),
        sa.Column('issue_date', sa.Date(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('subtotal', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('tax', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('total', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.CheckConstraint("status IN ('draft','unpaid','paid','overdue','void')"),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_invoices_business_id', 'invoices', ['business_id'])
    op.create_index('ix_invoices_customer_id', 'invoices', ['customer_id'])

    op.create_table(
        'bills',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('vendor_id', sa.UUID(), nullable=True),
        sa.Column('document_id', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_bills_business_id', 'bills', ['business_id'])
    op.create_index('ix_bills_vendor_id', 'bills', ['vendor_id'])

    op.create_table(
        'journal_entries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('transaction_id', sa.UUID(), nullable=True),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('memo', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Text(), nullable=False),
        sa.Column('is_draft', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_journal_entries_business_id', 'journal_entries', ['business_id'])
    op.create_index('ix_journal_entries_transaction_id', 'journal_entries', ['transaction_id'])

    # ── 4. Third-level children ─────────────────────────────────────────
    op.create_table(
        'journal_lines',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('journal_entry_id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('debit', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('credit', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.CheckConstraint('debit >= 0 AND credit >= 0'),
        sa.CheckConstraint('NOT (debit > 0 AND credit > 0)'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['journal_entry_id'], ['journal_entries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['account_id'], ['chart_of_accounts.id'], ondelete='RESTRICT'),
    )
    op.create_index('ix_journal_lines_journal_entry_id', 'journal_lines', ['journal_entry_id'])
    op.create_index('ix_journal_lines_account_id', 'journal_lines', ['account_id'])


def downgrade() -> None:
    op.drop_table('journal_lines')
    op.drop_table('journal_entries')
    op.drop_table('bills')
    op.drop_table('invoices')
    op.drop_table('extracted_records')
    op.drop_table('audit_log')
    op.drop_table('alerts')
    op.drop_table('forecasts')
    op.drop_table('transactions')
    op.drop_table('vendors')
    op.drop_table('customers')
    op.drop_table('documents')
    op.drop_table('chart_of_accounts')
    op.drop_table('users')
    op.drop_table('businesses')
