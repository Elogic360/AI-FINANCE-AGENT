"""
FinPilot AI — Bank Reconciliation Engine
─────────────────────────────────────────
Deterministic bank-to-ledger transaction matching and reconciliation.

Matching strategies (in priority order):
    1. Exact match: amount + date match
    2. Fuzzy match: amount matches within tolerance, date within window
    3. Partial match: amount matches but date differs significantly

All monetary values use Python ``Decimal`` — never ``float``.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import ChartOfAccounts, JournalEntry, JournalLine, Transaction

from app.financial.metrics import MatchedTransaction, ReconciliationResult


# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

_ZERO = Decimal("0")
_EXACT_DATE_TOLERANCE = timedelta(days=0)
_FUZZY_DATE_TOLERANCE = timedelta(days=3)
_FUZZY_AMOUNT_TOLERANCE = Decimal("0.02")  # 2% tolerance


# ──────────────────────────────────────────────────────────────────────
# Transaction matching
# ──────────────────────────────────────────────────────────────────────

def _amount_match_score(
    bank_amount: Decimal,
    ledger_amount: Decimal,
) -> Decimal:
    """
    Calculate a match score (0–1) based on amount similarity.

    Exact match → 1.0
    Within 2% → 0.8
    Within 5% → 0.5
    Otherwise → 0.0
    """
    if bank_amount == _ZERO and ledger_amount == _ZERO:
        return Decimal("1.0")

    if bank_amount == ledger_amount:
        return Decimal("1.0")

    # Allow for sign differences (bank debits vs ledger credits)
    if abs(bank_amount) == abs(ledger_amount):
        return Decimal("0.95")

    max_amt = max(abs(bank_amount), abs(ledger_amount))
    if max_amt == _ZERO:
        return _ZERO

    diff_pct = abs(abs(bank_amount) - abs(ledger_amount)) / max_amt

    if diff_pct <= Decimal("0.01"):
        return Decimal("0.9")
    if diff_pct <= _FUZZY_AMOUNT_TOLERANCE:
        return Decimal("0.8")
    if diff_pct <= Decimal("0.05"):
        return Decimal("0.5")

    return _ZERO


def _date_match_score(
    bank_date: date,
    ledger_date: date,
) -> Decimal:
    """
    Calculate a match score (0–1) based on date proximity.

    Same day → 1.0
    1 day apart → 0.9
    2–3 days apart → 0.7
    4–7 days apart → 0.4
    Otherwise → 0.0
    """
    diff = abs((bank_date - ledger_date).days)

    if diff == 0:
        return Decimal("1.0")
    if diff == 1:
        return Decimal("0.9")
    if diff <= 3:
        return Decimal("0.7")
    if diff <= 7:
        return Decimal("0.4")

    return _ZERO


def match_transactions(
    bank_transactions: list[dict[str, Any]],
    ledger_transactions: list[dict[str, Any]],
    *,
    min_score: Decimal = Decimal("0.6"),
) -> list[MatchedTransaction]:
    """
    Match bank transactions to ledger transactions.

    Parameters
    ----------
    bank_transactions : list[dict]
        Each must have: ``date`` (date), ``amount`` (Decimal), ``description`` (str)
    ledger_transactions : list[dict]
        Each must have: ``date`` (date), ``amount`` (Decimal), ``description`` (str)
    min_score : Decimal
        Minimum combined score to consider a match.

    Returns a list of ``MatchedTransaction`` objects sorted by match_score desc.
    """
    matches: list[MatchedTransaction] = []
    used_ledger: set[int] = set()

    # Sort bank transactions by amount (largest first) for priority matching
    sorted_bank = sorted(
        enumerate(bank_transactions),
        key=lambda x: abs(x[1].get("amount", _ZERO)),
        reverse=True,
    )

    for bank_idx, bank_txn in sorted_bank:
        bank_amount = bank_txn.get("amount", _ZERO)
        bank_date = bank_txn.get("date", date.today())

        best_score = _ZERO
        best_ledger_idx: int | None = None
        best_match_type = ""

        for ledger_idx, ledger_txn in enumerate(ledger_transactions):
            if ledger_idx in used_ledger:
                continue

            ledger_amount = ledger_txn.get("amount", _ZERO)
            ledger_date = ledger_txn.get("date", date.today())

            amt_score = _amount_match_score(bank_amount, ledger_amount)
            date_score = _date_match_score(bank_date, ledger_date)

            # Combined score: 70% amount, 30% date
            combined = amt_score * Decimal("0.7") + date_score * Decimal("0.3")

            if combined >= min_score and combined > best_score:
                best_score = combined
                best_ledger_idx = ledger_idx

                # Determine match type
                if amt_score >= Decimal("0.95") and date_score >= Decimal("0.9"):
                    best_match_type = "exact"
                elif combined >= Decimal("0.7"):
                    best_match_type = "fuzzy"
                else:
                    best_match_type = "partial"

        if best_ledger_idx is not None:
            used_ledger.add(best_ledger_idx)
            matches.append(MatchedTransaction(
                bank_transaction=bank_txn,
                ledger_transaction=ledger_transactions[best_ledger_idx],
                match_score=best_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                match_type=best_match_type,
            ))

    # Sort by score descending
    matches.sort(key=lambda m: m.match_score, reverse=True)
    return matches


# ──────────────────────────────────────────────────────────────────────
# Bank reconciliation
# ──────────────────────────────────────────────────────────────────────

async def reconcile_bank_transactions(
    db: AsyncSession,
    org_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    bank_statement_balance: Decimal | None = None,
    statement_date: date | None = None,
) -> ReconciliationResult:
    """
    Reconcile bank transactions against the general ledger.

    Fetches all transactions and journal entries for the bank account,
    then runs the matching algorithm.

    Parameters
    ----------
    bank_account_id : UUID
        The chart of accounts ID for the bank/cash account.
    bank_statement_balance : Decimal, optional
        The bank statement ending balance.  If not provided, uses
        the sum of bank transactions.
    statement_date : date, optional
        The statement date.  Defaults to today.
    """
    if statement_date is None:
        statement_date = date.today()

    # ── Fetch ledger entries for this bank account ─────────────────
    ledger_stmt = (
        select(
            JournalEntry.id.label("entry_id"),
            JournalEntry.entry_date.label("entry_date"),
            JournalEntry.memo.label("memo"),
            JournalLine.debit.label("debit"),
            JournalLine.credit.label("credit"),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            JournalLine.account_id == bank_account_id,
            JournalEntry.business_id == org_id,
            JournalEntry.is_draft.is_(False),
            JournalEntry.entry_date <= statement_date,
        )
        .order_by(JournalEntry.entry_date)
    )
    ledger_rows = (await db.execute(ledger_stmt)).all()

    ledger_transactions: list[dict[str, Any]] = []
    ledger_balance = _ZERO

    for r in ledger_rows:
        net_amount = r.debit - r.credit
        ledger_balance += net_amount
        ledger_transactions.append({
            "entry_id": str(r.entry_id),
            "date": r.entry_date,
            "amount": net_amount,
            "debit": r.debit,
            "credit": r.credit,
            "description": r.memo or "",
        })

    # ── Fetch raw transactions that might be bank transactions ────
    # (Transactions with source "bank" or "import" that haven't been matched)
    txn_stmt = (
        select(Transaction)
        .where(
            Transaction.business_id == org_id,
            Transaction.txn_date <= statement_date,
            Transaction.status.in_(["pending", "categorized"]),
        )
        .order_by(Transaction.txn_date)
    )
    txn_rows = (await db.execute(txn_stmt)).scalars().all()

    bank_transactions: list[dict[str, Any]] = []
    bank_total = _ZERO

    for t in txn_rows:
        bank_total += t.amount
        bank_transactions.append({
            "transaction_id": str(t.id),
            "date": t.txn_date,
            "amount": t.amount,
            "description": t.description or "",
            "counterparty": t.counterparty or "",
            "source": t.source,
        })

    # Use provided statement balance or calculated total
    statement_balance = bank_statement_balance if bank_statement_balance is not None else bank_total

    # ── Run matching ───────────────────────────────────────────────
    matches = match_transactions(bank_transactions, ledger_transactions)

    # Identify unmatched
    matched_bank_ids = {m.bank_transaction.get("transaction_id") for m in matches}
    matched_ledger_ids = {m.ledger_transaction.get("entry_id") for m in matches}

    unmatched_bank = [
        t for t in bank_transactions
        if t.get("transaction_id") not in matched_bank_ids
    ]
    unmatched_ledger = [
        t for t in ledger_transactions
        if t.get("entry_id") not in matched_ledger_ids
    ]

    # Calculate match rate
    total_items = max(len(bank_transactions), len(ledger_transactions))
    match_rate = (
        _d(len(matches)) / _d(total_items) * Decimal("100")
    ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP) if total_items else _ZERO

    difference = statement_balance - ledger_balance
    is_reconciled = abs(difference) < Decimal("0.01") and len(unmatched_bank) == 0 and len(unmatched_ledger) == 0

    return ReconciliationResult(
        org_id=org_id,
        bank_account_id=bank_account_id,
        statement_balance=statement_balance,
        ledger_balance=ledger_balance,
        difference=difference,
        matched=matches,
        unmatched_bank=unmatched_bank,
        unmatched_ledger=unmatched_ledger,
        is_reconciled=is_reconciled,
        match_rate=match_rate,
    )
