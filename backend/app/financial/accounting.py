"""
FinPilot AI — Double-Entry Accounting Engine
─────────────────────────────────────────────
Journal entry creation, validation, posting, general ledger queries,
and trial balance generation.

All monetary values use Python ``Decimal`` — never ``float``.
Double-entry sign convention:
    asset / expense                → debit-positive  (increases with debit)
    liability / equity / revenue   → credit-positive (increases with credit)
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import (
    ChartOfAccounts,
    JournalEntry,
    JournalLine,
    Transaction,
)


# ──────────────────────────────────────────────────────────────────────
# Data classes (lightweight, no external deps)
# ──────────────────────────────────────────────────────────────────────

class JournalLineData:
    """Input data for a single journal line."""
    __slots__ = ("account_id", "debit", "credit")

    def __init__(
        self,
        account_id: uuid.UUID,
        debit: Decimal | int | str = Decimal("0"),
        credit: Decimal | int | str = Decimal("0"),
    ):
        self.account_id = account_id
        self.debit = _to_decimal(debit)
        self.credit = _to_decimal(credit)


class JournalEntryData:
    """Complete journal entry with lines."""
    __slots__ = ("org_id", "entry_date", "lines", "memo", "created_by")

    def __init__(
        self,
        org_id: uuid.UUID,
        entry_date: date,
        lines: list[JournalLineData],
        memo: str | None = None,
        created_by: str = "system",
    ):
        self.org_id = org_id
        self.entry_date = entry_date
        self.lines = lines
        self.memo = memo
        self.created_by = created_by


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

_ZERO = Decimal("0")
_CREDIT_NORMAL = frozenset({"liability", "equity", "revenue"})


def _to_decimal(value: Any) -> Decimal:
    """Safely coerce *value* to ``Decimal``."""
    if isinstance(value, Decimal):
        return value
    if value is None:
        return _ZERO
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Cannot convert {value!r} to Decimal")


def _display_balance(debit: Decimal, credit: Decimal, account_type: str) -> Decimal:
    """Return the normal-balance display value."""
    if account_type in _CREDIT_NORMAL:
        return credit - debit
    return debit - credit


# ──────────────────────────────────────────────────────────────────────
# 1. Create journal entry
# ──────────────────────────────────────────────────────────────────────

async def create_journal_entry(
    db: AsyncSession,
    org_id: uuid.UUID,
    lines: list[dict[str, Any]] | list[JournalLineData],
    entry_date: date | None = None,
    memo: str | None = None,
    created_by: str = "system",
    transaction_id: uuid.UUID | None = None,
    is_draft: bool = True,
) -> JournalEntry:
    """
    Create a new ``JournalEntry`` with attached ``JournalLine`` records.

    Parameters
    ----------
    lines : list[dict | JournalLineData]
        Each item must have ``account_id``, ``debit``, ``credit``.
    entry_date : date, optional
        Defaults to ``date.today()``.
    memo : str, optional
    created_by : str
    transaction_id : UUID, optional
    is_draft : bool

    **Strict invariants enforced:**
    1. At least two lines.
    2. ``debit >= 0`` and ``credit >= 0`` on every line.
    3. No line may have both ``debit > 0`` and ``credit > 0``.
    4. At least one of debit or credit must be > 0 per line.
    5. **Total debits must equal total credits.**

    Raises ``ValueError`` on any violation.
    """
    if len(lines) < 2:
        raise ValueError("A journal entry requires at least two lines")

    if entry_date is None:
        entry_date = date.today()

    total_debit = _ZERO
    total_credit = _ZERO
    journal_lines: list[JournalLine] = []

    for idx, raw in enumerate(lines):
        if isinstance(raw, JournalLineData):
            account_id = raw.account_id
            debit = raw.debit
            credit = raw.credit
        else:
            account_id = raw.get("account_id")
            debit = _to_decimal(raw.get("debit", 0))
            credit = _to_decimal(raw.get("credit", 0))

        if account_id is None:
            raise ValueError(f"Line {idx}: account_id is required")

        if debit < 0 or credit < 0:
            raise ValueError(f"Line {idx}: debit and credit must be >= 0")

        if debit > 0 and credit > 0:
            raise ValueError(f"Line {idx}: cannot have both debit > 0 and credit > 0")

        if debit == 0 and credit == 0:
            raise ValueError(f"Line {idx}: at least one of debit or credit must be > 0")

        total_debit += debit
        total_credit += credit

        journal_lines.append(JournalLine(
            account_id=account_id,
            debit=debit,
            credit=credit,
        ))

    if total_debit != total_credit:
        raise ValueError(
            f"Debit-Credit imbalance: debits={total_debit}, credits={total_credit}. "
            f"Debits must equal credits."
        )

    entry = JournalEntry(
        business_id=org_id,
        transaction_id=transaction_id,
        entry_date=entry_date,
        memo=memo,
        created_by=created_by,
        is_draft=is_draft,
    )
    db.add(entry)
    await db.flush()

    for jl in journal_lines:
        jl.journal_entry_id = entry.id
        db.add(jl)

    await db.flush()

    if transaction_id is not None:
        await db.execute(
            update(Transaction)
            .where(Transaction.id == transaction_id)
            .values(status="posted")
        )

    return entry


# ──────────────────────────────────────────────────────────────────────
# 2. Validate journal entry
# ──────────────────────────────────────────────────────────────────────

def validate_journal_entry(lines: list[dict[str, Any]] | list[JournalLineData]) -> bool:
    """
    Validate that a list of journal lines satisfies double-entry rules.

    Returns ``True`` if valid, raises ``ValueError`` otherwise.
    """
    if len(lines) < 2:
        raise ValueError("A journal entry requires at least two lines")

    total_debit = _ZERO
    total_credit = _ZERO

    for idx, raw in enumerate(lines):
        if isinstance(raw, JournalLineData):
            debit = raw.debit
            credit = raw.credit
        else:
            debit = _to_decimal(raw.get("debit", 0))
            credit = _to_decimal(raw.get("credit", 0))

        if debit < 0 or credit < 0:
            raise ValueError(f"Line {idx}: debit and credit must be >= 0")

        if debit > 0 and credit > 0:
            raise ValueError(f"Line {idx}: cannot have both debit > 0 and credit > 0")

        if debit == 0 and credit == 0:
            raise ValueError(f"Line {idx}: at least one of debit or credit must be > 0")

        total_debit += debit
        total_credit += credit

    if total_debit != total_credit:
        raise ValueError(
            f"Debit-Credit imbalance: debits={total_debit}, credits={total_credit}"
        )

    return True


# ──────────────────────────────────────────────────────────────────────
# 3. Post journal entry (approve draft)
# ──────────────────────────────────────────────────────────────────────

async def post_journal_entry(
    db: AsyncSession,
    entry_id: uuid.UUID,
    *,
    approved_by: str = "system",
) -> JournalEntry:
    """
    Promote a draft journal entry to posted (``is_draft → False``).

    Re-verifies debit == credit before posting.

    Raises ``ValueError`` if:
    - Entry not found
    - Entry is not a draft
    - Lines no longer balance
    """
    stmt = select(JournalEntry).where(JournalEntry.id == entry_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()

    if entry is None:
        raise ValueError(f"Journal entry {entry_id} not found")

    if not entry.is_draft:
        raise ValueError(f"Journal entry {entry_id} is not a draft; cannot post")

    # Re-verify balance
    bal_stmt = (
        select(
            func.coalesce(func.sum(JournalLine.debit), _ZERO).label("td"),
            func.coalesce(func.sum(JournalLine.credit), _ZERO).label("tc"),
        )
        .where(JournalLine.journal_entry_id == entry_id)
    )
    row = (await db.execute(bal_stmt)).one()
    if row.td != row.tc:
        raise ValueError(
            f"Journal entry {entry_id} out of balance: debits={row.td}, credits={row.tc}"
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
# 4. General Ledger
# ──────────────────────────────────────────────────────────────────────

async def get_general_ledger(
    db: AsyncSession,
    org_id: uuid.UUID,
    account_id: uuid.UUID,
    period: tuple[date, date] | None = None,
) -> dict[str, Any]:
    """
    Return the general ledger for a specific account.

    Parameters
    ----------
    period : tuple[date, date], optional
        (start_date, end_date).  If omitted, returns all entries.

    Returns::

        {
            "account": { "id", "code", "name", "type" },
            "entries": [
                {
                    "entry_id": UUID,
                    "entry_date": date,
                    "memo": str,
                    "debit": Decimal,
                    "credit": Decimal,
                    "running_balance": Decimal,
                },
                ...
            ],
            "total_debit": Decimal,
            "total_credit": Decimal,
            "closing_balance": Decimal,
        }
    """
    # Fetch account info
    acct_stmt = select(ChartOfAccounts).where(ChartOfAccounts.id == account_id)
    acct = (await db.execute(acct_stmt)).scalar_one_or_none()
    if acct is None:
        raise ValueError(f"Account {account_id} not found")

    # Build entry query
    filters = [
        JournalLine.account_id == account_id,
        JournalEntry.business_id == org_id,
        JournalEntry.is_draft.is_(False),
    ]
    if period is not None:
        filters.append(JournalEntry.entry_date >= period[0])
        filters.append(JournalEntry.entry_date <= period[1])

    stmt = (
        select(
            JournalEntry.id.label("entry_id"),
            JournalEntry.entry_date.label("entry_date"),
            JournalEntry.memo.label("memo"),
            JournalLine.debit.label("debit"),
            JournalLine.credit.label("credit"),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(and_(*filters))
        .order_by(JournalEntry.entry_date, JournalEntry.id)
    )
    rows = (await db.execute(stmt)).all()

    entries: list[dict[str, Any]] = []
    running_balance = _ZERO
    total_debit = _ZERO
    total_credit = _ZERO

    for r in rows:
        total_debit += r.debit
        total_credit += r.credit

        if acct.account_type in _CREDIT_NORMAL:
            running_balance += r.credit - r.debit
        else:
            running_balance += r.debit - r.credit

        entries.append({
            "entry_id": r.entry_id,
            "entry_date": r.entry_date,
            "memo": r.memo,
            "debit": r.debit,
            "credit": r.credit,
            "running_balance": running_balance,
        })

    return {
        "account": {
            "id": acct.id,
            "code": acct.code,
            "name": acct.name,
            "type": acct.account_type,
        },
        "entries": entries,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "closing_balance": running_balance,
    }


# ──────────────────────────────────────────────────────────────────────
# 5. Trial Balance
# ──────────────────────────────────────────────────────────────────────

async def get_trial_balance(
    db: AsyncSession,
    org_id: uuid.UUID,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """
    Generate a Trial Balance for the organization.

    Returns::

        {
            "org_id": UUID,
            "as_of_date": date | None,
            "accounts": [
                {
                    "account_id": UUID,
                    "code": str,
                    "name": str,
                    "account_type": str,
                    "debit_total": Decimal,
                    "credit_total": Decimal,
                },
                ...
            ],
            "total_debits": Decimal,
            "total_credits": Decimal,
            "balanced": bool,
        }
    """
    entry_filters = [
        JournalEntry.business_id == org_id,
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
            func.coalesce(func.sum(JournalLine.debit), _ZERO).label("debit_total"),
            func.coalesce(func.sum(JournalLine.credit), _ZERO).label("credit_total"),
        )
        .join(JournalLine, JournalLine.account_id == ChartOfAccounts.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(and_(*entry_filters))
        .group_by(
            ChartOfAccounts.id, ChartOfAccounts.code,
            ChartOfAccounts.name, ChartOfAccounts.account_type,
        )
        .order_by(ChartOfAccounts.code)
    )

    rows = (await db.execute(stmt)).all()

    accounts: list[dict[str, Any]] = []
    total_debits = _ZERO
    total_credits = _ZERO

    for r in rows:
        accounts.append({
            "account_id": r.account_id,
            "code": r.code,
            "name": r.name,
            "account_type": r.account_type,
            "debit_total": r.debit_total,
            "credit_total": r.credit_total,
        })
        total_debits += r.debit_total
        total_credits += r.credit_total

    return {
        "org_id": org_id,
        "as_of_date": as_of_date,
        "accounts": accounts,
        "total_debits": total_debits,
        "total_credits": total_credits,
        "balanced": total_debits == total_credits,
    }
