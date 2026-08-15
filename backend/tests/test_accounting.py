"""
FinPilot AI — Accounting Service Tests
───────────────────────────────────────
Tests for journal entry creation, balance enforcement,
trial balance, and profit & loss calculations.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio

from app.models.accounting import ChartOfAccounts
from app.services.accounting_service import create_journal_entry
from app.services.reports_service import get_profit_loss, get_trial_balance


@pytest_asyncio.fixture
async def chart_of_accounts(db_session, test_business):
    """Seed a minimal chart of accounts for the test business."""
    accounts = [
        ChartOfAccounts(
            business_id=test_business.id,
            code="1000",
            name="Cash",
            account_type="asset",
        ),
        ChartOfAccounts(
            business_id=test_business.id,
            code="4000",
            name="Sales Revenue",
            account_type="revenue",
        ),
        ChartOfAccounts(
            business_id=test_business.id,
            code="5000",
            name="Rent Expense",
            account_type="expense",
        ),
        ChartOfAccounts(
            business_id=test_business.id,
            code="3000",
            name="Owner Equity",
            account_type="equity",
        ),
    ]
    for acct in accounts:
        db_session.add(acct)
    await db_session.flush()
    return {acct.code: acct for acct in accounts}


@pytest.mark.asyncio
async def test_create_journal_entry(db_session, test_business, chart_of_accounts):
    """Creating a balanced journal entry succeeds and returns the entry."""
    cash = chart_of_accounts["1000"]
    revenue = chart_of_accounts["4000"]

    entry = await create_journal_entry(
        db_session,
        business_id=test_business.id,
        entry_date=date(2025, 1, 15),
        lines=[
            {"account_id": cash.id, "debit": Decimal("500000"), "credit": Decimal("0")},
            {"account_id": revenue.id, "debit": Decimal("0"), "credit": Decimal("500000")},
        ],
        memo="Sales received in cash",
    )

    assert entry.id is not None
    assert entry.business_id == test_business.id
    assert entry.is_draft is False
    assert len(entry.lines) == 2


@pytest.mark.asyncio
async def test_journal_entry_unbalanced_raises(db_session, test_business, chart_of_accounts):
    """Creating an unbalanced journal entry raises ValueError."""
    cash = chart_of_accounts["1000"]
    revenue = chart_of_accounts["4000"]

    with pytest.raises(ValueError, match="Debit-Credit imbalance"):
        await create_journal_entry(
            db_session,
            business_id=test_business.id,
            entry_date=date(2025, 1, 15),
            lines=[
                {"account_id": cash.id, "debit": Decimal("500000"), "credit": Decimal("0")},
                {"account_id": revenue.id, "debit": Decimal("0"), "credit": Decimal("300000")},
            ],
        )


@pytest.mark.asyncio
async def test_journal_entry_too_few_lines_raises(db_session, test_business, chart_of_accounts):
    """A journal entry with fewer than 2 lines raises ValueError."""
    cash = chart_of_accounts["1000"]

    with pytest.raises(ValueError, match="at least two lines"):
        await create_journal_entry(
            db_session,
            business_id=test_business.id,
            entry_date=date(2025, 1, 15),
            lines=[
                {"account_id": cash.id, "debit": Decimal("100"), "credit": Decimal("0")},
            ],
        )


@pytest.mark.asyncio
async def test_get_trial_balance(db_session, test_business, chart_of_accounts):
    """Trial balance totals are equal after balanced journal entries."""
    cash = chart_of_accounts["1000"]
    revenue = chart_of_accounts["4000"]
    expense = chart_of_accounts["5000"]

    # Entry 1: Revenue
    await create_journal_entry(
        db_session,
        business_id=test_business.id,
        entry_date=date(2025, 1, 15),
        lines=[
            {"account_id": cash.id, "debit": Decimal("1000000"), "credit": Decimal("0")},
            {"account_id": revenue.id, "debit": Decimal("0"), "credit": Decimal("1000000")},
        ],
    )

    # Entry 2: Expense
    await create_journal_entry(
        db_session,
        business_id=test_business.id,
        entry_date=date(2025, 1, 20),
        lines=[
            {"account_id": expense.id, "debit": Decimal("200000"), "credit": Decimal("0")},
            {"account_id": cash.id, "debit": Decimal("0"), "credit": Decimal("200000")},
        ],
    )

    await db_session.commit()

    tb = await get_trial_balance(test_business.id, db=db_session)

    assert tb["balanced"] is True
    assert tb["total_debits"] == tb["total_credits"]


@pytest.mark.asyncio
async def test_profit_loss(db_session, test_business, chart_of_accounts):
    """Profit & Loss correctly calculates net income."""
    cash = chart_of_accounts["1000"]
    revenue = chart_of_accounts["4000"]
    expense = chart_of_accounts["5000"]

    # Revenue entry: 1,000,000 TZS
    await create_journal_entry(
        db_session,
        business_id=test_business.id,
        entry_date=date(2025, 2, 1),
        lines=[
            {"account_id": cash.id, "debit": Decimal("1000000"), "credit": Decimal("0")},
            {"account_id": revenue.id, "debit": Decimal("0"), "credit": Decimal("1000000")},
        ],
    )

    # Expense entry: 300,000 TZS
    await create_journal_entry(
        db_session,
        business_id=test_business.id,
        entry_date=date(2025, 2, 10),
        lines=[
            {"account_id": expense.id, "debit": Decimal("300000"), "credit": Decimal("0")},
            {"account_id": cash.id, "debit": Decimal("0"), "credit": Decimal("300000")},
        ],
    )

    await db_session.commit()

    pnl = await get_profit_loss(
        business_id=test_business.id,
        start_date=date(2025, 2, 1),
        end_date=date(2025, 2, 28),
        db=db_session,
    )

    assert pnl["revenue"] == Decimal("1000000")
    assert pnl["net_income"] == Decimal("700000")
