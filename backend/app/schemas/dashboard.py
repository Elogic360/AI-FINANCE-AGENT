"""Dashboard schemas for FinPilot AI."""

from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class HealthScoreResponse(BaseModel):
    """Business health score response."""
    model_config = ConfigDict(from_attributes=True)

    overall_score: int  # 0-100
    cash_health: int
    revenue_trend: int
    expense_control: int
    receivables: int
    recommendation: str


class DashboardSummaryResponse(BaseModel):
    """Dashboard summary for the current period."""
    model_config = ConfigDict(from_attributes=True)

    currency: str
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
