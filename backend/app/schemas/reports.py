"""Financial report schemas for FinPilot AI."""

import uuid
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class AccountBalance(BaseModel):
    """Single account balance line."""
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_type: str
    debit_total: Decimal
    credit_total: Decimal
    balance: Decimal


class PnLResponse(BaseModel):
    """Profit & Loss report response."""
    model_config = ConfigDict(from_attributes=True)

    period_start: str
    period_end: str
    currency: str
    revenue: list[AccountBalance]
    total_revenue: Decimal
    expenses: list[AccountBalance]
    total_expenses: Decimal
    net_income: Decimal


class BalanceSheetResponse(BaseModel):
    """Balance sheet report response."""
    model_config = ConfigDict(from_attributes=True)

    as_of_date: str
    currency: str
    assets: list[AccountBalance]
    total_assets: Decimal
    liabilities: list[AccountBalance]
    total_liabilities: Decimal
    equity: list[AccountBalance]
    total_equity: Decimal


class CashFlowResponse(BaseModel):
    """Cash flow statement response."""
    model_config = ConfigDict(from_attributes=True)

    period_start: str
    period_end: str
    currency: str
    operating: list[AccountBalance]
    total_operating: Decimal
    investing: list[AccountBalance]
    total_investing: Decimal
    financing: list[AccountBalance]
    total_financing: Decimal
    net_cash_change: Decimal
