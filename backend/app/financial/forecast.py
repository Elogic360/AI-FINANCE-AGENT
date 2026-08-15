"""
FinPilot AI — Forecasting Engine
─────────────────────────────────
Deterministic financial forecasting using historical data patterns:

* Cash flow forecast (moving average projection)
* Revenue forecast (trend-based projection)
* What-if scenario analysis

All projections are based on historical averages and trends —
**no LLM calls, no stochastic models**.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import ChartOfAccounts, JournalEntry, JournalLine

from app.financial.metrics import (
    CashFlowForecast,
    CashFlowForecastPoint,
    RevenueForecast,
    RevenueForecastPoint,
    ScenarioResult,
)
from app.financial.engine import FinancialEngine, _safe_ratio, _pct, _ZERO, _d


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

async def _monthly_revenue(
    db: AsyncSession,
    org_id: uuid.UUID,
    months: int = 6,
) -> list[dict[str, Any]]:
    """
    Return monthly revenue totals for the last *months* months.

    Each item: {"month": "YYYY-MM", "revenue": Decimal}
    """
    today = date.today()
    results: list[dict[str, Any]] = []

    for i in range(months):
        # Calculate month boundaries
        end = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1) if i > 0 else today
        if i > 0:
            start = end
            end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        else:
            start = (today.replace(day=1) - timedelta(days=(months - 1) * 30)).replace(day=1)

        if i == 0:
            start = today.replace(day=1)
            end = today

        stmt = (
            select(
                func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), _ZERO).label("revenue"),
            )
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
            .where(
                ChartOfAccounts.business_id == org_id,
                ChartOfAccounts.account_type == "revenue",
                JournalEntry.is_draft.is_(False),
                JournalEntry.entry_date >= start,
                JournalEntry.entry_date <= end,
            )
        )
        row = (await db.execute(stmt)).one()
        month_label = start.strftime("%Y-%m")
        results.append({"month": month_label, "revenue": abs(row.revenue)})

    results.reverse()  # Chronological order
    return results


async def _daily_cash_movements(
    db: AsyncSession,
    org_id: uuid.UUID,
    days: int = 30,
) -> tuple[list[Decimal], list[Decimal]]:
    """
    Return (daily_inflows, daily_outflows) for the last *days* days.

    Inflows = revenue credits; Outflows = expense debits.
    """
    today = date.today()
    inflows: list[Decimal] = []
    outflows: list[Decimal] = []

    for i in range(days):
        day = today - timedelta(days=i)

        # Inflow: revenue credits on this day
        inflow_stmt = (
            select(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), _ZERO).label("amt"))
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
            .where(
                ChartOfAccounts.business_id == org_id,
                ChartOfAccounts.account_type == "revenue",
                JournalEntry.is_draft.is_(False),
                JournalEntry.entry_date == day,
            )
        )
        inflow = abs((await db.execute(inflow_stmt)).scalar() or _ZERO)

        # Outflow: expense debits on this day
        outflow_stmt = (
            select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), _ZERO).label("amt"))
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
            .where(
                ChartOfAccounts.business_id == org_id,
                ChartOfAccounts.account_type == "expense",
                JournalEntry.is_draft.is_(False),
                JournalEntry.entry_date == day,
            )
        )
        outflow = (await db.execute(outflow_stmt)).scalar() or _ZERO

        inflows.append(inflow)
        outflows.append(outflow)

    inflows.reverse()
    outflows.reverse()
    return inflows, outflows


async def _current_cash_balance(db: AsyncSession, org_id: uuid.UUID) -> Decimal:
    """Get current cash/bank balance from the chart of accounts."""
    cash_accts = (
        select(ChartOfAccounts.id)
        .where(
            ChartOfAccounts.business_id == org_id,
            ChartOfAccounts.account_type == "asset",
        )
    )
    all_assets = (await db.execute(cash_accts)).all()
    cash_ids = set()

    for a in all_assets:
        # We need the name to check for cash/bank
        pass

    # Simpler approach: query directly
    stmt = (
        select(
            func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), _ZERO).label("balance"),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
        .where(
            ChartOfAccounts.business_id == org_id,
            ChartOfAccounts.account_type == "asset",
            ChartOfAccounts.name.ilike("%cash%"),
            JournalEntry.is_draft.is_(False),
        )
    )
    cash_balance = (await db.execute(stmt)).scalar() or _ZERO

    bank_stmt = (
        select(
            func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), _ZERO).label("balance"),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .join(ChartOfAccounts, ChartOfAccounts.id == JournalLine.account_id)
        .where(
            ChartOfAccounts.business_id == org_id,
            ChartOfAccounts.account_type == "asset",
            ChartOfAccounts.name.ilike("%bank%"),
            JournalEntry.is_draft.is_(False),
        )
    )
    bank_balance = (await db.execute(bank_stmt)).scalar() or _ZERO

    return cash_balance + bank_balance


# ──────────────────────────────────────────────────────────────────────
# 1. Cash Flow Forecast
# ──────────────────────────────────────────────────────────────────────

async def forecast_cash_flow(
    db: AsyncSession,
    org_id: uuid.UUID,
    days: int = 90,
) -> CashFlowForecast:
    """
    Forecast cash flow for the next *days* days using a simple
    moving-average projection of daily inflows and outflows.

    Uses the last 30 days of actual data to project forward.
    """
    engine = FinancialEngine()
    current_balance = await _current_cash_balance(db, org_id)

    # Get historical daily movements
    daily_inflows, daily_outflows = await _daily_cash_movements(db, org_id, days=30)

    # Calculate averages
    active_inflow_days = [d for d in daily_inflows if d > _ZERO]
    active_outflow_days = [d for d in daily_outflows if d > _ZERO]

    avg_inflow = sum(daily_inflows) / Decimal(len(daily_inflows)) if daily_inflows else _ZERO
    avg_outflow = sum(daily_outflows) / Decimal(len(daily_outflows)) if daily_outflows else _ZERO

    # Calculate standard deviation for confidence bands
    if len(daily_inflows) > 1:
        mean_i = avg_inflow
        variance_i = sum((d - mean_i) ** 2 for d in daily_inflows) / Decimal(len(daily_inflows) - 1)
        std_i = variance_i.sqrt() if variance_i > 0 else _ZERO
    else:
        std_i = _ZERO

    if len(daily_outflows) > 1:
        mean_o = avg_outflow
        variance_o = sum((d - mean_o) ** 2 for d in daily_outflows) / Decimal(len(daily_outflows) - 1)
        std_o = variance_o.sqrt() if variance_o > 0 else _ZERO
    else:
        std_o = _ZERO

    # Project forward
    today = date.today()
    running_balance = current_balance
    forecast_points: list[CashFlowForecastPoint] = []
    shortfall_date: date | None = None

    for day_offset in range(1, days + 1):
        forecast_date = today + timedelta(days=day_offset)

        # Add some weekly seasonality (lower on weekends)
        weekday = forecast_date.weekday()
        if weekday >= 5:  # Weekend
            day_inflow = avg_inflow * Decimal("0.3")
            day_outflow = avg_outflow * Decimal("0.5")
        else:
            day_inflow = avg_inflow
            day_outflow = avg_outflow

        running_balance += day_inflow - day_outflow

        lower_bound = running_balance - std_i - std_o
        upper_bound = running_balance + std_i + std_o

        forecast_points.append(CashFlowForecastPoint(
            date=forecast_date,
            projected_balance=running_balance.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            projected_inflow=day_inflow.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            projected_outflow=day_outflow.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            confidence_lower=lower_bound.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            confidence_upper=upper_bound.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        ))

        if running_balance < _ZERO and shortfall_date is None:
            shortfall_date = forecast_date

    # Determine confidence level based on data quality
    if len(daily_inflows) >= 20 and all(d > _ZERO for d in daily_inflows[-7:]):
        confidence = "high"
    elif len(daily_inflows) >= 10:
        confidence = "medium"
    else:
        confidence = "low"

    return CashFlowForecast(
        org_id=org_id,
        horizon_days=days,
        current_balance=current_balance,
        projected_end_balance=running_balance.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        daily_forecast=forecast_points,
        average_daily_inflow=avg_inflow.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        average_daily_outflow=avg_outflow.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        risk_of_shortfall=shortfall_date is not None,
        shortfall_date=shortfall_date,
        confidence=confidence,
    )


# ──────────────────────────────────────────────────────────────────────
# 2. Revenue Forecast
# ──────────────────────────────────────────────────────────────────────

async def forecast_revenue(
    db: AsyncSession,
    org_id: uuid.UUID,
    months: int = 3,
) -> RevenueForecast:
    """
    Forecast revenue for the next *months* months using linear trend
    extrapolation from the last 6 months of data.
    """
    historical = await _monthly_revenue(db, org_id, months=6)

    if not historical or all(m["revenue"] == _ZERO for m in historical):
        return RevenueForecast(
            org_id=org_id,
            horizon_months=months,
            historical_monthly_revenue=historical,
            trend="stable",
            confidence="low",
        )

    revenues = [m["revenue"] for m in historical]
    avg_revenue = sum(revenues) / Decimal(len(revenues))

    # Simple linear regression for trend
    n = Decimal(len(revenues))
    x_values = [Decimal(i) for i in range(len(revenues))]
    x_mean = sum(x_values) / n
    y_mean = avg_revenue

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, revenues))
    denominator = sum((x - x_mean) ** 2 for x in x_values)

    if denominator > _ZERO:
        slope = numerator / denominator
    else:
        slope = _ZERO

    # Determine trend
    if slope > avg_revenue * Decimal("0.05"):
        trend = "growing"
    elif slope < -avg_revenue * Decimal("0.05"):
        trend = "declining"
    else:
        trend = "stable"

    # Project forward
    forecast_points: list[RevenueForecastPoint] = []
    last_x = Decimal(len(revenues) - 1)
    projected_total = _ZERO

    today = date.today()
    for i in range(1, months + 1):
        projected_x = last_x + Decimal(i)
        projected_value = y_mean + slope * (projected_x - x_mean)
        projected_value = max(_ZERO, projected_value)  # Revenue can't be negative

        # Confidence band (±15% for stable, wider for volatile)
        band_width = Decimal("0.15")
        if len(revenues) > 1:
            variance = sum((r - avg_revenue) ** 2 for r in revenues) / Decimal(len(revenues) - 1)
            std_dev = variance.sqrt() if variance > 0 else _ZERO
            band_pct = min(Decimal("0.30"), _safe_ratio(std_dev, avg_revenue) + Decimal("0.05"))
        else:
            band_pct = band_width

        forecast_month = (today + timedelta(days=i * 30)).strftime("%Y-%m")

        forecast_points.append(RevenueForecastPoint(
            month=forecast_month,
            projected_revenue=projected_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            confidence_lower=(projected_value * (1 - band_pct)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            confidence_upper=(projected_value * (1 + band_pct)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        ))
        projected_total += projected_value

    # Confidence based on data quality
    if len(revenues) >= 6 and all(r > _ZERO for r in revenues):
        confidence = "high"
    elif len(revenues) >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    return RevenueForecast(
        org_id=org_id,
        horizon_months=months,
        historical_monthly_revenue=historical,
        forecast_points=forecast_points,
        trend=trend,
        average_monthly_revenue=avg_revenue.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        projected_total=projected_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        confidence=confidence,
    )


# ──────────────────────────────────────────────────────────────────────
# 3. Scenario Analysis
# ──────────────────────────────────────────────────────────────────────

async def run_scenario(
    db: AsyncSession,
    org_id: uuid.UUID,
    changes: dict[str, Any],
) -> ScenarioResult:
    """
    Run a what-if scenario analysis.

    Parameters
    ----------
    changes : dict
        Keys can include:
        - ``revenue_change_pct`` : Decimal  (e.g., 10 = 10% increase)
        - ``expense_change_pct`` : Decimal
        - ``new_fixed_cost``     : Decimal (monthly)
        - ``revenue_change_abs`` : Decimal (absolute monthly change)
        - ``expense_change_abs`` : Decimal (absolute monthly change)

    Returns the projected impact on net income.
    """
    engine = FinancialEngine()
    today = date.today()
    period = (today - timedelta(days=90), today)

    # Base case
    pl = await engine.calculate_profit_loss(db, org_id, period)

    base_revenue = pl.revenue
    base_expenses = pl.cost_of_goods_sold + pl.operating_expenses + pl.other_expenses
    base_net_income = pl.net_income

    # Apply changes
    revenue_change = changes.get("revenue_change_pct", _ZERO)
    expense_change = changes.get("expense_change_pct", _ZERO)
    new_fixed_cost = changes.get("new_fixed_cost", _ZERO)
    revenue_abs = changes.get("revenue_change_abs", _ZERO)
    expense_abs = changes.get("expense_change_abs", _ZERO)

    projected_revenue = base_revenue * (1 + _d(revenue_change) / Decimal("100")) + _d(revenue_abs)
    projected_expenses = base_expenses * (1 + _d(expense_change) / Decimal("100")) + _d(expense_abs) + _d(new_fixed_cost)
    projected_net_income = projected_revenue - projected_expenses

    delta = projected_net_income - base_net_income
    delta_pct = _pct(delta, abs(base_net_income)) if base_net_income != _ZERO else _ZERO

    # Monthly projection for 6 months
    monthly_projection: list[dict[str, Any]] = []
    for i in range(6):
        month_label = (today + timedelta(days=(i + 1) * 30)).strftime("%Y-%m")
        monthly_projection.append({
            "month": month_label,
            "projected_revenue": (projected_revenue / Decimal("3")).quantize(Decimal("0.01")),
            "projected_expenses": (projected_expenses / Decimal("3")).quantize(Decimal("0.01")),
            "projected_net_income": (projected_net_income / Decimal("3")).quantize(Decimal("0.01")),
        })

    return ScenarioResult(
        org_id=org_id,
        scenario_name="Custom Scenario",
        base_net_income=base_net_income,
        projected_net_income=projected_net_income.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        delta=delta.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        delta_percent=delta_pct,
        assumptions=changes,
        monthly_projection=monthly_projection,
    )
