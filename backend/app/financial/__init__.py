"""
FinPilot AI — Financial Engine
──────────────────────────────
Deterministic financial calculations for the FinPilot AI platform.

All calculations are performed with Python ``Decimal`` math and
SQLAlchemy database queries — **no LLM calls**.

Modules:
    engine          Core FinancialEngine class (revenue, expenses, P&L, balance sheet, etc.)
    accounting      Double-entry accounting (journal entries, GL, trial balance)
    health_score    Composite financial health scoring
    risk_engine     Automated financial risk detection
    forecast        Cash flow and revenue forecasting
    metrics         Data classes for all financial metrics
    reconciliation  Bank-to-ledger transaction matching
"""

from app.financial.engine import FinancialEngine
from app.financial.accounting import (
    create_journal_entry,
    validate_journal_entry,
    post_journal_entry,
    get_general_ledger,
    get_trial_balance,
    JournalLineData,
    JournalEntryData,
)
from app.financial.health_score import calculate_health_score
from app.financial.risk_engine import detect_risks
from app.financial.forecast import forecast_cash_flow, forecast_revenue, run_scenario
from app.financial.reconciliation import reconcile_bank_transactions, match_transactions
from app.financial.metrics import (
    RevenueMetrics,
    ExpenseMetrics,
    ProfitabilityMetrics,
    PLStatement,
    BalanceSheet,
    CashFlowStatement,
    CashMetrics,
    WorkingCapitalMetrics,
    ReceivablesMetrics,
    ReceivablesReport,
    PayablesReport,
    InventoryMetrics,
    FinancialRatios,
    BreakEvenAnalysis,
    HealthScore,
    HealthScoreComponent,
    Risk,
    CashFlowForecast,
    CashFlowForecastPoint,
    RevenueForecast,
    RevenueForecastPoint,
    ScenarioResult,
    MatchedTransaction,
    ReconciliationResult,
)

__all__ = [
    # Engine
    "FinancialEngine",
    # Accounting
    "create_journal_entry",
    "validate_journal_entry",
    "post_journal_entry",
    "get_general_ledger",
    "get_trial_balance",
    "JournalLineData",
    "JournalEntryData",
    # Health Score
    "calculate_health_score",
    # Risk
    "detect_risks",
    # Forecasting
    "forecast_cash_flow",
    "forecast_revenue",
    "run_scenario",
    # Reconciliation
    "reconcile_bank_transactions",
    "match_transactions",
    # Metrics
    "RevenueMetrics",
    "ExpenseMetrics",
    "ProfitabilityMetrics",
    "PLStatement",
    "BalanceSheet",
    "CashFlowStatement",
    "CashMetrics",
    "WorkingCapitalMetrics",
    "ReceivablesMetrics",
    "ReceivablesReport",
    "PayablesReport",
    "InventoryMetrics",
    "FinancialRatios",
    "BreakEvenAnalysis",
    "HealthScore",
    "HealthScoreComponent",
    "Risk",
    "CashFlowForecast",
    "CashFlowForecastPoint",
    "RevenueForecast",
    "RevenueForecastPoint",
    "ScenarioResult",
    "MatchedTransaction",
    "ReconciliationResult",
]
