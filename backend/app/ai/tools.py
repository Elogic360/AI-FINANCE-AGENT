"""
FinPilot AI Agent Tools — the ONLY interface between runtime agents and the ledger.

All tools are read-only or draft-only. No execute_* tools exist by design.
This module contains MOCK implementations that return realistic placeholder data.
Real database integration will be added later.

Tool categories:
- READ tools: Query business data (profiles, accounts, transactions, reports)
- DRAFT tools: Propose actions that require human approval
"""

from decimal import Decimal
from typing import Any
import uuid
import random
from datetime import datetime, timedelta


# ── Mock data constants ────────────────────────────────────────────────────

_MOCK_ORG_ID = "org_001_kilimanjaro_electronics"
_MOCK_CURRENCY = "TZS"

_MOCK_BUSINESS_PROFILE = {
    "id": _MOCK_ORG_ID,
    "name": "Kilimanjaro Electronics Ltd",
    "trading_name": "KiliElectro",
    "country": "TZ",
    "currency": _MOCK_CURRENCY,
    "industry": "Retail — Electronics",
    "registration_number": "TZ-2023-REG-45678",
    "tin_number": "123-456-789",
    "vat_registered": True,
    "fiscal_year_start": "01-01",
    "created_at": "2023-03-15T00:00:00Z",
    "owner": "John Mwangi",
    "employees": 12,
    "address": "Samora Avenue, Dar es Salaam",
    "phone": "+255 22 212 3456",
    "email": "info@kilielectro.co.tz",
}

_MOCK_ACCOUNTS = [
    {"id": "acc_1000", "code": "1000", "name": "Cash on Hand", "type": "asset", "balance": 2500000},
    {"id": "acc_1010", "code": "1010", "name": "CRDB Bank Account", "type": "asset", "balance": 28400000},
    {"id": "acc_1020", "code": "1020", "name": "M-Pesa Business", "type": "asset", "balance": 4200000},
    {"id": "acc_1100", "code": "1100", "name": "Accounts Receivable", "type": "asset", "balance": 8700000},
    {"id": "acc_1200", "code": "1200", "name": "Inventory", "type": "asset", "balance": 15600000},
    {"id": "acc_1500", "code": "1500", "name": "Office Equipment", "type": "asset", "balance": 3200000},
    {"id": "acc_2000", "code": "2000", "name": "Accounts Payable", "type": "liability", "balance": 6800000},
    {"id": "acc_2100", "code": "2100", "name": "VAT Payable", "type": "liability", "balance": 1809000},
    {"id": "acc_2200", "code": "2200", "name": "Employee Benefits Payable", "type": "liability", "balance": 950000},
    {"id": "acc_2500", "code": "2500", "name": "Bank Loan", "type": "liability", "balance": 10000000},
    {"id": "acc_3000", "code": "3000", "name": "Owner's Equity", "type": "equity", "balance": 25000000},
    {"id": "acc_3100", "code": "3100", "name": "Retained Earnings", "type": "equity", "balance": 9950000},
    {"id": "acc_4000", "code": "4000", "name": "Sales Revenue", "type": "revenue", "balance": 45200000},
    {"id": "acc_4100", "code": "4100", "name": "Service Revenue", "type": "revenue", "balance": 3800000},
    {"id": "acc_5000", "code": "5000", "name": "Cost of Goods Sold", "type": "expense", "balance": 27120000},
    {"id": "acc_6000", "code": "6000", "name": "Rent Expense", "type": "expense", "balance": 4800000},
    {"id": "acc_6100", "code": "6100", "name": "Salaries Expense", "type": "expense", "balance": 7200000},
    {"id": "acc_6200", "code": "6200", "name": "Utilities Expense", "type": "expense", "balance": 1200000},
    {"id": "acc_6300", "code": "6300", "name": "Transport Expense", "type": "expense", "balance": 900000},
    {"id": "acc_6400", "code": "6400", "name": "Marketing Expense", "type": "expense", "balance": 600000},
]

_MOCK_TRANSACTIONS = [
    {
        "id": str(uuid.uuid4()),
        "date": "2024-08-15",
        "description": "Samsung Galaxy A54 sale to Serengeti Trading",
        "amount": 8500000,
        "currency": _MOCK_CURRENCY,
        "type": "income",
        "category": "Sales Revenue",
        "account_code": "4000",
        "counterparty": "Serengeti Trading Co.",
        "status": "completed",
        "reference": "INV-2024-0156",
        "payment_method": "bank_transfer",
    },
    {
        "id": str(uuid.uuid4()),
        "date": "2024-08-14",
        "description": "Monthly rent payment — Samora Avenue office",
        "amount": 400000,
        "currency": _MOCK_CURRENCY,
        "type": "expense",
        "category": "Rent Expense",
        "account_code": "6000",
        "counterparty": "Dar Properties Ltd",
        "status": "completed",
        "reference": "RENT-AUG-2024",
        "payment_method": "bank_transfer",
    },
    {
        "id": str(uuid.uuid4()),
        "date": "2024-08-13",
        "description": "Bulk USB-C cables purchase from Shenzhen Direct",
        "amount": 2400000,
        "currency": _MOCK_CURRENCY,
        "type": "expense",
        "category": "Cost of Goods Sold",
        "account_code": "5000",
        "counterparty": "Shenzhen Direct Imports",
        "status": "completed",
        "reference": "PO-2024-0089",
        "payment_method": "bank_transfer",
    },
    {
        "id": str(uuid.uuid4()),
        "date": "2024-08-12",
        "description": "iPhone accessories sale — walk-in customer",
        "amount": 450000,
        "currency": _MOCK_CURRENCY,
        "type": "income",
        "category": "Sales Revenue",
        "account_code": "4000",
        "counterparty": "Walk-in Customer",
        "status": "completed",
        "reference": "POS-2024-3421",
        "payment_method": "mpesa",
    },
    {
        "id": str(uuid.uuid4()),
        "date": "2024-08-12",
        "description": "Employee salary — August 2024 batch",
        "amount": 600000,
        "currency": _MOCK_CURRENCY,
        "type": "expense",
        "category": "Salaries Expense",
        "account_code": "6100",
        "counterparty": "Staff Payroll",
        "status": "completed",
        "reference": "PAY-AUG-2024",
        "payment_method": "bank_transfer",
    },
    {
        "id": str(uuid.uuid4()),
        "date": "2024-08-11",
        "description": "Samsung TV sale to Zanzibar Hotel Group",
        "amount": 3200000,
        "currency": _MOCK_CURRENCY,
        "type": "income",
        "category": "Sales Revenue",
        "account_code": "4000",
        "counterparty": "Zanzibar Hotel Group",
        "status": "pending",
        "reference": "INV-2024-0155",
        "payment_method": "bank_transfer",
    },
    {
        "id": str(uuid.uuid4()),
        "date": "2024-08-10",
        "description": "Facebook ads — August campaign",
        "amount": 150000,
        "currency": _MOCK_CURRENCY,
        "type": "expense",
        "category": "Marketing Expense",
        "account_code": "6400",
        "counterparty": "Meta Platforms",
        "status": "completed",
        "reference": "MKT-AUG-001",
        "payment_method": "credit_card",
    },
    {
        "id": str(uuid.uuid4()),
        "date": "2024-08-09",
        "description": "TANESCO electricity bill — July 2024",
        "amount": 280000,
        "currency": _MOCK_CURRENCY,
        "type": "expense",
        "category": "Utilities Expense",
        "account_code": "6200",
        "counterparty": "TANESCO",
        "status": "completed",
        "reference": "UTIL-JUL-2024",
        "payment_method": "mpesa",
    },
]


# ── READ tools ──────────────────────────────────────────────────────────────

async def get_business_profile(org_id: str) -> dict:
    """Return business name, currency, country, creation date."""
    return {**_MOCK_BUSINESS_PROFILE, "id": org_id}


async def get_accounts(org_id: str) -> list[dict]:
    """Return chart of accounts with current balances."""
    return _MOCK_ACCOUNTS


async def get_transactions(
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    category: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Search and filter transactions."""
    results = _MOCK_TRANSACTIONS.copy()

    if category:
        results = [t for t in results if category.lower() in t["category"].lower()]
    if status:
        results = [t for t in results if t["status"] == status]

    return results[:limit]


async def get_revenue(org_id: str, period: str = "month") -> dict:
    """Aggregate revenue by period with trend."""
    return {
        "period": period,
        "total": 12500000,
        "currency": _MOCK_CURRENCY,
        "breakdown": {
            "sales_revenue": 11750000,
            "service_revenue": 750000,
        },
        "trend": {
            "current_period": 12500000,
            "previous_period": 10870000,
            "change_pct": 15.0,
            "direction": "up",
        },
        "by_category": [
            {"category": "Electronics Sales", "amount": 8500000, "pct": 68.0},
            {"category": "Accessories", "amount": 2100000, "pct": 16.8},
            {"category": "TV & Audio", "amount": 1150000, "pct": 9.2},
            {"category": "Repair Services", "amount": 750000, "pct": 6.0},
        ],
        "top_customers": [
            {"name": "Serengeti Trading Co.", "amount": 8500000},
            {"name": "Zanzibar Hotel Group", "amount": 3200000},
            {"name": "Walk-in Customers", "amount": 800000},
        ],
    }


async def get_expenses(org_id: str, period: str = "month") -> dict:
    """Aggregate expenses by period with trend."""
    return {
        "period": period,
        "total": 6200000,
        "currency": _MOCK_CURRENCY,
        "breakdown": {
            "cost_of_goods_sold": 2400000,
            "rent": 400000,
            "salaries": 600000,
            "utilities": 280000,
            "transport": 150000,
            "marketing": 150000,
            "other": 2220000,
        },
        "trend": {
            "current_period": 6200000,
            "previous_period": 5800000,
            "change_pct": 6.9,
            "direction": "up",
        },
        "by_category": [
            {"category": "Cost of Goods Sold", "amount": 2400000, "pct": 38.7},
            {"category": "Salaries", "amount": 600000, "pct": 9.7},
            {"category": "Rent", "amount": 400000, "pct": 6.5},
            {"category": "Utilities", "amount": 280000, "pct": 4.5},
            {"category": "Marketing", "amount": 150000, "pct": 2.4},
            {"category": "Transport", "amount": 150000, "pct": 2.4},
            {"category": "Other", "amount": 2220000, "pct": 35.8},
        ],
    }


async def get_profit_loss(org_id: str, period: str = "month") -> dict:
    """Full P&L statement for the period."""
    return {
        "period": period,
        "currency": _MOCK_CURRENCY,
        "revenue": {
            "sales": 11750000,
            "services": 750000,
            "total": 12500000,
        },
        "cost_of_goods_sold": 7500000,
        "gross_profit": 5000000,
        "gross_margin_pct": 40.0,
        "operating_expenses": {
            "rent": 400000,
            "salaries": 600000,
            "utilities": 280000,
            "transport": 150000,
            "marketing": 150000,
            "depreciation": 80000,
            "total": 1660000,
        },
        "operating_income": 3340000,
        "operating_margin_pct": 26.7,
        "other_income": 0,
        "other_expenses": 50000,
        "income_before_tax": 3290000,
        "tax_provision": 0,  # SME tax handled separately
        "net_income": 3290000,
        "net_margin_pct": 26.3,
    }


async def get_balance_sheet(org_id: str) -> dict:
    """Balance sheet at current date."""
    return {
        "as_of_date": "2024-08-15",
        "currency": _MOCK_CURRENCY,
        "assets": {
            "current_assets": {
                "cash_on_hand": 2500000,
                "bank_accounts": 28400000,
                "mpesa_business": 4200000,
                "accounts_receivable": 8700000,
                "inventory": 15600000,
                "total": 59400000,
            },
            "non_current_assets": {
                "office_equipment": 3200000,
                "accumulated_depreciation": -800000,
                "total": 2400000,
            },
            "total_assets": 61800000,
        },
        "liabilities": {
            "current_liabilities": {
                "accounts_payable": 6800000,
                "vat_payable": 1809000,
                "employee_benefits": 950000,
                "total": 9559000,
            },
            "non_current_liabilities": {
                "bank_loan": 10000000,
                "total": 10000000,
            },
            "total_liabilities": 19559000,
        },
        "equity": {
            "owners_equity": 25000000,
            "retained_earnings": 17241000,
            "total_equity": 42241000,
        },
        "total_liabilities_and_equity": 61800000,
        "check": "balanced",
    }


async def get_cash_flow(org_id: str, period: str = "month") -> dict:
    """Cash flow statement by period."""
    return {
        "period": period,
        "currency": _MOCK_CURRENCY,
        "operating_activities": {
            "net_income": 3290000,
            "depreciation": 80000,
            "changes_in_receivables": -1200000,
            "changes_in_inventory": -800000,
            "changes_in_payables": 600000,
            "total": 1970000,
        },
        "investing_activities": {
            "equipment_purchases": -200000,
            "total": -200000,
        },
        "financing_activities": {
            "loan_repayment": -500000,
            "owner_drawings": -300000,
            "total": -800000,
        },
        "net_change_in_cash": 970000,
        "beginning_cash": 34130000,
        "ending_cash": 35100000,
    }


async def get_receivables(org_id: str) -> dict:
    """Accounts receivable aging report."""
    return {
        "total_receivable": 8700000,
        "currency": _MOCK_CURRENCY,
        "aging": {
            "current": 5200000,
            "1_30_days": 1500000,
            "31_60_days": 1200000,
            "61_90_days": 500000,
            "over_90_days": 300000,
        },
        "top_debtors": [
            {
                "customer": "Serengeti Trading Co.",
                "amount": 3500000,
                "oldest_invoice_date": "2024-07-01",
                "invoice_count": 2,
            },
            {
                "customer": "Zanzibar Hotel Group",
                "amount": 3200000,
                "oldest_invoice_date": "2024-08-11",
                "invoice_count": 1,
            },
            {
                "customer": "Arusha Motors Ltd",
                "amount": 2000000,
                "oldest_invoice_date": "2024-06-15",
                "invoice_count": 3,
            },
        ],
        "overdue_count": 4,
        "overdue_total": 2300000,
    }


async def get_payables(org_id: str) -> dict:
    """Outstanding bills to pay."""
    return {
        "total_payable": 6800000,
        "currency": _MOCK_CURRENCY,
        "aging": {
            "current": 3200000,
            "1_30_days": 2100000,
            "31_60_days": 1000000,
            "over_60_days": 500000,
        },
        "bills": [
            {
                "vendor": "Shenzhen Direct Imports",
                "amount": 2400000,
                "due_date": "2024-09-01",
                "status": "pending",
                "reference": "PO-2024-0089",
            },
            {
                "vendor": "Samsung East Africa",
                "amount": 3200000,
                "due_date": "2024-08-25",
                "status": "pending",
                "reference": "PO-2024-0087",
            },
            {
                "vendor": "Dar Properties Ltd",
                "amount": 400000,
                "due_date": "2024-09-05",
                "status": "pending",
                "reference": "RENT-SEP-2024",
            },
            {
                "vendor": "TANESCO",
                "amount": 280000,
                "due_date": "2024-08-20",
                "status": "overdue",
                "reference": "UTIL-AUG-2024",
            },
        ],
    }


async def get_overdue_invoices(org_id: str) -> list[dict]:
    """All unpaid invoices past their due date."""
    return [
        {
            "invoice_id": "INV-2024-0148",
            "customer": "Arusha Motors Ltd",
            "amount": 2000000,
            "currency": _MOCK_CURRENCY,
            "issued_date": "2024-06-15",
            "due_date": "2024-07-15",
            "days_overdue": 31,
            "status": "overdue",
        },
        {
            "invoice_id": "INV-2024-0132",
            "customer": "Mwanza Traders",
            "amount": 300000,
            "currency": _MOCK_CURRENCY,
            "issued_date": "2024-05-20",
            "due_date": "2024-06-20",
            "days_overdue": 56,
            "status": "overdue",
        },
    ]


async def search_documents(org_id: str, query: str) -> list[dict]:
    """Search documents by filename or content."""
    return [
        {
            "id": str(uuid.uuid4()),
            "filename": "Invoice_INV-2024-0156.pdf",
            "type": "invoice",
            "size_bytes": 245000,
            "uploaded_at": "2024-08-15T10:30:00Z",
            "content_preview": "INVOICE #INV-2024-0156 — Kilimanjaro Electronics Ltd...",
            "relevance_score": 0.95,
        },
        {
            "id": str(uuid.uuid4()),
            "filename": "Q2_2024_Financial_Report.xlsx",
            "type": "report",
            "size_bytes": 189000,
            "uploaded_at": "2024-07-05T14:00:00Z",
            "content_preview": "Q2 2024 Financial Summary — Revenue TZS 37.5M...",
            "relevance_score": 0.87,
        },
        {
            "id": str(uuid.uuid4()),
            "filename": "Receipt_TANESCO_July2024.jpg",
            "type": "receipt",
            "size_bytes": 320000,
            "uploaded_at": "2024-08-01T09:15:00Z",
            "content_preview": "TANESCO payment receipt — TZS 280,000...",
            "relevance_score": 0.72,
        },
    ]


async def run_business_health_check(org_id: str) -> dict:
    """Comprehensive health score with breakdown."""
    return {
        "overall_score": 78,
        "grade": "B+",
        "currency": _MOCK_CURRENCY,
        "summary": "Your business is in good health with strong revenue growth and healthy margins. "
        "Main areas for improvement: receivables collection and cash reserves.",
        "breakdown": {
            "liquidity": {
                "score": 82,
                "current_ratio": 6.22,
                "quick_ratio": 4.58,
                "status": "strong",
                "note": "Current assets well exceed short-term obligations",
            },
            "profitability": {
                "score": 85,
                "gross_margin": 40.0,
                "net_margin": 26.3,
                "roe": 7.8,
                "status": "healthy",
                "note": "Margins above industry average for electronics retail in Tanzania",
            },
            "efficiency": {
                "score": 72,
                "inventory_turnover": 4.2,
                "receivable_days": 28,
                "payable_days": 35,
                "status": "acceptable",
                "note": "Inventory turnover could improve; consider slow-moving stock analysis",
            },
            "leverage": {
                "score": 80,
                "debt_to_equity": 0.46,
                "interest_coverage": 6.7,
                "status": "conservative",
                "note": "Low leverage provides buffer for downturns",
            },
            "cash_flow": {
                "score": 68,
                "operating_cf_positive": True,
                "cf_to_income_ratio": 0.60,
                "status": "needs_attention",
                "note": "Cash conversion cycle is stretched due to receivables",
            },
        },
        "alerts": [
            {
                "severity": "warning",
                "message": "TZS 2.3M in receivables overdue by 30+ days",
                "action": "Follow up with Arusha Motors Ltd and Mwanza Traders",
            },
            {
                "severity": "info",
                "message": "Revenue growing 15% month-over-month",
                "action": "Maintain current growth trajectory",
            },
            {
                "severity": "warning",
                "message": "Single supplier dependency for Samsung products",
                "action": "Consider diversifying supplier base",
            },
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }


async def forecast_cash_flow(org_id: str, days: int = 30) -> dict:
    """Forecast cash flow for the next N days."""
    base_cash = 35100000
    daily_avg_inflow = 420000
    daily_avg_outflow = 210000

    projections = []
    running_cash = base_cash
    for i in range(days):
        day = datetime.utcnow() + timedelta(days=i + 1)
        inflow = daily_avg_inflow * (1 + random.uniform(-0.2, 0.3))
        outflow = daily_avg_outflow * (1 + random.uniform(-0.15, 0.25))
        net = inflow - outflow
        running_cash += net
        projections.append({
            "date": day.strftime("%Y-%m-%d"),
            "projected_inflow": round(inflow),
            "projected_outflow": round(outflow),
            "net_flow": round(net),
            "projected_balance": round(running_cash),
        })

    return {
        "forecast_days": days,
        "currency": _MOCK_CURRENCY,
        "current_cash": base_cash,
        "projected_end_cash": round(running_cash),
        "projected_change": round(running_cash - base_cash),
        "projected_change_pct": round((running_cash - base_cash) / base_cash * 100, 1),
        "confidence": "medium",
        "confidence_score": 0.72,
        "assumptions": [
            "Average daily sales continue at current run rate",
            "No major one-time payments planned",
            "Seasonal patterns from last year applied",
            "Pending receivables collected within 30 days",
        ],
        "risk_factors": [
            "TZS 2.3M overdue receivables may delay collection",
            "Upcoming VAT payment of TZS 1.8M due end of month",
            "Bank loan installment of TZS 500K due in 15 days",
        ],
        "daily_projections": projections[:7],  # First week in detail
        "weekly_summary": [
            {
                "week": f"Week {i // 7 + 1}",
                "start_balance": projections[i]["projected_balance"],
                "end_balance": projections[min(i + 6, len(projections) - 1)]["projected_balance"],
            }
            for i in range(0, days, 7)
        ],
    }


# ── DRAFT tools (propose, never auto-execute) ──────────────────────────────

async def create_draft_journal_entry(
    org_id: str,
    transaction_id: str | None,
    entry_date: str,
    lines: list[dict],
    memo: str | None = None,
) -> dict:
    """Propose a draft journal entry. Returns with is_draft=True. Human must approve."""
    return {
        "id": str(uuid.uuid4()),
        "is_draft": True,
        "status": "pending_approval",
        "entry_date": entry_date,
        "memo": memo or "Draft entry created by AI assistant",
        "lines": lines,
        "total_debit": sum(l.get("debit", 0) for l in lines),
        "total_credit": sum(l.get("credit", 0) for l in lines),
        "is_balanced": sum(l.get("debit", 0) for l in lines) == sum(l.get("credit", 0) for l in lines),
        "created_by": "ai_assistant",
        "requires_approval": True,
    }


async def create_draft_invoice(
    org_id: str,
    customer_name: str,
    items: list[dict],
    due_date: str | None = None,
) -> dict:
    """Propose a draft invoice. Human must approve before sending."""
    subtotal = sum(item.get("quantity", 1) * item.get("unit_price", 0) for item in items)
    vat = round(subtotal * 0.18)
    return {
        "id": str(uuid.uuid4()),
        "is_draft": True,
        "status": "pending_approval",
        "invoice_number": f"INV-2024-{random.randint(1000, 9999)}",
        "customer": customer_name,
        "items": items,
        "subtotal": subtotal,
        "vat_amount": vat,
        "total": subtotal + vat,
        "currency": _MOCK_CURRENCY,
        "due_date": due_date or (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "created_by": "ai_assistant",
        "requires_approval": True,
    }


# ── Tool registry for agent tool-calling ────────────────────────────────────

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_business_profile",
            "description": "Return business name, currency, country, industry, and registration details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "org_id": {"type": "string", "description": "Organization ID"},
                },
                "required": ["org_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_accounts",
            "description": "Return the full chart of accounts with current balances.",
            "parameters": {
                "type": "object",
                "properties": {
                    "org_id": {"type": "string", "description": "Organization ID"},
                },
                "required": ["org_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_transactions",
            "description": "Search and filter transactions by date, category, and status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "org_id": {"type": "string", "description": "Organization ID"},
                    "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "category": {"type": "string", "description": "Transaction category filter"},
                    "status": {"type": "string", "description": "Status filter (completed, pending, etc.)"},
                    "limit": {"type": "integer", "description": "Max results to return"},
                },
                "required": ["org_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_revenue",
            "description": "Get aggregated revenue by period with breakdown and trend analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "org_id": {"type": "string", "description": "Organization ID"},
                    "period": {"type": "string", "description": "Period: day, week, month, quarter, year"},
                },
                "required": ["org_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_expenses",
            "description": "Get aggregated expenses by period with breakdown and trend.",
            "parameters": {
                "type": "object",
                "properties": {
                    "org_id": {"type": "string", "description": "Organization ID"},
                    "period": {"type": "string", "description": "Period: day, week, month, quarter, year"},
                },
                "required": ["org_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_profit_loss",
            "description": "Get a full Profit & Loss statement for the given period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "org_id": {"type": "string", "description": "Organization ID"},
                    "period": {"type": "string", "description": "Period: month, quarter, year"},
                },
                "required": ["org_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_balance_sheet",
            "description": "Get the balance sheet showing assets, liabilities, and equity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "org_id": {"type": "string", "description": "Organization ID"},
                },
                "required": ["org_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cash_flow",
            "description": "Get cash flow statement showing operating, investing, and financing activities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "org_id": {"type": "string", "description": "Organization ID"},
                    "period": {"type": "string", "description": "Period: month, quarter, year"},
                },
                "required": ["org_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_receivables",
            "description": "Get accounts receivable aging report with top debtors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "org_id": {"type": "string", "description": "Organization ID"},
                },
                "required": ["org_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_payables",
            "description": "Get outstanding bills and payables with aging.",
            "parameters": {
                "type": "object",
                "properties": {
                    "org_id": {"type": "string", "description": "Organization ID"},
                },
                "required": ["org_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_overdue_invoices",
            "description": "Get all invoices that are past their due date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "org_id": {"type": "string", "description": "Organization ID"},
                },
                "required": ["org_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search uploaded documents by filename or content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "org_id": {"type": "string", "description": "Organization ID"},
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["org_id", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_business_health_check",
            "description": "Run a comprehensive business health check with scores across liquidity, profitability, efficiency, leverage, and cash flow.",
            "parameters": {
                "type": "object",
                "properties": {
                    "org_id": {"type": "string", "description": "Organization ID"},
                },
                "required": ["org_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forecast_cash_flow",
            "description": "Generate a cash flow forecast for the specified number of days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "org_id": {"type": "string", "description": "Organization ID"},
                    "days": {"type": "integer", "description": "Number of days to forecast (default 30)"},
                },
                "required": ["org_id"],
            },
        },
    },
]

# Function name -> callable mapping
TOOL_REGISTRY: dict[str, Any] = {
    "get_business_profile": get_business_profile,
    "get_accounts": get_accounts,
    "get_transactions": get_transactions,
    "get_revenue": get_revenue,
    "get_expenses": get_expenses,
    "get_profit_loss": get_profit_loss,
    "get_balance_sheet": get_balance_sheet,
    "get_cash_flow": get_cash_flow,
    "get_receivables": get_receivables,
    "get_payables": get_payables,
    "get_overdue_invoices": get_overdue_invoices,
    "search_documents": search_documents,
    "run_business_health_check": run_business_health_check,
    "forecast_cash_flow": forecast_cash_flow,
    "create_draft_journal_entry": create_draft_journal_entry,
    "create_draft_invoice": create_draft_invoice,
}
