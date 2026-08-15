"""Financial reports — P&L, Balance Sheet, Cash Flow, Trial Balance."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.business import User
from app.schemas.reports import (
    PnLResponse,
    BalanceSheetResponse,
    CashFlowResponse,
    AccountBalance,
)
from app.services.reports_service import (
    get_profit_loss,
    get_balance_sheet,
    get_cash_flow,
    get_trial_balance,
)

router = APIRouter()


# Trial balance schemas (not in schemas/reports.py yet)
class TrialBalanceAccount(BaseModel):
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_type: str
    debit_total: Decimal
    credit_total: Decimal


class TrialBalanceReportResponse(BaseModel):
    as_of_date: Optional[str]
    accounts: list[TrialBalanceAccount]
    total_debits: Decimal
    total_credits: Decimal
    balanced: bool


# ---------------------------------------------------------------------------
# GET /reports/pnl
# ---------------------------------------------------------------------------

@router.get("/pnl", response_model=PnLResponse)
async def get_pnl_report(
    start_date: date = Query(..., description="Period start date"),
    end_date: date = Query(..., description="Period end date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Profit & Loss report for the given period."""
    data = await get_profit_loss(
        business_id=current_user.business_id,
        start_date=start_date,
        end_date=end_date,
        db=db,
    )

    return PnLResponse(
        period_start=str(data["period"]["start"]),
        period_end=str(data["period"]["end"]),
        currency="TZS",
        revenue=[
            AccountBalance(
                account_id=item["account_id"],
                account_code=item["code"],
                account_name=item["name"],
                account_type="revenue",
                debit_total=Decimal("0"),
                credit_total=item["amount"],
                balance=item["amount"],
            )
            for item in data["revenue_items"]
        ],
        total_revenue=data["revenue"],
        expenses=[
            AccountBalance(
                account_id=item["account_id"],
                account_code=item["code"],
                account_name=item["name"],
                account_type="expense",
                debit_total=item["amount"],
                credit_total=Decimal("0"),
                balance=item["amount"],
            )
            for item in data["expense_items"]
        ],
        total_expenses=data["cost_of_goods_sold"] + data["operating_expenses"],
        net_income=data["net_income"],
    )


# ---------------------------------------------------------------------------
# GET /reports/balance-sheet
# ---------------------------------------------------------------------------

@router.get("/balance-sheet", response_model=BalanceSheetResponse)
async def get_balance_sheet_report(
    as_of_date: date = Query(..., description="Balance sheet date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Balance Sheet as of a given date."""
    data = await get_balance_sheet(
        business_id=current_user.business_id,
        as_of_date=as_of_date,
        db=db,
    )

    def _format_items(items: list[dict], acct_type: str) -> list[AccountBalance]:
        return [
            AccountBalance(
                account_id=item["account_id"],
                account_code=item["code"],
                account_name=item["name"],
                account_type=acct_type,
                debit_total=item["balance"] if item["balance"] > 0 else Decimal("0"),
                credit_total=abs(item["balance"]) if item["balance"] < 0 else Decimal("0"),
                balance=item["balance"],
            )
            for item in items
        ]

    return BalanceSheetResponse(
        as_of_date=str(data["as_of_date"]),
        currency="TZS",
        assets=_format_items(data["assets"], "asset"),
        total_assets=data["total_assets"],
        liabilities=_format_items(data["liabilities"], "liability"),
        total_liabilities=data["total_liabilities"],
        equity=_format_items(data["equity"], "equity"),
        total_equity=data["total_equity"],
    )


# ---------------------------------------------------------------------------
# GET /reports/cash-flow
# ---------------------------------------------------------------------------

@router.get("/cash-flow", response_model=CashFlowResponse)
async def get_cash_flow_report(
    start_date: date = Query(..., description="Period start date"),
    end_date: date = Query(..., description="Period end date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cash Flow statement for the given period."""
    data = await get_cash_flow(
        business_id=current_user.business_id,
        start_date=start_date,
        end_date=end_date,
        db=db,
    )

    operating_items = [
        AccountBalance(
            account_id=uuid.UUID(int=0),  # synthetic — no single account
            account_code="OP",
            account_name=item["type"],
            account_type="revenue" if "inflow" in item["type"] else "expense",
            debit_total=item["amount"] if item["amount"] > 0 else Decimal("0"),
            credit_total=abs(item["amount"]) if item["amount"] < 0 else Decimal("0"),
            balance=item["amount"],
        )
        for item in data["details"]["operating"]
    ]
    investing_items = [
        AccountBalance(
            account_id=item.get("account_id", uuid.UUID(int=0)),
            account_code="INV",
            account_name=item["name"],
            account_type="asset",
            debit_total=item["amount"] if item["amount"] > 0 else Decimal("0"),
            credit_total=abs(item["amount"]) if item["amount"] < 0 else Decimal("0"),
            balance=item["amount"],
        )
        for item in data["details"]["investing"]
    ]
    financing_items = [
        AccountBalance(
            account_id=item.get("account_id", uuid.UUID(int=0)),
            account_code="FIN",
            account_name=item["name"],
            account_type="liability",
            debit_total=item["amount"] if item["amount"] > 0 else Decimal("0"),
            credit_total=abs(item["amount"]) if item["amount"] < 0 else Decimal("0"),
            balance=item["amount"],
        )
        for item in data["details"]["financing"]
    ]

    return CashFlowResponse(
        period_start=str(data["period"]["start"]),
        period_end=str(data["period"]["end"]),
        currency="TZS",
        operating=operating_items,
        total_operating=data["operating_activities"],
        investing=investing_items,
        total_investing=data["investing_activities"],
        financing=financing_items,
        total_financing=data["financing_activities"],
        net_cash_change=data["net_cash_flow"],
    )


# ---------------------------------------------------------------------------
# GET /reports/trial-balance
# ---------------------------------------------------------------------------

@router.get("/trial-balance", response_model=TrialBalanceReportResponse)
async def get_trial_balance_report(
    as_of_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trial balance showing debits and credits per account."""
    data = await get_trial_balance(
        business_id=current_user.business_id,
        db=db,
        as_of_date=as_of_date,
    )

    return TrialBalanceReportResponse(
        as_of_date=str(data["as_of_date"]) if data["as_of_date"] else None,
        accounts=[
            TrialBalanceAccount(
                account_id=acct["account_id"],
                account_code=acct["code"],
                account_name=acct["name"],
                account_type=acct["account_type"],
                debit_total=acct["debit_total"],
                credit_total=acct["credit_total"],
            )
            for acct in data["accounts"]
        ],
        total_debits=data["total_debits"],
        total_credits=data["total_credits"],
        balanced=data["balanced"],
    )
