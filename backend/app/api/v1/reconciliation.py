"""Bank reconciliation endpoints for FinPilot AI."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.accounting import Transaction
from app.models.business import User
from app.schemas.reconciliation import (
    ReconciliationRunRequest,
    ReconciliationResult,
    ReconciledItem,
    ReconciliationResultsList,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /reconciliation/run — Run bank reconciliation
# ---------------------------------------------------------------------------

@router.post("/run", response_model=ReconciliationResult)
async def run_reconciliation(
    body: ReconciliationRunRequest = ReconciliationRunRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run bank reconciliation — match bank transactions against book records."""
    bid = current_user.business_id
    today = date.today()
    start = body.date_from or today.replace(day=1)
    end = body.date_to or today

    # Fetch all transactions in the period
    txns = (await db.execute(
        select(Transaction)
        .where(
            Transaction.business_id == bid,
            Transaction.txn_date >= start,
            Transaction.txn_date <= end,
        )
        .order_by(Transaction.txn_date)
    )).scalars().all()

    matched = []
    unmatched_bank = []
    unmatched_books = []

    # Simple matching: source == "bank" vs source == "manual"/"csv_import"
    bank_txns = [t for t in txns if t.source in ("bank", "bank_import")]
    book_txns = [t for t in txns if t.source not in ("bank", "bank_import")]

    matched_book_ids: set[uuid.UUID] = set()

    for bt in bank_txns:
        found_match = False
        for bk in book_txns:
            if bk.id in matched_book_ids:
                continue
            # Match by amount and date (within 3 days)
            if (
                abs(bt.amount - bk.amount) < Decimal("0.01")
                and abs((bt.txn_date - bk.txn_date).days) <= 3
            ):
                matched.append(ReconciledItem(
                    id=bt.id,
                    transaction_date=bt.txn_date,
                    description=bt.description or "",
                    amount=bt.amount,
                    match_status="matched",
                    matched_transaction_id=bk.id,
                    confidence=Decimal("0.95"),
                ))
                matched_book_ids.add(bk.id)
                found_match = True
                break
        if not found_match:
            unmatched_bank.append(ReconciledItem(
                id=bt.id,
                transaction_date=bt.txn_date,
                description=bt.description or "",
                amount=bt.amount,
                match_status="unmatched_bank",
            ))

    for bk in book_txns:
        if bk.id not in matched_book_ids:
            unmatched_books.append(ReconciledItem(
                id=bk.id,
                transaction_date=bk.txn_date,
                description=bk.description or "",
                amount=bk.amount,
                match_status="unmatched_books",
            ))

    all_items = matched + unmatched_bank + unmatched_books

    bank_balance = sum(t.amount for t in bank_txns)
    book_balance = sum(t.amount for t in book_txns)

    return ReconciliationResult(
        id=uuid.uuid4(),
        run_date=datetime.utcnow(),
        period_start=start,
        period_end=end,
        bank_balance=bank_balance,
        book_balance=book_balance,
        difference=bank_balance - book_balance,
        matched_count=len(matched),
        unmatched_bank_count=len(unmatched_bank),
        unmatched_books_count=len(unmatched_books),
        items=all_items,
        status="completed" if not unmatched_bank and not unmatched_books else "needs_review",
    )


# ---------------------------------------------------------------------------
# GET /reconciliation/results — Get past reconciliation results
# ---------------------------------------------------------------------------

@router.get("/results", response_model=ReconciliationResultsList)
async def get_reconciliation_results(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get historical reconciliation results.

    In production this would fetch from a reconciliations table.
    Returns a placeholder for now.
    """
    # Placeholder result
    result = ReconciliationResult(
        id=uuid.uuid4(),
        run_date=datetime.utcnow(),
        period_start=date.today().replace(day=1),
        period_end=date.today(),
        bank_balance=Decimal("15000000"),
        book_balance=Decimal("14800000"),
        difference=Decimal("200000"),
        matched_count=42,
        unmatched_bank_count=3,
        unmatched_books_count=1,
        items=[],
        status="needs_review",
    )

    return ReconciliationResultsList(
        results=[result],
        total=1,
    )
