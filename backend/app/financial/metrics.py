"""
FinPilot AI — Financial Metrics Data Classes
─────────────────────────────────────────────
Deterministic metric containers used across the financial engine.

All monetary values use Python ``Decimal`` — never ``float``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any


# ──────────────────────────────────────────────────────────────────────
# Revenue
# ──────────────────────────────────────────────────────────────────────

@dataclass
class RevenueMetrics:
    """Revenue breakdown for a period."""
    org_id: uuid.UUID
    period_start: date
    period_end: date
    total_revenue: Decimal = Decimal("0")
    recurring_revenue: Decimal = Decimal("0")
    one_time_revenue: Decimal = Decimal("0")
    revenue_by_account: list[dict[str, Any]] = field(default_factory=list)
    transaction_count: int = 0
    average_transaction_value: Decimal = Decimal("0")
    month_over_month_growth: Decimal | None = None


# ──────────────────────────────────────────────────────────────────────
# Expenses
# ──────────────────────────────────────────────────────────────────────

@dataclass
class ExpenseMetrics:
    """Expense breakdown for a period."""
    org_id: uuid.UUID
    period_start: date
    period_end: date
    total_expenses: Decimal = Decimal("0")
    cost_of_goods_sold: Decimal = Decimal("0")
    operating_expenses: Decimal = Decimal("0")
    financial_expenses: Decimal = Decimal("0")
    other_expenses: Decimal = Decimal("0")
    expense_by_account: list[dict[str, Any]] = field(default_factory=list)
    expense_by_category: dict[str, Decimal] = field(default_factory=dict)
    top_expense_accounts: list[dict[str, Any]] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────
# Profitability
# ──────────────────────────────────────────────────────────────────────

@dataclass
class ProfitabilityMetrics:
    """Profitability analysis."""
    org_id: uuid.UUID
    period_start: date
    period_end: date
    gross_profit: Decimal = Decimal("0")
    gross_margin: Decimal = Decimal("0")
    operating_income: Decimal = Decimal("0")
    operating_margin: Decimal = Decimal("0")
    net_income: Decimal = Decimal("0")
    net_margin: Decimal = Decimal("0")
    ebitda: Decimal = Decimal("0")


# ──────────────────────────────────────────────────────────────────────
# P&L Statement
# ──────────────────────────────────────────────────────────────────────

@dataclass
class PLStatement:
    """Full Profit & Loss statement."""
    org_id: uuid.UUID
    period_start: date
    period_end: date
    revenue: Decimal = Decimal("0")
    cost_of_goods_sold: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    operating_expenses: Decimal = Decimal("0")
    operating_income: Decimal = Decimal("0")
    other_income: Decimal = Decimal("0")
    other_expenses: Decimal = Decimal("0")
    net_income: Decimal = Decimal("0")
    revenue_items: list[dict[str, Any]] = field(default_factory=list)
    expense_items: list[dict[str, Any]] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────
# Balance Sheet
# ──────────────────────────────────────────────────────────────────────

@dataclass
class BalanceSheet:
    """Statement of Financial Position."""
    org_id: uuid.UUID
    as_of_date: date
    total_assets: Decimal = Decimal("0")
    total_liabilities: Decimal = Decimal("0")
    total_equity: Decimal = Decimal("0")
    current_assets: Decimal = Decimal("0")
    non_current_assets: Decimal = Decimal("0")
    current_liabilities: Decimal = Decimal("0")
    non_current_liabilities: Decimal = Decimal("0")
    assets: list[dict[str, Any]] = field(default_factory=list)
    liabilities: list[dict[str, Any]] = field(default_factory=list)
    equity: list[dict[str, Any]] = field(default_factory=list)
    is_balanced: bool = False


# ──────────────────────────────────────────────────────────────────────
# Cash Flow
# ──────────────────────────────────────────────────────────────────────

@dataclass
class CashFlowStatement:
    """Cash flow statement."""
    org_id: uuid.UUID
    period_start: date
    period_end: date
    operating_activities: Decimal = Decimal("0")
    investing_activities: Decimal = Decimal("0")
    financing_activities: Decimal = Decimal("0")
    net_cash_flow: Decimal = Decimal("0")
    beginning_cash: Decimal = Decimal("0")
    ending_cash: Decimal = Decimal("0")
    details: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


@dataclass
class CashMetrics:
    """Cash position metrics."""
    org_id: uuid.UUID
    cash_balance: Decimal = Decimal("0")
    burn_rate_monthly: Decimal = Decimal("0")
    runway_months: Decimal | None = None
    daily_cash_change: Decimal = Decimal("0")


# ──────────────────────────────────────────────────────────────────────
# Working Capital
# ──────────────────────────────────────────────────────────────────────

@dataclass
class WorkingCapitalMetrics:
    """Working capital analysis."""
    org_id: uuid.UUID
    as_of_date: date
    current_assets: Decimal = Decimal("0")
    current_liabilities: Decimal = Decimal("0")
    working_capital: Decimal = Decimal("0")
    current_ratio: Decimal = Decimal("0")
    quick_ratio: Decimal = Decimal("0")


# ──────────────────────────────────────────────────────────────────────
# Receivables
# ──────────────────────────────────────────────────────────────────────

@dataclass
class ReceivablesMetrics:
    """Accounts receivable metrics."""
    org_id: uuid.UUID
    total_outstanding: Decimal = Decimal("0")
    current: Decimal = Decimal("0")
    overdue_30: Decimal = Decimal("0")
    overdue_60: Decimal = Decimal("0")
    overdue_90_plus: Decimal = Decimal("0")
    average_days_outstanding: Decimal = Decimal("0")
    invoices_count: int = 0
    overdue_count: int = 0


@dataclass
class ReceivablesReport:
    """Full receivables report."""
    org_id: uuid.UUID
    total_outstanding: Decimal = Decimal("0")
    current: Decimal = Decimal("0")
    overdue_30: Decimal = Decimal("0")
    overdue_60: Decimal = Decimal("0")
    overdue_90_plus: Decimal = Decimal("0")
    average_days_outstanding: Decimal = Decimal("0")
    invoices: list[dict[str, Any]] = field(default_factory=list)
    by_customer: list[dict[str, Any]] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────
# Payables
# ──────────────────────────────────────────────────────────────────────

@dataclass
class PayablesReport:
    """Accounts payable report."""
    org_id: uuid.UUID
    total_outstanding: Decimal = Decimal("0")
    current: Decimal = Decimal("0")
    overdue_30: Decimal = Decimal("0")
    overdue_60: Decimal = Decimal("0")
    overdue_90_plus: Decimal = Decimal("0")
    average_days_outstanding: Decimal = Decimal("0")
    bills: list[dict[str, Any]] = field(default_factory=list)
    by_vendor: list[dict[str, Any]] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────
# Inventory
# ──────────────────────────────────────────────────────────────────────

@dataclass
class InventoryMetrics:
    """Inventory metrics (if applicable)."""
    org_id: uuid.UUID
    inventory_value: Decimal = Decimal("0")
    inventory_turnover: Decimal = Decimal("0")
    days_inventory_outstanding: Decimal = Decimal("0")


# ──────────────────────────────────────────────────────────────────────
# Financial Ratios
# ──────────────────────────────────────────────────────────────────────

@dataclass
class FinancialRatios:
    """Comprehensive financial ratio analysis."""
    org_id: uuid.UUID
    as_of_date: date
    # Liquidity
    current_ratio: Decimal = Decimal("0")
    quick_ratio: Decimal = Decimal("0")
    cash_ratio: Decimal = Decimal("0")
    # Profitability
    gross_margin: Decimal = Decimal("0")
    operating_margin: Decimal = Decimal("0")
    net_margin: Decimal = Decimal("0")
    roe: Decimal = Decimal("0")          # Return on Equity
    roa: Decimal = Decimal("0")          # Return on Assets
    # Efficiency
    receivables_turnover: Decimal = Decimal("0")
    payables_turnover: Decimal = Decimal("0")
    asset_turnover: Decimal = Decimal("0")
    # Leverage
    debt_to_equity: Decimal = Decimal("0")
    debt_to_assets: Decimal = Decimal("0")
    interest_coverage: Decimal = Decimal("0")


# ──────────────────────────────────────────────────────────────────────
# Break-Even
# ──────────────────────────────────────────────────────────────────────

@dataclass
class BreakEvenAnalysis:
    """Break-even analysis."""
    org_id: uuid.UUID
    period_start: date
    period_end: date
    fixed_costs: Decimal = Decimal("0")
    variable_costs: Decimal = Decimal("0")
    total_revenue: Decimal = Decimal("0")
    contribution_margin: Decimal = Decimal("0")
    contribution_margin_ratio: Decimal = Decimal("0")
    break_even_revenue: Decimal = Decimal("0")
    break_even_units: Decimal = Decimal("0")
    margin_of_safety: Decimal = Decimal("0")
    margin_of_safety_ratio: Decimal = Decimal("0")
    is_above_breakeven: bool = False


# ──────────────────────────────────────────────────────────────────────
# Health Score
# ──────────────────────────────────────────────────────────────────────

@dataclass
class HealthScoreComponent:
    """Individual health score component."""
    name: str
    score: int  # 0-100
    weight: Decimal
    description: str = ""


@dataclass
class HealthScore:
    """Financial health score with component breakdown."""
    org_id: uuid.UUID
    overall_score: int  # 0-100
    components: list[HealthScoreComponent] = field(default_factory=list)
    recommendation: str = ""
    grade: str = ""  # A, B, C, D, F


# ──────────────────────────────────────────────────────────────────────
# Risk
# ──────────────────────────────────────────────────────────────────────

@dataclass
class Risk:
    """Detected financial risk."""
    category: str   # CASH_FLOW, PROFITABILITY, EXPENSE, RECEIVABLE, etc.
    severity: str   # low, medium, high, critical
    title: str
    evidence: str
    impact: str
    recommendation: str
    confidence: Decimal = Decimal("0.8")
    affected_amount: Decimal | None = None


# ──────────────────────────────────────────────────────────────────────
# Forecasting
# ──────────────────────────────────────────────────────────────────────

@dataclass
class CashFlowForecastPoint:
    """Single point in a cash flow forecast."""
    date: date
    projected_balance: Decimal
    projected_inflow: Decimal
    projected_outflow: Decimal
    confidence_lower: Decimal = Decimal("0")
    confidence_upper: Decimal = Decimal("0")


@dataclass
class CashFlowForecast:
    """Cash flow forecast."""
    org_id: uuid.UUID
    horizon_days: int
    current_balance: Decimal = Decimal("0")
    projected_end_balance: Decimal = Decimal("0")
    daily_forecast: list[CashFlowForecastPoint] = field(default_factory=list)
    average_daily_inflow: Decimal = Decimal("0")
    average_daily_outflow: Decimal = Decimal("0")
    risk_of_shortfall: bool = False
    shortfall_date: date | None = None
    confidence: str = "medium"


@dataclass
class RevenueForecastPoint:
    """Single point in a revenue forecast."""
    month: str  # YYYY-MM
    projected_revenue: Decimal
    confidence_lower: Decimal = Decimal("0")
    confidence_upper: Decimal = Decimal("0")


@dataclass
class RevenueForecast:
    """Revenue forecast."""
    org_id: uuid.UUID
    horizon_months: int
    historical_monthly_revenue: list[dict[str, Any]] = field(default_factory=list)
    forecast_points: list[RevenueForecastPoint] = field(default_factory=list)
    trend: str = "stable"  # growing, stable, declining
    average_monthly_revenue: Decimal = Decimal("0")
    projected_total: Decimal = Decimal("0")
    confidence: str = "medium"


@dataclass
class ScenarioResult:
    """Result of a what-if scenario."""
    org_id: uuid.UUID
    scenario_name: str
    base_net_income: Decimal = Decimal("0")
    projected_net_income: Decimal = Decimal("0")
    delta: Decimal = Decimal("0")
    delta_percent: Decimal = Decimal("0")
    assumptions: dict[str, Any] = field(default_factory=dict)
    monthly_projection: list[dict[str, Any]] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────
# Reconciliation
# ──────────────────────────────────────────────────────────────────────

@dataclass
class MatchedTransaction:
    """A matched pair of bank and ledger transactions."""
    bank_transaction: dict[str, Any]
    ledger_transaction: dict[str, Any]
    match_score: Decimal  # 0-1 confidence
    match_type: str  # exact, fuzzy, manual


@dataclass
class ReconciliationResult:
    """Bank reconciliation result."""
    org_id: uuid.UUID
    bank_account_id: uuid.UUID
    statement_balance: Decimal = Decimal("0")
    ledger_balance: Decimal = Decimal("0")
    difference: Decimal = Decimal("0")
    matched: list[MatchedTransaction] = field(default_factory=list)
    unmatched_bank: list[dict[str, Any]] = field(default_factory=list)
    unmatched_ledger: list[dict[str, Any]] = field(default_factory=list)
    is_reconciled: bool = False
    match_rate: Decimal = Decimal("0")
