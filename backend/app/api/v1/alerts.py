"""Alert routes — list and acknowledge."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.ai import Alert
from app.models.business import User
from app.schemas.alerts import AlertResponse
from app.schemas.common import PaginatedResponse

router = APIRouter()


class AcknowledgeResponse(BaseModel):
    id: uuid.UUID
    acknowledged: bool


# ---------------------------------------------------------------------------
# GET /alerts
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse[AlertResponse])
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List alerts with optional severity and acknowledgement filters."""
    base = select(Alert).where(Alert.business_id == current_user.business_id)

    if severity:
        base = base.where(Alert.severity == severity)
    if acknowledged is not None:
        base = base.where(Alert.acknowledged == acknowledged)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        base.order_by(Alert.created_at.desc()).offset(offset).limit(page_size)
    )
    items = result.scalars().all()
    pages = max(1, (total + page_size - 1) // page_size)

    return PaginatedResponse(
        items=[AlertResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


# ---------------------------------------------------------------------------
# POST /alerts/{id}/acknowledge
# ---------------------------------------------------------------------------

@router.post("/{alert_id}/acknowledge", response_model=AcknowledgeResponse)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark an alert as acknowledged."""
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.business_id == current_user.business_id,
        )
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.acknowledged = True
    await db.flush()

    return AcknowledgeResponse(id=alert.id, acknowledged=True)
