"""
FinPilot AI — Accounting Service
─────────────────────────────────
Transaction categorisation, journal entry creation (with enforced debit == credit
equality), approval, and balance queries.

All monetary values use Python ``Decimal`` — never ``float``.
Double-entry rules enforced:
    asset / expense  → debit-positive  (increases with debit)
    liability / equity / revenue → credit-positive (increases with credit)
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import (
    ChartOfAccounts,
    JournalEntry,
    JournalLine,
    Transaction,
)

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

VALID_ACCOUNT_TYPES = frozenset({"asset", "liability", "equity", "revenue", "expense"})

# Normal balance sign convention: positive normal balance side for each type.
# asset/expense → normal debit balance  →  sign_factor = +1 on debit side
# liability/equity/revenue → normal credit balance → sign_factor = -1 on debit side
DEBIT_NORMAL_TYPES = frozenset({"asset", "expense"})
CREDIT_NORMAL_TYPES = frozenset({"liability", "equity", "revenue"})

DEFAULT_CURRENCY = "TZS"

# Keyword → category mapping for auto-categorisation
KEYWORD_CATEGORY_MAP: dict[str, str] = {
    # Revenue
    "sales": "revenue",
    "invoice": "revenue",
    "service income": "revenue",
    "consulting": "revenue",
    "commission": "revenue",
    # Expense – COGS
    "cost of goods": "expense_cogs",
    "cogs": "expense_cogs",
    "inventory purchase": "expense_cogs",
    # Expense – Operating
    "rent": "expense_operating",
    "utilities": "expense_operating",
    "salary": "expense_operating",
    "payroll": "expense_operating",
    "insurance": "expense_operating",
    "marketing": "expense_operating",
    "advertising": "expense_operating",
    "office supplies": "expense_operating",
    "subscription": "expense_operating",
    "software": "expense_operating",
    # Expense – Financial
    "bank charges": "expense_financial",
    "interest expense": "expense_financial",
    "loan interest": "expense_financial",
    # Asset
    "cash": "asset",
    "bank": "asset",
    "accounts receivable": "asset",
    "prepaid": "asset",
    # Liability
    "accounts payable": "liability",
    "loan": "liability",
    "credit card": "liability",
    "tax payable": "liability",
}


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


def _normalise(text: str) -> str:
    """Lower-case, collapse whitespace, strip."""
    return re.sub(r"\s+", " ", text.lower().strip())


# ──────────────────────────────────────────────────────────────────────
# 1.  Categorise a single transaction
# ──────────────────────────────────────────────────────────────────────

def categorise_transaction(
    transaction: Transaction,
    *,
    keyword_map: dict[str, str] | None = None,
) -> str:
    """
    Assign an ``ai_category`` to *transaction* by keyword matching.

    Returns the assigned category string (also written to
    ``transaction.ai_category``).  Confidence is set to a simple heuristic:
    1.0 for exact keyword hit, 0.5 for partial, 0.0 if nothing matches.

    This function does **not** commit — the caller persists changes.
    """
    mapping = keyword_map or KEYWORD_CATEGORY_MAP
    description = _normalise(transaction.description or "")
    counterparty = _normalise(transaction.counterparty or "")
    searchable = f"{description} {counterparty}"

    best_match: str | None = None
    best_score: Decimal = Decimal("0.000")

    for keyword, category in mapping.items():
        kw = _normalise(keyword)
        if kw in searchable:
            score = Decimal("1.000")
        elif all(word in searchable for word in kw.split()):
            score = Decimal("0.750")
        else:
            continue

        if score > best_score:
            best_score = score
            best_match = category

    transaction.ai_category = best_match or "uncategorized"
    transaction.ai_confidence = best_score
    transaction.status = "categorized"

    return transaction.ai_category


# ──────────────────────────────────────────────────────────────────────
# 2.  Bulk categorise transactions by keywords
# ──────────────────────────────────────────────────────────────────────

async def bulk_categorize_by_keywords(
    db: AsyncSession,
    business_id: uuid.UUID,
    *,
    keyword_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Categorise every ``pending`` transaction for *business_id* using the
    keyword map.

    Returns a summary dict::

        {
            "total":       int,
            "categorized": int,
            "uncategorized": int,
        }
    """
    stmt = (
        select(Transaction)
        .where(
            Transaction.business_id == business_id,
            Transaction.status == "pending",
        )
        .order_by(Transaction.txn_date)
    )
    result = await db.execute(stmt)
    transactions = result.scalars().all()

    categorized = 0
    uncategorized = 0

    for txn in transactions:
        cat = categorise_transaction(txn, keyword_map=keyword_map)
        db.add(txn)
        if cat == "uncategorized":
            uncategorized += 1
        else:
            categorized += 1

    return {
        "total": len(transactions),
        "categorized": categorized,
        "uncategorized": uncategorized,
    }


# ──────────────────────────────────────────────────────────────────────
# 3.  Create journal entry (enforced debit == credit)
# ──────────────────────────────────────────────────────────────────────

async def create_journal_entry(
    db: AsyncSession,
    *,
    business_id: uuid.UUID,
    entry_date: date,
    lines: list[dict[str, Any]],
    memo: str | None = None,
    transaction_id: uuid.UUID | None = None,
    created_by: str = "system",
    is_draft: bool = False,
) -> JournalEntry:
    """
    Create a new ``JournalEntry`` with attached ``JournalLine`` records.

    Parameters
    ----------
    lines : list[dict]
        Each dict must contain:
        - ``account_id`` : UUID of the account from ``chart_of_accounts``
        - ``debit``      : Decimal amount (0 if credit)
        - ``credit``     : Decimal amount (0 if debit)

    **Strict invariants enforced:**

    1. Each line has ``debit >= 0`` and ``credit >= 0``.
    2. No line has both ``debit > 0`` **and** ``credit > 0``.
    3. Total debits **must equal** total credits.
    4. At least two lines are required.

    Raises ``ValueError`` on any violation.
    """
    if len(lines) < 2:
        raise ValueError("A journal entry requires at least two lines")

    total_debit = Decimal("0")
    total_credit = Decimal("0")

    journal_lines: list[JournalLine] = []

    for idx, raw in enumerate(lines):
        account_id = raw.get("account_id")
        if account_id is None:
            raise ValueError(f"Line {idx}: account_id is required")

        debit = _to_decimal(raw.get("debit", 0))
        credit = _to_decimal(raw.get("credit", 0))

        if debit < 0 or credit < 0:
            raise ValueError(f"Line {idx}: debit and credit must be >= 0")

        if debit > 0 and credit > 0:
            raise ValueError(
                f"Line {idx}: a line cannot have both debit > 0 and credit > 0"
            )

        if debit == 0 and credit == 0:
            raise ValueError(f"Line {idx}: at least one of debit or credit must be > 0")

        total_debit += debit
        total_credit += credit

        journal_lines.append(
            JournalLine(
                account_id=account_id,
                debit=debit,
                credit=credit,
            )
        )

    if total_debit != total_credit:
        raise ValueError(
            f"Debit-Credit imbalance: total_debit={total_debit}, "
            f"total_credit={total_credit}. Debits must equal credits."
        )

    entry = JournalEntry(
        business_id=business_id,
        transaction_id=transaction_id,
        entry_date=entry_date,
        memo=memo,
        created_by=created_by,
        is_draft=is_draft,
    )
    db.add(entry)
    await db.flush()  # assign entry.id

    for jl in journal_lines:
        jl.journal_entry_id = entry.id
        db.add(jl)

    await db.flush()

    # If linked to a transaction, update its status
    if transaction_id is not None:
        await db.execute(
            update(Transaction)
            .where(Transaction.id == transaction_id)
            .values(status="posted")
        )

    return entry


# ──────────────────────────────────────────────────────────────────────
# 4.  Approve journal entry
# ──────────────────────────────────────────────────────────────────────

async def approve_journal_entry(
    db: AsyncSession,
    entry_id: uuid.UUID,
    *,
    approved_by: str = "system",
) -> JournalEntry:
    """
    Approve a draft journal entry by flipping ``is_draft → False``.

    Only entries currently in ``is_draft == True`` can be approved.

    Raises ``ValueError`` if the entry is not found or not a draft.
    """
    stmt = select(JournalEntry).where(JournalEntry.id == entry_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()

    if entry is None:
        raise ValueError(f"Journal entry {entry_id} not found")

    if not entry.is_draft:
        raise ValueError(f"Journal entry {entry_id} is not a draft and cannot be approved")

    entry.is_draft = False
    entry.created_by = approved_by
    db.add(entry)
    await db.flush()

    return entry


# ──────────────────────────────────────────────────────────────────────
# 5.  Get account balance
# ──────────────────────────────────────────────────────────────────────

async def get_account_balance(
    db: AsyncSession,
    account_id: uuid.UUID,
) -> Decimal:
    """
    Return the **net balance** for a single account.

    Balance = total_debits − total_credits for the account.

    For debit-normal accounts (asset/expense) a positive result means a
    normal (expected) balance.  For credit-normal accounts (liability/
    equity/revenue) a negative result means a normal balance — negate it
    for display if you want the conventional sign.

    Only approved (non-draft) journal entries are included.
    """
    stmt = (
        select(
            func.coalesce(func.sum(JournalLine.debit), Decimal("0")).label("total_debit"),
            func.coalesce(func.sum(JournalLine.credit), Decimal("0")).label("total_credit"),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            JournalLine.account_id == account_id,
            JournalEntry.is_draft.is_(False),
        )
    )
    result = await db.execute(stmt)
    row = result.one()

    return row.total_debit - row.total_credit


# ──────────────────────────────────────────────────────────────────────
# 6.  Get all account balances for a business
# ──────────────────────────────────────────────────────────────────────

async def get_business_balances(
    db: AsyncSession,
    business_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """
    Return a list of balances for every account in the business's
    chart of accounts.

    Each item::

        {
            "account_id":   UUID,
            "code":         str,
            "name":         str,
            "account_type": str,
            "balance":      Decimal,  (debit − credit)
        }

    Only approved (non-draft) journal entries are included.
    """
    accounts_stmt = (
        select(ChartOfAccounts)
        .where(ChartOfAccounts.business_id == business_id)
        .order_by(ChartOfAccounts.code)
    )
    result = await db.execute(accounts_stmt)
    accounts = result.scalars().all()

    balances: list[dict[str, Any]] = []

    for acct in accounts:
        bal = await get_account_balance(db, acct.id)
        balances.append(
            {
                "account_id": acct.id,
                "code": acct.code,
                "name": acct.name,
                "account_type": acct.account_type,
                "balance": bal,
            }
        )

    return balances
