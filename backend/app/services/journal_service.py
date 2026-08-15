"""
FinPilot AI — Journal Service
──────────────────────────────
Draft journal entries, approval, reversal, and balance queries at the
individual-account and full-business level.

All monetary values use Python ``Decimal`` — never ``float``.
Double-entry rules enforced:
    asset / expense          → debit-positive  (increases with debit)
    liability / equity / revenue → credit-positive (increases with credit)
"""

from __future__ import annotations

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


async def _get_account(db: AsyncSession, account_id: uuid.UUID) -> ChartOfAccounts:
    """Fetch an account or raise ``ValueError``."""
    stmt = select(ChartOfAccounts).where(ChartOfAccounts.id == account_id)
    result = await db.execute(stmt)
    acct = result.scalar_one_or_none()
    if acct is None:
        raise ValueError(f"Account {account_id} not found")
    return acct


async def _get_entry(db: AsyncSession, entry_id: uuid.UUID) -> JournalEntry:
    """Fetch a journal entry or raise ``ValueError``."""
    stmt = select(JournalEntry).where(JournalEntry.id == entry_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if entry is None:
        raise ValueError(f"Journal entry {entry_id} not found")
    return entry


# ──────────────────────────────────────────────────────────────────────
# 1.  Create draft journal entry
# ──────────────────────────────────────────────────────────────────────

async def create_draft_entry(
    db: AsyncSession,
    *,
    business_id: uuid.UUID,
    entry_date: date,
    lines: list[dict[str, Any]],
    memo: str | None = None,
    transaction_id: uuid.UUID | None = None,
    created_by: str = "system",
) -> JournalEntry:
    """
    Create a journal entry in **draft** state (``is_draft=True``).

    Parameters
    ----------
    lines : list[dict]
        Each dict must contain:
        - ``account_id`` : UUID of an existing account in ``chart_of_accounts``
        - ``debit``      : Decimal amount (omit or 0 for credit-only lines)
        - ``credit``     : Decimal amount (omit or 0 for debit-only lines)

    **Strict invariants enforced:**

    1. At least two lines.
    2. ``debit >= 0`` and ``credit >= 0`` on every line.
    3. No line may have both ``debit > 0`` **and** ``credit > 0``.
    4. At least one line has a nonzero amount.
    5. **Total debits must equal total credits.**

    Raises ``ValueError`` on any violation.

    The entry is inserted as ``is_draft=True``.  Call ``approve_entry``
    (below) to promote it.
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

        # Validate the account actually exists
        await _get_account(db, account_id)

        debit = _to_decimal(raw.get("debit", 0))
        credit = _to_decimal(raw.get("credit", 0))

        if debit < 0 or credit < 0:
            raise ValueError(f"Line {idx}: debit and credit must be >= 0")

        if debit > 0 and credit > 0:
            raise ValueError(
                f"Line {idx}: a line cannot have both debit > 0 and credit > 0"
            )

        if debit == 0 and credit == 0:
            raise ValueError(
                f"Line {idx}: at least one of debit or credit must be > 0"
            )

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
        is_draft=True,
    )
    db.add(entry)
    await db.flush()

    for jl in journal_lines:
        jl.journal_entry_id = entry.id
        db.add(jl)

    await db.flush()

    return entry


# ──────────────────────────────────────────────────────────────────────
# 2.  Approve entry (draft → posted)
# ──────────────────────────────────────────────────────────────────────

async def approve_entry(
    db: AsyncSession,
    entry_id: uuid.UUID,
    *,
    approved_by: str = "system",
) -> JournalEntry:
    """
    Promote a draft journal entry to **posted** (``is_draft → False``).

    A re-check of debit == credit is performed before approval to guard
    against any race-condition corruption.

    Raises ``ValueError`` if:
    - entry not found
    - entry is not a draft
    - entry lines no longer balance
    """
    entry = await _get_entry(db, entry_id)

    if not entry.is_draft:
        raise ValueError(
            f"Journal entry {entry_id} is not a draft; cannot approve"
        )

    # Re-verify balance
    bal_stmt = (
        select(
            func.coalesce(func.sum(JournalLine.debit), Decimal("0")).label("td"),
            func.coalesce(func.sum(JournalLine.credit), Decimal("0")).label("tc"),
        )
        .where(JournalLine.journal_entry_id == entry_id)
    )
    row = (await db.execute(bal_stmt)).one()
    if row.td != row.tc:
        raise ValueError(
            f"Journal entry {entry_id} is out of balance at approval time: "
            f"debit={row.td}, credit={row.tc}"
        )

    entry.is_draft = False
    entry.created_by = approved_by
    db.add(entry)
    await db.flush()

    # Mark linked transaction as posted
    if entry.transaction_id is not None:
        await db.execute(
            update(Transaction)
            .where(Transaction.id == entry.transaction_id)
            .values(status="posted")
        )

    return entry


# ──────────────────────────────────────────────────────────────────────
# 3.  Reverse entry
# ──────────────────────────────────────────────────────────────────────

async def reverse_entry(
    db: AsyncSession,
    entry_id: uuid.UUID,
    *,
    reversal_date: date | None = None,
    memo: str | None = None,
    created_by: str = "system",
) -> JournalEntry:
    """
    Create a **reversing entry** that cancels out an existing approved entry.

    The reversal entry:

    - Is created as ``is_draft=False`` (immediately posted).
    - Debits and credits are **swapped** from the original entry.
    - The original entry's ``memo`` is preserved and prefixed with
      ``"[REVERSED]"``.
    - A new ``memo`` field can be supplied for the reversal entry.

    Parameters
    ----------
    reversal_date : date, optional
        Defaults to ``date.today()`` if omitted.

    Returns the newly created reversal ``JournalEntry``.

    Raises ``ValueError`` if the original entry is not found or is still
    a draft.
    """
    original = await _get_entry(db, entry_id)

    if original.is_draft:
        raise ValueError(
            f"Journal entry {entry_id} is still a draft; reverse only posted entries"
        )

    if reversal_date is None:
        reversal_date = date.today()

    # Fetch original lines
    lines_stmt = (
        select(JournalLine)
        .where(JournalLine.journal_entry_id == entry_id)
    )
    result = await db.execute(lines_stmt)
    orig_lines = result.scalars().all()

    # Build reversed lines (swap debit ↔ credit)
    reversed_lines: list[dict[str, Any]] = []
    for ol in orig_lines:
        reversed_lines.append(
            {
                "account_id": ol.account_id,
                "debit": ol.credit,   # swap
                "credit": ol.debit,   # swap
            }
        )

    reversal_memo = memo or f"Reversal of entry {entry_id}"
    original_memo = original.memo or ""
    original.memo = f"[REVERSED] {original_memo}".strip()
    db.add(original)

    reversal_entry = JournalEntry(
        business_id=original.business_id,
        transaction_id=None,
        entry_date=reversal_date,
        memo=reversal_memo,
        created_by=created_by,
        is_draft=False,
    )
    db.add(reversal_entry)
    await db.flush()

    for rl in reversed_lines:
        jl = JournalLine(
            journal_entry_id=reversal_entry.id,
            account_id=rl["account_id"],
            debit=rl["debit"],
            credit=rl["credit"],
        )
        db.add(jl)

    await db.flush()

    # If original had a linked transaction, mark it as reversed
    if original.transaction_id is not None:
        await db.execute(
            update(Transaction)
            .where(Transaction.id == original.transaction_id)
            .values(status="flagged")
        )

    return reversal_entry


# ──────────────────────────────────────────────────────────────────────
# 4.  Get balance for a single account
# ──────────────────────────────────────────────────────────────────────

async def get_balance_for_account(
    db: AsyncSession,
    account_id: uuid.UUID,
) -> Decimal:
    """
    Return the **net balance** (total debits − total credits) for a single
    account across all **approved** (non-draft) journal entries.

    For debit-normal accounts (asset / expense) a positive number is the
    expected normal balance.  For credit-normal accounts (liability /
    equity / revenue) a negative number is the expected normal balance;
    negate it to display the conventional positive figure.
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
    row = (await db.execute(stmt)).one()
    return row.total_debit - row.total_credit


# ──────────────────────────────────────────────────────────────────────
# 5.  Get all account balances for a business
# ──────────────────────────────────────────────────────────────────────

async def get_all_account_balances_for_business(
    db: AsyncSession,
    business_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """
    Return the balance of **every** account in the business's chart of
    accounts, ordered by account code.

    Each item::

        {
            "account_id":   UUID,
            "code":         str,
            "name":         str,
            "account_type": str,       # asset | liability | equity | revenue | expense
            "balance":      Decimal,   # debit − credit
        }

    Only approved (non-draft) journal entries are counted.
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
        bal = await get_balance_for_account(db, acct.id)
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
