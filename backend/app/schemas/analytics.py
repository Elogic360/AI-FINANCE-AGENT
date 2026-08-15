"""Analytics schemas for FinPilot AI — all amounts in TZS."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Dashboard aggregate
# ---------------------------------------------------------------------------

class DashboardData(BaseModel):
    """Full dashboard payload."""
    currency: str = "TZS"
    period_label: str
    total_revenue: Decimal
    total_expenses: Decimal
    net_income: Decimal
    cash_balance: Decimal
    accounts_receivable: Decimal
    accounts_payable: Decimal
    transaction_count: int
    pending_invoices: int
    overdue_invoices: int
    active_alerts: int
    monthly_revenue: list[dict]
    monthly_expenses: list[dict]
    top_expense_categories: list[dict]


# ---------------------------------------------------------------------------
# P&L
# ---------------------------------------------------------------------------

class PnLLineItem(BaseModel):
    account_code: str
    account_name: str
    amount: Decimal


class ProfitLossResponse(BaseModel):
    currency: str = "TZS"
    period_start: date
    period_end: date
    revenue_lines: list[PnLLineItem]
    expense_lines: list[PnLLineItem]
    total_revenue: Decimal
    total_expenses: Decimal
    gross_profit: Decimal
    net_income: Decimal


# ---------------------------------------------------------------------------
# Balance Sheet
# ---------------------------------------------------------------------------

class BalanceSheetLine(BaseModel):
    account_code: str
    account_name: str
    balance: Decimal


class BalanceSheetResponse(BaseModel):
    currency: str = "TZS"
    as_of_date: date
    assets: list[BalanceSheetLine]
    liabilities: list[BalanceSheetLine]
    equity: list[BalanceSheetLine]
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal


# ---------------------------------------------------------------------------
# Cash Flow
# ---------------------------------------------------------------------------

class CashFlowLine(BaseModel):
    category: str
    description: str
    amount: Decimal


class CashFlowResponse(BaseModel):
    currency: str = "TZS"
    period_start: date
    period_end: date
    operating: list[CashFlowLine]
    investing: list[CashFlowLine]
    financing: list[CashFlowLine]
    net_operating: Decimal
    net_investing: Decimal
    net_financing: Decimal
    net_change: Decimal


# ---------------------------------------------------------------------------
# AR / AP Aging
# ---------------------------------------------------------------------------

class AgingBucket(BaseModel):
    current: Decimal = Decimal("0")
    days_1_30: Decimal = Decimal("0")
    days_31_60: Decimal = Decimal("0")
    days_61_90: Decimal = Decimal("0")
    over_90: Decimal = Decimal("0")


class AgingLineItem(BaseModel):
    id: uuid.UUID
    name: str
    invoice_number: Optional[str] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    total: Decimal
    status: str
    days_overdue: int


class AgingReport(BaseModel):
    currency: str = "TZS"
    as_of_date: date
    summary: AgingBucket
    items: list[AgingLineItem]
    total_outstanding: Decimal


# ---------------------------------------------------------------------------
# Forecast
# ---------------------------------------------------------------------------

class ForecastPoint(BaseModel):
    date: date
    projected_amount: Decimal
    confidence_low: Decimal
    confidence_high: Decimal


class ForecastResponse(BaseModel):
    currency: str = "TZS"
    forecast_type: str
    horizon_days: int
    data_points: list[ForecastPoint]
    confidence: str
    generated_at: datetime


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------

class RiskItem(BaseModel):
    risk_type: str
    severity: str  # info | warning | critical
    title: str
    detail: str
    recommendation: str


class RiskAnalysisResponse(BaseModel):
    overall_risk_level: str  # low | medium | high | critical
    risks: list[RiskItem]
    analyzed_at: datetime


# ---------------------------------------------------------------------------
# All metrics
# ---------------------------------------------------------------------------

class AllMetricsResponse(BaseModel):
    """Aggregated metrics for the full analytics page."""
    health_score: int
    revenue_mtd: Decimal
    expenses_mtd: Decimal
    net_income_mtd: Decimal
    cash_balance: Decimal
    ar_total: Decimal
    ap_total: Decimal
    overdue_invoices: int
    pending_transactions: int
    currency: str = "TZS"
