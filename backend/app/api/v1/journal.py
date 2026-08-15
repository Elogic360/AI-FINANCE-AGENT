"""Journal entry routes — create drafts, approve, and list."""

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.accounting import JournalEntry, JournalLine
from app.models.business import User
from app.schemas.journal import JournalEntryCreate, JournalEntryResponse, JournalLineCreate
from app.schemas.common import PaginatedResponse
from app.services.journal_service import create_draft_entry, approve_entry

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /journal-entries — create draft
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_journal_entry_route(
    body: JournalEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a journal entry in draft status. Lines must balance (debits == credits)."""
    try:
        lines_data = [
            {
                "account_id": line.account_id,
                "debit": line.debit,
                "credit": line.credit,
            }
            for line in body.lines
        ]
        entry = await create_draft_entry(
            db,
            business_id=current_user.business_id,
            entry_date=body.entry_date,
            lines=lines_data,
            memo=body.memo,
            transaction_id=body.transaction_id,
            created_by=current_user.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    # Reload with lines
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.id == entry.id)
    )
    entry = result.scalar_one()

    return JournalEntryResponse.model_validate(entry)


# ---------------------------------------------------------------------------
# POST /journal-entries/{id}/approve
# ---------------------------------------------------------------------------

@router.post("/{entry_id}/approve", response_model=JournalEntryResponse)
async def approve_journal_entry_route(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a draft journal entry (set is_draft=False)."""
    try:
        entry = await approve_entry(
            db, entry_id, approved_by=current_user.email
        )
    except ValueError as exc:
        detail = str(exc)
        code = status.HTTP_404_NOT_FOUND if "not found" in detail.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=detail)

    # Reload with lines
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.id == entry.id)
    )
    entry = result.scalar_one()

    return JournalEntryResponse.model_validate(entry)


# ---------------------------------------------------------------------------
# GET /journal-entries — list
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse[JournalEntryResponse])
async def list_journal_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_draft: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List journal entries with pagination."""
    base = select(JournalEntry).where(
        JournalEntry.business_id == current_user.business_id
    )

    if is_draft is not None:
        base = base.where(JournalEntry.is_draft == is_draft)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        base.options(selectinload(JournalEntry.lines))
        .order_by(JournalEntry.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    entries = result.scalars().unique().all()
    pages = max(1, (total + page_size - 1) // page_size)

    return PaginatedResponse(
        items=[JournalEntryResponse.model_validate(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
