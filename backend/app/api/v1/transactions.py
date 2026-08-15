"""Transaction API routes — CSV import, listing, and AI categorization."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.accounting import Transaction
from app.models.business import User
from app.schemas.transaction import TransactionCreate, TransactionResponse, TransactionImportResponse
from app.schemas.common import PaginatedResponse
from app.services.accounting_service import categorise_transaction, bulk_categorize_by_keywords

router = APIRouter()

REQUIRED_CSV_COLUMNS = {"date", "description", "amount"}


# ---------------------------------------------------------------------------
# POST /transactions/import — CSV upload via pandas
# ---------------------------------------------------------------------------

@router.post(
    "/import",
    response_model=TransactionImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_transactions(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import transactions from a CSV file using pandas.

    Expected CSV columns: date, description, amount, [currency], [counterparty], [source]
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are supported",
        )

    try:
        content = await file.read()
        df = pd.read_csv(StringIO(content.decode("utf-8-sig")))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse CSV: {exc}",
        )

    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()

    missing = REQUIRED_CSV_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required columns: {', '.join(sorted(missing))}",
        )

    imported = 0
    skipped = 0
    transaction_ids: list[uuid.UUID] = []

    for idx, row in df.iterrows():
        try:
            txn_date = pd.to_datetime(row["date"]).date()

            amount_raw = row["amount"]
            if pd.isna(amount_raw):
                skipped += 1
                continue
            amount = Decimal(str(amount_raw)).quantize(Decimal("0.01"))
            if amount == 0:
                skipped += 1
                continue

            currency = str(row.get("currency", "TZS") or "TZS").upper()[:3]
            source = str(row.get("source", "csv_import") or "csv_import")
            description = str(row["description"]) if pd.notna(row.get("description")) else None
            counterparty = str(row["counterparty"]) if pd.notna(row.get("counterparty")) else None

            txn = Transaction(
                business_id=current_user.business_id,
                source=source,
                txn_date=txn_date,
                description=description,
                amount=amount,
                currency=currency,
                counterparty=counterparty,
                status="pending",
            )
            db.add(txn)
            await db.flush()

            # Auto-categorize
            categorise_transaction(txn)
            transaction_ids.append(txn.id)
            imported += 1
        except Exception:
            skipped += 1

    return TransactionImportResponse(
        total_found=imported + skipped,
        imported=imported,
        skipped=skipped,
        transaction_ids=transaction_ids,
    )


# ---------------------------------------------------------------------------
# GET /transactions — paginated + filtered
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse[TransactionResponse])
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List transactions with pagination and optional filters."""
    base = select(Transaction).where(Transaction.business_id == current_user.business_id)

    if status_filter:
        base = base.where(Transaction.status == status_filter)
    if category:
        base = base.where(Transaction.ai_category == category)
    if date_from:
        base = base.where(Transaction.txn_date >= date_from)
    if date_to:
        base = base.where(Transaction.txn_date <= date_to)
    if search:
        base = base.where(Transaction.description.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        base.order_by(Transaction.txn_date.desc(), Transaction.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = result.scalars().all()
    pages = max(1, (total + page_size - 1) // page_size)

    return PaginatedResponse(
        items=[TransactionResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


# ---------------------------------------------------------------------------
# POST /transactions/{id}/categorize — AI-assigned category
# ---------------------------------------------------------------------------

@router.post("/{txn_id}/categorize", response_model=TransactionResponse)
async def categorize_transaction_route(
    txn_id: uuid.UUID,
    category: str = Query(..., min_length=1, max_length=100),
    confidence: Optional[float] = Query(None, ge=0, le=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually or AI-assigned category for a transaction."""
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == txn_id,
            Transaction.business_id == current_user.business_id,
        )
    )
    txn = result.scalar_one_or_none()
    if txn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    txn.ai_category = category
    txn.ai_confidence = Decimal(str(confidence)) if confidence is not None else None
    txn.status = "categorized"

    return TransactionResponse.model_validate(txn)


# ---------------------------------------------------------------------------
# POST /transactions/auto-categorize — bulk keyword-based categorization
# ---------------------------------------------------------------------------

@router.post("/auto-categorize")
async def auto_categorize_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk auto-categorize all pending transactions using keyword matching."""
    result = await bulk_categorize_by_keywords(db, current_user.business_id)
    return result
