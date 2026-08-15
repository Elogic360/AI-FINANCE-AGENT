"""
FinPilot AI — Reports Service
──────────────────────────────
Standard financial reports built exclusively from ``journal_lines``:

* Profit & Loss  (Income Statement)
* Balance Sheet  (Statement of Financial Position)
* Cash Flow Statement  (indirect method)
* Trial Balance

All monetary values use Python ``Decimal`` — never ``float``.
Double-entry sign convention:
    asset / expense                → debit-positive  (balance = debits − credits)
    liability / equity / revenue   → credit-positive (balance = credits − debits)
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import (
    ChartOfAccounts,
    JournalEntry,
    JournalLine,
)


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _to_decimal(value: Any) -> Decimal:
    """Safely coerce *value* to ``Decimal``."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Cannot convert {value!r} to Decimal")


# Sign convention: for display purposes, revenue and expense balances
# are shown as positive values.  Liability/equity/asset balances follow
# their natural sign convention (credit-normal → positive when credit > debit).
_CREDIT_NORMAL_TYPES = frozenset({"liability", "equity", "revenue"})


def _balance_for_display(
    total_debit: Decimal,
    total_credit: Decimal,
    account_type: str,
) -> Decimal:
    """
    Return the display balance for an account.

    - For debit-normal accounts (asset, expense): return debit − credit
      (positive = normal balance).
    - For credit-normal accounts (liability, equity, revenue): return
      credit − debit (positive = normal balance).
    """
    if account_type in _CREDIT_NORMAL_TYPES:
        return total_credit - total_debit
    return total_debit - total_credit


def _positive(value: Decimal) -> Decimal:
    """Return *value* as positive (useful for income-statement display)."""
    return abs(value)


# ──────────────────────────────────────────────────────────────────────
# 1.  Profit & Loss (Income Statement)
# ──────────────────────────────────────────────────────────────────────

async def get_profit_loss(
    business_id: uuid.UUID,
    start_date: date,
    end_date: date,
    *,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Generate a **Profit & Loss** report for the given date range.

    Returns::

        {
            "business_id":  UUID,
            "period":       {"start": date, "end": date},
            "revenue":      Decimal,
            "cost_of_goods_sold": Decimal,
            "gross_profit": Decimal,
            "operating_expenses": Decimal,
            "operating_income": Decimal,
            "other_income":  Decimal,
            "other_expenses": Decimal,
            "net_income":   Decimal,
            "revenue_items": [
                {"account_id": UUID, "code": str, "name": str, "amount": Decimal},
                ...
            ],
            "expense_items": [
                {"account_id": UUID, "code": str, "name": str, "amount": Decimal},
                ...
            ],
        }
    """
    # ── Revenue accounts ──────────────────────────────────────────────
    revenue_stmt = (
        select(
            ChartOfAccounts.id.label("account_id"),
            ChartOfAccounts.code.label("code"),
            ChartOfAccounts.name.label("name"),
            ChartOfAccounts.account_type.label("account_type"),
            func.coalesce(func.sum(JournalLine.debit), Decimal("0")).label("total_debit"),
            func.coalesce(func.sum(JournalLine.credit), Decimal("0")).label("total_credit"),
        )
        .join(JournalLine, JournalLine.account_id == ChartOfAccounts.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            ChartOfAccounts.business_id == business_id,
            ChartOfAccounts.account_type == "revenue",
            JournalEntry.is_draft.is_(False),
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
        )
        .group_by(ChartOfAccounts.id, ChartOfAccounts.code, ChartOfAccounts.name, ChartOfAccounts.account_type)
        .order_by(ChartOfAccounts.code)
    )
    rev_result = await db.execute(revenue_stmt)
    rev_rows = rev_result.all()

    total_revenue = Decimal("0")
    revenue_items: list[dict[str, Any]] = []
    for row in rev_rows:
        amt = _positive(_balance_for_display(row.total_debit, row.total_credit, row.account_type))
        total_revenue += amt
        revenue_items.append(
            {"account_id": row.account_id, "code": row.code, "name": row.name, "amount": amt}
        )

    # ── Expense accounts ──────────────────────────────────────────────
    expense_stmt = (
        select(
            ChartOfAccounts.id.label("account_id"),
            ChartOfAccounts.code.label("code"),
            ChartOfAccounts.name.label("name"),
            ChartOfAccounts.account_type.label("account_type"),
            ChartOfAccounts.parent_id.label("parent_id"),
            func.coalesce(func.sum(JournalLine.debit), Decimal("0")).label("total_debit"),
            func.coalesce(func.sum(JournalLine.credit), Decimal("0")).label("total_credit"),
        )
        .join(JournalLine, JournalLine.account_id == ChartOfAccounts.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            ChartOfAccounts.business_id == business_id,
            ChartOfAccounts.account_type == "expense",
            JournalEntry.is_draft.is_(False),
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
        )
        .group_by(
            ChartOfAccounts.id, ChartOfAccounts.code,
            ChartOfAccounts.name, ChartOfAccounts.account_type,
            ChartOfAccounts.parent_id,
        )
        .order_by(ChartOfAccounts.code)
    )
    exp_result = await db.execute(expense_stmt)
    exp_rows = exp_result.all()

    # Classify expenses by parent / keyword heuristic
    total_cogs = Decimal("0")
    total_operating = Decimal("0")
    total_other_expenses = Decimal("0")
    expense_items: list[dict[str, Any]] = []

    for row in exp_rows:
        amt = _balance_for_display(row.total_debit, row.total_credit, row.account_type)
        name_lower = row.name.lower()

        if "cost of goods" in name_lower or "cogs" in name_lower or row.parent_id is not None:
            total_cogs += amt
        elif any(kw in name_lower for kw in ("bank", "interest", "finance")):
            total_other_expenses += amt
        else:
            total_operating += amt

        expense_items.append(
            {"account_id": row.account_id, "code": row.code, "name": row.name, "amount": amt}
        )

    # ── Other income (gain accounts) ─────────────────────────────────
    other_income_stmt = (
        select(
            func.coalesce(func.sum(JournalLine.debit), Decimal("0")).label("td"),
            func.coalesce(func.sum(JournalLine.credit), Decimal("0")).label("tc"),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
        .where(
            ChartOfAccounts.business_id == business_id,
            ChartOfAccounts.account_type == "revenue",
            ChartOfAccounts.name.ilike("%gain%"),
            JournalEntry.is_draft.is_(False),
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
        )
    )
    oi_row = (await db.execute(other_income_stmt)).one_or_none()
    other_income = _positive(_balance_for_display(oi_row.td, oi_row.tc, "revenue")) if oi_row else Decimal("0")

    # ── Assemble ──────────────────────────────────────────────────────
    gross_profit = total_revenue - total_cogs
    operating_income = gross_profit - total_operating
    net_income = operating_income + other_income - total_other_expenses

    return {
        "business_id": business_id,
        "period": {"start": start_date, "end": end_date},
        "revenue": total_revenue,
        "cost_of_goods_sold": total_cogs,
        "gross_profit": gross_profit,
        "operating_expenses": total_operating,
        "operating_income": operating_income,
        "other_income": other_income,
        "other_expenses": total_other_expenses,
        "net_income": net_income,
        "revenue_items": revenue_items,
        "expense_items": expense_items,
    }


# ──────────────────────────────────────────────────────────────────────
# 2.  Balance Sheet (Statement of Financial Position)
# ──────────────────────────────────────────────────────────────────────

async def get_balance_sheet(
    business_id: uuid.UUID,
    as_of_date: date,
    *,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Generate a **Balance Sheet** as of *as_of_date*.

    Balances are computed from all approved journal entries with
    ``entry_date <= as_of_date``.

    Returns::

        {
            "business_id":  UUID,
            "as_of_date":   date,
            "total_assets": Decimal,
            "total_liabilities": Decimal,
            "total_equity": Decimal,
            "assets": [...],
            "liabilities": [...],
            "equity": [...],
            "check": {
                "debit_total":  Decimal,
                "credit_total": Decimal,
                "balanced":     bool,
            },
        }

    The ``check`` block verifies the accounting equation:
    Assets = Liabilities + Equity
    """
    # ── Helper: balance for an account type as of date ────────────────
    async def _account_balances(account_type: str) -> list[dict[str, Any]]:
        stmt = (
            select(
                ChartOfAccounts.id.label("account_id"),
                ChartOfAccounts.code.label("code"),
                ChartOfAccounts.name.label("name"),
                ChartOfAccounts.account_type.label("account_type"),
                func.coalesce(func.sum(JournalLine.debit), Decimal("0")).label("total_debit"),
                func.coalesce(func.sum(JournalLine.credit), Decimal("0")).label("total_credit"),
            )
            .join(JournalLine, JournalLine.account_id == ChartOfAccounts.id)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(
                ChartOfAccounts.business_id == business_id,
                ChartOfAccounts.account_type == account_type,
                JournalEntry.is_draft.is_(False),
                JournalEntry.entry_date <= as_of_date,
            )
            .group_by(ChartOfAccounts.id, ChartOfAccounts.code, ChartOfAccounts.name, ChartOfAccounts.account_type)
            .order_by(ChartOfAccounts.code)
        )
        result = await db.execute(stmt)
        rows = result.all()

        items: list[dict[str, Any]] = []
        for row in rows:
            bal = _balance_for_display(row.total_debit, row.total_credit, row.account_type)
            items.append(
                {
                    "account_id": row.account_id,
                    "code": row.code,
                    "name": row.name,
                    "balance": bal,
                }
            )
        return items

    assets = await _account_balances("asset")
    liabilities = await _account_balances("liability")
    equity = await _account_balances("equity")

    total_assets = sum((a["balance"] for a in assets), Decimal("0"))
    total_liabilities = sum((l["balance"] for l in liabilities), Decimal("0"))
    total_equity = sum((e["balance"] for e in equity), Decimal("0"))

    # Verify accounting equation (Assets = Liabilities + Equity)
    balanced = total_assets == (total_liabilities + total_equity)

    return {
        "business_id": business_id,
        "as_of_date": as_of_date,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "check": {
            "debit_total": total_assets,
            "credit_total": total_liabilities + total_equity,
            "balanced": balanced,
        },
    }


# ──────────────────────────────────────────────────────────────────────
# 3.  Cash Flow Statement (indirect method)
# ──────────────────────────────────────────────────────────────────────

async def get_cash_flow(
    business_id: uuid.UUID,
    start_date: date,
    end_date: date,
    *,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Generate a **Cash Flow Statement** using the indirect method.

    Cash accounts are identified by name containing "cash" or "bank".

    Returns::

        {
            "business_id":       UUID,
            "period":            {"start": date, "end": date},
            "operating_activities": Decimal,
            "investing_activities": Decimal,
            "financing_activities": Decimal,
            "net_cash_flow":     Decimal,
            "beginning_cash":    Decimal,
            "ending_cash":       Decimal,
            "details": {
                "operating": [...],
                "investing": [...],
                "financing": [...],
            },
        }
    """
    # ── Identify cash accounts ────────────────────────────────────────
    cash_acct_stmt = (
        select(ChartOfAccounts.id, ChartOfAccounts.code, ChartOfAccounts.name)
        .where(
            ChartOfAccounts.business_id == business_id,
            ChartOfAccounts.account_type == "asset",
        )
    )
    cash_result = await db.execute(cash_acct_stmt)
    all_asset_accts = cash_result.all()

    cash_account_ids = {
        a.id for a in all_asset_accts
        if "cash" in a.name.lower() or "bank" in a.name.lower()
    }
    non_cash_asset_ids = {a.id for a in all_asset_accts} - cash_account_ids

    # ── Revenue-based inflows (operating) ─────────────────────────────
    revenue_stmt = (
        select(
            ChartOfAccounts.id.label("account_id"),
            ChartOfAccounts.name.label("name"),
            func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), Decimal("0")).label("amount"),
        )
        .join(JournalLine, JournalLine.account_id == ChartOfAccounts.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            ChartOfAccounts.business_id == business_id,
            ChartOfAccounts.account_type == "revenue",
            JournalEntry.is_draft.is_(False),
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
        )
        .group_by(ChartOfAccounts.id, ChartOfAccounts.name)
    )
    rev_result = await db.execute(revenue_stmt)
    operating_inflows = sum(
        (row.amount for row in rev_result.all()),
        Decimal("0"),
    )

    # ── Expense-based outflows (operating) ────────────────────────────
    expense_stmt = (
        select(
            ChartOfAccounts.id.label("account_id"),
            ChartOfAccounts.name.label("name"),
            func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), Decimal("0")).label("amount"),
        )
        .join(JournalLine, JournalLine.account_id == ChartOfAccounts.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            ChartOfAccounts.business_id == business_id,
            ChartOfAccounts.account_type == "expense",
            JournalEntry.is_draft.is_(False),
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
        )
        .group_by(ChartOfAccounts.id, ChartOfAccounts.name)
    )
    exp_result = await db.execute(expense_stmt)
    operating_outflows = sum(
        (row.amount for row in exp_result.all()),
        Decimal("0"),
    )

    net_operating = operating_inflows - operating_outflows

    # ── Investing activities (non-cash asset changes) ─────────────────
    investing_stmt = (
        select(
            ChartOfAccounts.id.label("account_id"),
            ChartOfAccounts.name.label("name"),
            func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), Decimal("0")).label("amount"),
        )
        .join(JournalLine, JournalLine.account_id == ChartOfAccounts.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            ChartOfAccounts.id.in_(non_cash_asset_ids),
            JournalEntry.is_draft.is_(False),
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
        )
        .group_by(ChartOfAccounts.id, ChartOfAccounts.name)
    )
    inv_result = await db.execute(investing_stmt)
    investing_details = []
    net_investing = Decimal("0")
    for row in inv_result.all():
        # Positive debit-credit balance on a non-cash asset = cash outflow
        net_investing -= row.amount
        investing_details.append({"account_id": row.account_id, "name": row.name, "amount": -row.amount})

    # ── Financing activities (liability + equity changes) ─────────────
    financing_stmt = (
        select(
            ChartOfAccounts.id.label("account_id"),
            ChartOfAccounts.name.label("name"),
            ChartOfAccounts.account_type.label("account_type"),
            func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), Decimal("0")).label("amount"),
        )
        .join(JournalLine, JournalLine.account_id == ChartOfAccounts.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            ChartOfAccounts.account_type.in_(["liability", "equity"]),
            JournalEntry.is_draft.is_(False),
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
        )
        .group_by(ChartOfAccounts.id, ChartOfAccounts.name, ChartOfAccounts.account_type)
    )
    fin_result = await db.execute(financing_stmt)
    financing_details = []
    net_financing = Decimal("0")
    for row in fin_result.all():
        # Positive credit-balance increase = cash inflow
        net_financing += row.amount
        financing_details.append({"account_id": row.account_id, "name": row.name, "amount": row.amount})

    # ── Cash balance changes ──────────────────────────────────────────
    cash_begin_stmt = (
        select(
            func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), Decimal("0")).label("amount"),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            JournalLine.account_id.in_(cash_account_ids),
            JournalEntry.is_draft.is_(False),
            JournalEntry.entry_date < start_date,
        )
    )
    cash_end_stmt = (
        select(
            func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), Decimal("0")).label("amount"),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            JournalLine.account_id.in_(cash_account_ids),
            JournalEntry.is_draft.is_(False),
            JournalEntry.entry_date <= end_date,
        )
    )
    beg_row = (await db.execute(cash_begin_stmt)).one()
    end_row = (await db.execute(cash_end_stmt)).one()

    beginning_cash = beg_row.amount
    net_cash_flow = net_operating + net_investing + net_financing
    ending_cash = beginning_cash + net_cash_flow

    return {
        "business_id": business_id,
        "period": {"start": start_date, "end": end_date},
        "operating_activities": net_operating,
        "investing_activities": net_investing,
        "financing_activities": net_financing,
        "net_cash_flow": net_cash_flow,
        "beginning_cash": beginning_cash,
        "ending_cash": ending_cash,
        "details": {
            "operating": [
                {"type": "revenue_inflows", "amount": operating_inflows},
                {"type": "expense_outflows", "amount": -operating_outflows},
            ],
            "investing": investing_details,
            "financing": financing_details,
        },
    }


# ──────────────────────────────────────────────────────────────────────
# 4.  Trial Balance
# ──────────────────────────────────────────────────────────────────────

async def get_trial_balance(
    business_id: uuid.UUID,
    *,
    db: AsyncSession,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """
    Generate a **Trial Balance** for the business.

    If *as_of_date* is provided, only approved entries up to that date
    are included; otherwise **all** approved entries are used.

    Returns::

        {
            "business_id":  UUID,
            "as_of_date":   date | None,
            "accounts": [
                {
                    "account_id":   UUID,
                    "code":         str,
                    "name":         str,
                    "account_type": str,
                    "debit_total":  Decimal,
                    "credit_total": Decimal,
                },
                ...
            ],
            "total_debits":  Decimal,
            "total_credits": Decimal,
            "balanced":      bool,
        }
    """
    # Build the base filter for journal entries
    entry_filters = [
        JournalEntry.business_id == business_id,
        JournalEntry.is_draft.is_(False),
    ]
    if as_of_date is not None:
        entry_filters.append(JournalEntry.entry_date <= as_of_date)

    stmt = (
        select(
            ChartOfAccounts.id.label("account_id"),
            ChartOfAccounts.code.label("code"),
            ChartOfAccounts.name.label("name"),
            ChartOfAccounts.account_type.label("account_type"),
            func.coalesce(func.sum(JournalLine.debit), Decimal("0")).label("debit_total"),
            func.coalesce(func.sum(JournalLine.credit), Decimal("0")).label("credit_total"),
        )
        .join(JournalLine, JournalLine.account_id == ChartOfAccounts.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(and_(*entry_filters))
        .group_by(
            ChartOfAccounts.id,
            ChartOfAccounts.code,
            ChartOfAccounts.name,
            ChartOfAccounts.account_type,
        )
        .order_by(ChartOfAccounts.code)
    )

    result = await db.execute(stmt)
    rows = result.all()

    accounts: list[dict[str, Any]] = []
    total_debits = Decimal("0")
    total_credits = Decimal("0")

    for row in rows:
        accounts.append(
            {
                "account_id": row.account_id,
                "code": row.code,
                "name": row.name,
                "account_type": row.account_type,
                "debit_total": row.debit_total,
                "credit_total": row.credit_total,
            }
        )
        total_debits += row.debit_total
        total_credits += row.credit_total

    balanced = total_debits == total_credits

    return {
        "business_id": business_id,
        "as_of_date": as_of_date,
        "accounts": accounts,
        "total_debits": total_debits,
        "total_credits": total_credits,
        "balanced": balanced,
    }
