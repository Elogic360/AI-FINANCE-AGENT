"""Reconciliation schemas for FinPilot AI."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ReconciliationRunRequest(BaseModel):
    """Request to run bank reconciliation."""
    bank_account_id: Optional[uuid.UUID] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class ReconciledItem(BaseModel):
    """A single matched or unmatched item."""
    id: uuid.UUID
    transaction_date: date
    description: str
    amount: Decimal
    match_status: str  # matched | unmatched_bank | unmatched_books
    matched_transaction_id: Optional[uuid.UUID] = None
    confidence: Optional[Decimal] = None


class ReconciliationResult(BaseModel):
    """Result of a reconciliation run."""
    id: uuid.UUID
    run_date: datetime
    period_start: date
    period_end: date
    bank_balance: Decimal
    book_balance: Decimal
    difference: Decimal
    matched_count: int
    unmatched_bank_count: int
    unmatched_books_count: int
    items: list[ReconciledItem]
    status: str  # completed | in_progress | needs_review


class ReconciliationResultsList(BaseModel):
    """List of reconciliation results."""
    results: list[ReconciliationResult]
    total: int
