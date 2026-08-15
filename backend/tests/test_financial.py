"""
FinPilot AI — Financial Intelligence Tests
───────────────────────────────────────────
Tests for health score calculation, risk detection, and metrics.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest
import pytest_asyncio

from app.models.accounting import ChartOfAccounts
from app.services.accounting_service import (
    categorise_transaction,
    create_journal_entry,
)
from app.services.reports_service import (
    get_balance_sheet,
    get_profit_loss,
    get_trial_balance,
)
from app.models.accounting import Transaction


@pytest_asyncio.fixture
async def financial_accounts(db_session, test_business):
    """Seed a fuller chart of accounts for financial tests."""
    accounts = [
        ChartOfAccounts(business_id=test_business.id, code="1000", name="Cash", account_type="asset"),
        ChartOfAccounts(business_id=test_business.id, code="1100", name="Accounts Receivable", account_type="asset"),
        ChartOfAccounts(business_id=test_business.id, code="2000", name="Accounts Payable", account_type="liability"),
        ChartOfAccounts(business_id=test_business.id, code="2100", name="Loan Payable", account_type="liability"),
        ChartOfAccounts(business_id=test_business.id, code="3000", name="Owner Equity", account_type="equity"),
        ChartOfAccounts(business_id=test_business.id, code="4000", name="Sales Revenue", account_type="revenue"),
        ChartOfAccounts(business_id=test_business.id, code="5000", name="Rent Expense", account_type="expense"),
        ChartOfAccounts(business_id=test_business.id, code="5100", name="Utilities Expense", account_type="expense"),
    ]
    for acct in accounts:
        db_session.add(acct)
    await db_session.flush()
    return {acct.code: acct for acct in accounts}


@pytest.mark.asyncio
async def test_health_score_balance_sheet(db_session, test_business, financial_accounts):
    """Balance sheet satisfies the accounting equation: Assets = Liabilities + Equity."""
    accts = financial_accounts

    # Inject cash from equity (owner investment)
    await create_journal_entry(
        db_session,
        business_id=test_business.id,
        entry_date=date(2025, 1, 1),
        lines=[
            {"account_id": accts["1000"].id, "debit": Decimal("5000000"), "credit": Decimal("0")},
            {"account_id": accts["3000"].id, "debit": Decimal("0"), "credit": Decimal("5000000")},
        ],
        memo="Owner investment",
    )

    # Recognize revenue
    await create_journal_entry(
        db_session,
        business_id=test_business.id,
        entry_date=date(2025, 1, 15),
        lines=[
            {"account_id": accts["1000"].id, "debit": Decimal("2000000"), "credit": Decimal("0")},
            {"account_id": accts["4000"].id, "debit": Decimal("0"), "credit": Decimal("2000000")},
        ],
        memo="Sales",
    )

    # Record expense
    await create_journal_entry(
        db_session,
        business_id=test_business.id,
        entry_date=date(2025, 1, 20),
        lines=[
            {"account_id": accts["5000"].id, "debit": Decimal("500000"), "credit": Decimal("0")},
            {"account_id": accts["1000"].id, "debit": Decimal("0"), "credit": Decimal("500000")},
        ],
        memo="Rent payment",
    )

    await db_session.commit()

    bs = await get_balance_sheet(
        business_id=test_business.id,
        as_of_date=date(2025, 1, 31),
        db=db_session,
    )

    # Verify accounting equation
    assert bs["check"]["balanced"] is True


@pytest.mark.asyncio
async def test_risk_detection_keyword_categorisation():
    """Transaction categorisation correctly flags risk-related keywords."""
    txn = Transaction(
        business_id=uuid.uuid4(),
        source="manual",
        txn_date=date(2025, 3, 1),
        description="Late loan interest payment",
        amount=Decimal("100000"),
        currency="TZS",
        counterparty="Bank of Tanzania",
        status="pending",
    )

    category = categorise_transaction(txn)
    assert category != "uncategorized"
    assert txn.ai_confidence > 0


@pytest.mark.asyncio
async def test_metrics_calculation_trial_balance(db_session, test_business, financial_accounts):
    """Trial balance metrics are consistent after multiple entries."""
    accts = financial_accounts

    entries_data = [
        # Owner invests 5M
        (date(2025, 1, 1), [
            {"account_id": accts["1000"].id, "debit": Decimal("5000000"), "credit": Decimal("0")},
            {"account_id": accts["3000"].id, "debit": Decimal("0"), "credit": Decimal("5000000")},
        ]),
        # Revenue 2M
        (date(2025, 1, 15), [
            {"account_id": accts["1000"].id, "debit": Decimal("2000000"), "credit": Decimal("0")},
            {"account_id": accts["4000"].id, "debit": Decimal("0"), "credit": Decimal("2000000")},
        ]),
        # Rent expense 500K
        (date(2025, 1, 20), [
            {"account_id": accts["5000"].id, "debit": Decimal("500000"), "credit": Decimal("0")},
            {"account_id": accts["1000"].id, "debit": Decimal("0"), "credit": Decimal("500000")},
        ]),
        # Utilities 200K
        (date(2025, 1, 25), [
            {"account_id": accts["5100"].id, "debit": Decimal("200000"), "credit": Decimal("0")},
            {"account_id": accts["1000"].id, "debit": Decimal("0"), "credit": Decimal("200000")},
        ]),
    ]

    for entry_date, lines in entries_data:
        await create_journal_entry(
            db_session,
            business_id=test_business.id,
            entry_date=entry_date,
            lines=lines,
        )

    await db_session.commit()

    tb = await get_trial_balance(test_business.id, db=db_session)

    assert tb["balanced"] is True
    # Total debits should be 5M + 2M + 500K + 200K = 7,700,000
    assert tb["total_debits"] == Decimal("7700000")
    assert tb["total_credits"] == Decimal("7700000")
