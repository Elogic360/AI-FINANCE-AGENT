"""Demo data for a Tanzania clothing shop in Dar es Salaam.

All amounts in TZS. Generates realistic 3-month financial data:
- Chart of accounts (assets, liabilities, equity, revenue, expenses)
- Products: T-shirts, jeans, dresses, khangas, kanzus, shoes, bags
- Customers with TZ phone numbers
- Vendors/suppliers
- Daily sales and expense transactions
- Invoices (paid, unpaid, overdue)
- Bank transactions
"""

import uuid
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BUSINESS_NAME = "Mwanga Fashion House"
BUSINESS_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")

TODAY = date.today()
THREE_MONTHS_AGO = TODAY - timedelta(days=90)

# ---------------------------------------------------------------------------
# Chart of Accounts
# ---------------------------------------------------------------------------

CHART_OF_ACCOUNTS = [
    # Assets
    {"code": "1000", "name": "Cash", "account_type": "asset"},
    {"code": "1010", "name": "M-Pesa", "account_type": "asset"},
    {"code": "1020", "name": "CRDB Bank Account", "account_type": "asset"},
    {"code": "1100", "name": "Accounts Receivable", "account_type": "asset"},
    {"code": "1200", "name": "Inventory", "account_type": "asset"},
    {"code": "1300", "name": "Prepaid Rent", "account_type": "asset"},
    {"code": "1400", "name": "Shop Fixtures & Fittings", "account_type": "asset"},
    # Liabilities
    {"code": "2000", "name": "Accounts Payable", "account_type": "liability"},
    {"code": "2100", "name": "VAT Payable", "account_type": "liability"},
    {"code": "2200", "name": "Employee Wages Payable", "account_type": "liability"},
    {"code": "2300", "name": "Business Loan - NMB", "account_type": "liability"},
    # Equity
    {"code": "3000", "name": "Owner's Capital", "account_type": "equity"},
    {"code": "3100", "name": "Retained Earnings", "account_type": "equity"},
    # Revenue
    {"code": "4000", "name": "T-Shirt Sales", "account_type": "revenue"},
    {"code": "4010", "name": "Jeans Sales", "account_type": "revenue"},
    {"code": "4020", "name": "Dress Sales", "account_type": "revenue"},
    {"code": "4030", "name": "Khanga Sales", "account_type": "revenue"},
    {"code": "4040", "name": "Kanzu Sales", "account_type": "revenue"},
    {"code": "4050", "name": "Shoe Sales", "account_type": "revenue"},
    {"code": "4060", "name": "Bag Sales", "account_type": "revenue"},
    {"code": "4070", "name": "Alteration Services", "account_type": "revenue"},
    # Expenses
    {"code": "5000", "name": "Cost of Goods Sold", "account_type": "expense"},
    {"code": "5100", "name": "Rent Expense", "account_type": "expense"},
    {"code": "5200", "name": "Utilities", "account_type": "expense"},
    {"code": "5300", "name": "Employee Wages", "account_type": "expense"},
    {"code": "5400", "name": "Transport & Delivery", "account_type": "expense"},
    {"code": "5500", "name": "Marketing & Advertising", "account_type": "expense"},
    {"code": "5600", "name": "Packaging & Supplies", "account_type": "expense"},
    {"code": "5700", "name": "Insurance", "account_type": "expense"},
    {"code": "5800", "name": "Bank Charges", "account_type": "expense"},
    {"code": "5900", "name": "Mobile Money Fees", "account_type": "expense"},
]

# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

PRODUCTS = [
    {"name": "T-Shirt (Cotton, Various)", "category": "T-Shirt Sales", "unit_price": Decimal("25000")},
    {"name": "T-Shirt (Designer Print)", "category": "T-Shirt Sales", "unit_price": Decimal("35000")},
    {"name": "Jeans (Men's Regular)", "category": "Jeans Sales", "unit_price": Decimal("55000")},
    {"name": "Jeans (Women's Slim)", "category": "Jeans Sales", "unit_price": Decimal("60000")},
    {"name": "Dress (Kitenge)", "category": "Dress Sales", "unit_price": Decimal("80000")},
    {"name": "Dress (Casual)", "category": "Dress Sales", "unit_price": Decimal("45000")},
    {"name": "Khanga (Pair)", "category": "Khanga Sales", "unit_price": Decimal("30000")},
    {"name": "Khanga (Single)", "category": "Khanga Sales", "unit_price": Decimal("18000")},
    {"name": "Kanzu (Men's Formal)", "category": "Kanzu Sales", "unit_price": Decimal("70000")},
    {"name": "Kanzu (Embroidered)", "category": "Kanzu Sales", "unit_price": Decimal("120000")},
    {"name": "Shoes (Casual Sneakers)", "category": "Shoe Sales", "unit_price": Decimal("45000")},
    {"name": "Shoes (Leather Formal)", "category": "Shoe Sales", "unit_price": Decimal("85000")},
    {"name": "Handbag (Kitenge)", "category": "Bag Sales", "unit_price": Decimal("35000")},
    {"name": "Backpack (Everyday)", "category": "Bag Sales", "unit_price": Decimal("40000")},
]

# ---------------------------------------------------------------------------
# Customers — 10 with TZ phone numbers
# ---------------------------------------------------------------------------

CUSTOMERS = [
    {"name": "Amina Hassan", "phone": "+255 712 345 678"},
    {"name": "John Mwakasege", "phone": "+255 754 987 654"},
    {"name": "Fatima Omar", "phone": "+255 765 111 222"},
    {"name": "David Kimaro", "phone": "+255 689 333 444"},
    {"name": "Grace Mushi", "phone": "+255 713 555 666"},
    {"name": "Peter Ngowi", "phone": "+255 756 777 888"},
    {"name": "Neema Shayo", "phone": "+255 677 999 000"},
    {"name": "Hassan Mwalimu", "phone": "+255 714 222 333"},
    {"name": "Elizabeth Mollel", "phone": "+255 755 444 555"},
    {"name": "Joseph Kibona", "phone": "+255 688 666 777"},
]

# ---------------------------------------------------------------------------
# Vendors — 5 suppliers
# ---------------------------------------------------------------------------

VENDORS = [
    {"name": "Kariakoo Textiles Ltd", "location": "Kariakoo, Dar es Salaam"},
    {"name": "Mwanza Garment Suppliers", "location": "Mwanza"},
    {"name": "Tanzania Shoe Distributors", "location": "Ubungo, Dar es Salaam"},
    {"name": "Zanzibar Khanga Co.", "location": "Stone Town, Zanzibar"},
    {"name": "DSM Packaging Solutions", "location": "Ilala, Dar es Salaam"},
]

# ---------------------------------------------------------------------------
# Expense categories and typical amounts (monthly)
# ---------------------------------------------------------------------------

EXPENSE_TEMPLATES = [
    {"category": "Rent Expense", "description": "Shop rent - Kariakoo", "amount": Decimal("800000"), "frequency": "monthly"},
    {"category": "Utilities", "description": "TANESCO electricity bill", "amount": Decimal("150000"), "frequency": "monthly"},
    {"category": "Utilities", "description": "DAWASCO water bill", "amount": Decimal("45000"), "frequency": "monthly"},
    {"category": "Employee Wages", "description": "Shop assistant salary - Amina", "amount": Decimal("350000"), "frequency": "monthly"},
    {"category": "Employee Wages", "description": "Shop assistant salary - Juma", "amount": Decimal("300000"), "frequency": "monthly"},
    {"category": "Transport & Delivery", "description": "Delivery to customer", "amount": Decimal("15000"), "frequency": "per_use"},
    {"category": "Transport & Delivery", "description": "Supplier visit transport", "amount": Decimal("25000"), "frequency": "weekly"},
    {"category": "Marketing & Advertising", "description": "Instagram/Facebook ads", "amount": Decimal("100000"), "frequency": "monthly"},
    {"category": "Marketing & Advertising", "description": "Flyers and banners", "amount": Decimal("50000"), "frequency": "monthly"},
    {"category": "Packaging & Supplies", "description": "Shopping bags and tissue paper", "amount": Decimal("35000"), "frequency": "monthly"},
    {"category": "Insurance", "description": "Shop insurance premium", "amount": Decimal("120000"), "frequency": "monthly"},
    {"category": "Bank Charges", "description": "CRDB bank account fees", "amount": Decimal("15000"), "frequency": "monthly"},
    {"category": "Mobile Money Fees", "description": "M-Pesa transaction fees", "amount": Decimal("25000"), "frequency": "monthly"},
]


def _random_date_in_range(start: date, end: date) -> date:
    """Return a random date between start and end."""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(0, delta)))


def generate_demo_data() -> dict:
    """Generate all demo data and return as a dict of lists ready for DB insertion.

    Returns:
        dict with keys: business, user, accounts, customers, vendors,
        transactions, invoices, bills, bank_transactions
    """
    random.seed(42)  # Reproducible demo data

    # --- Business ---
    business = {
        "id": BUSINESS_ID,
        "name": BUSINESS_NAME,
        "currency": "TZS",
        "country": "TZ",
        "created_at": datetime(2024, 1, 15),
    }

    # --- User ---
    from app.services.auth_service import hash_password

    user = {
        "id": USER_ID,
        "business_id": BUSINESS_ID,
        "email": "owner@mwangafashion.co.tz",
        "hashed_password": hash_password("Demo@2024"),
        "role": "owner",
        "created_at": datetime(2024, 1, 15),
    }

    # --- Chart of Accounts ---
    accounts = []
    account_id_map = {}  # code -> uuid
    for acct in CHART_OF_ACCOUNTS:
        acct_id = uuid.uuid5(BUSINESS_ID, acct["code"])
        account_id_map[acct["code"]] = acct_id
        accounts.append({
            "id": acct_id,
            "business_id": BUSINESS_ID,
            "code": acct["code"],
            "name": acct["name"],
            "account_type": acct["account_type"],
        })

    # --- Customers ---
    customers = []
    customer_ids = []
    for cust in CUSTOMERS:
        cid = uuid.uuid5(BUSINESS_ID, cust["name"])
        customer_ids.append(cid)
        customers.append({
            "id": cid,
            "business_id": BUSINESS_ID,
            "name": cust["name"],
        })

    # --- Vendors ---
    vendors = []
    vendor_ids = []
    for vnd in VENDORS:
        vid = uuid.uuid5(BUSINESS_ID, vnd["name"])
        vendor_ids.append(vid)
        vendors.append({
            "id": vid,
            "business_id": BUSINESS_ID,
            "name": vnd["name"],
        })

    # --- Transactions (3 months of daily sales + expenses) ---
    transactions = []
    txn_id_counter = 0

    # Generate daily sales
    current_date = THREE_MONTHS_AGO
    while current_date <= TODAY:
        # Skip some days randomly (closed on some Sundays)
        if current_date.weekday() == 6 and random.random() < 0.5:
            current_date += timedelta(days=1)
            continue

        # 3-8 sales per day
        num_sales = random.randint(3, 8)
        for _ in range(num_sales):
            product = random.choice(PRODUCTS)
            qty = random.randint(1, 4)
            amount = product["unit_price"] * qty

            txn_id_counter += 1
            txn_id = uuid.uuid5(BUSINESS_ID, f"sale-{current_date}-{txn_id_counter}")
            transactions.append({
                "id": txn_id,
                "business_id": BUSINESS_ID,
                "source": random.choice(["pos", "mpesa", "cash"]),
                "txn_date": current_date,
                "description": f"Sale: {product['name']} x{qty}",
                "amount": amount,
                "currency": "TZS",
                "counterparty": random.choice(CUSTOMERS)["name"] if random.random() < 0.3 else "Walk-in Customer",
                "ai_category": product["category"],
                "ai_confidence": Decimal("0.92"),
                "status": "categorized",
                "created_at": datetime.combine(current_date, datetime.min.time()) + timedelta(hours=random.randint(8, 18)),
            })

        # Add COGS for the day (roughly 40-50% of sales)
        day_sales_total = sum(
            t["amount"] for t in transactions
            if t["txn_date"] == current_date and t["amount"] > 0
        )
        if day_sales_total > 0:
            txn_id_counter += 1
            cogs = (day_sales_total * Decimal(str(random.uniform(0.40, 0.50)))).quantize(Decimal("1"))
            transactions.append({
                "id": uuid.uuid5(BUSINESS_ID, f"cogs-{current_date}"),
                "business_id": BUSINESS_ID,
                "source": "system",
                "txn_date": current_date,
                "description": "Cost of goods sold (daily)",
                "amount": -cogs,
                "currency": "TZS",
                "counterparty": None,
                "ai_category": "Cost of Goods Sold",
                "ai_confidence": Decimal("0.95"),
                "status": "categorized",
                "created_at": datetime.combine(current_date, datetime.min.time()) + timedelta(hours=19),
            })

        current_date += timedelta(days=1)

    # Monthly expenses
    month_start = THREE_MONTHS_AGO.replace(day=1)
    current_month = month_start
    while current_month <= TODAY:
        month_end = (current_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

        for exp in EXPENSE_TEMPLATES:
            if exp["frequency"] == "monthly":
                exp_date = current_month + timedelta(days=random.randint(0, 5))
                if exp_date > TODAY:
                    continue
                txn_id_counter += 1
                transactions.append({
                    "id": uuid.uuid5(BUSINESS_ID, f"exp-{current_month}-{txn_id_counter}"),
                    "business_id": BUSINESS_ID,
                    "source": "manual",
                    "txn_date": exp_date,
                    "description": exp["description"],
                    "amount": -exp["amount"],
                    "currency": "TZS",
                    "counterparty": None,
                    "ai_category": exp["category"],
                    "ai_confidence": Decimal("0.88"),
                    "status": "categorized",
                    "created_at": datetime.combine(exp_date, datetime.min.time()) + timedelta(hours=10),
                })
            elif exp["frequency"] == "weekly":
                for week_start_day in range(0, 28, 7):
                    exp_date = current_month + timedelta(days=week_start_day + random.randint(0, 2))
                    if exp_date > TODAY or exp_date > month_end:
                        continue
                    txn_id_counter += 1
                    transactions.append({
                        "id": uuid.uuid5(BUSINESS_ID, f"exp-w-{exp_date}-{txn_id_counter}"),
                        "business_id": BUSINESS_ID,
                        "source": "manual",
                        "txn_date": exp_date,
                        "description": exp["description"],
                        "amount": -exp["amount"],
                        "currency": "TZS",
                        "counterparty": None,
                        "ai_category": exp["category"],
                        "ai_confidence": Decimal("0.85"),
                        "status": "categorized",
                        "created_at": datetime.combine(exp_date, datetime.min.time()) + timedelta(hours=11),
                    })

        # Move to next month
        if current_month.month == 12:
            current_month = current_month.replace(year=current_month.year + 1, month=1)
        else:
            current_month = current_month.replace(month=current_month.month + 1)

    # --- Invoices ---
    invoices = []
    invoice_counter = 0
    for i in range(15):
        invoice_counter += 1
        cust_id = random.choice(customer_ids)
        inv_date = _random_date_in_range(THREE_MONTHS_AGO, TODAY - timedelta(days=10))
        due_date = inv_date + timedelta(days=random.choice([14, 30, 45]))
        subtotal = Decimal(str(random.randint(50000, 800000)))
        tax = (subtotal * Decimal("0.18")).quantize(Decimal("1"))
        total = subtotal + tax

        if due_date < TODAY - timedelta(days=30):
            status = random.choice(["overdue", "overdue", "paid"])
        elif due_date < TODAY:
            status = random.choice(["overdue", "paid", "unpaid"])
        else:
            status = "unpaid"

        invoices.append({
            "id": uuid.uuid5(BUSINESS_ID, f"inv-{invoice_counter}"),
            "business_id": BUSINESS_ID,
            "customer_id": cust_id,
            "invoice_number": f"INV-2024-{invoice_counter:04d}",
            "issue_date": inv_date,
            "due_date": due_date,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "status": status,
        })

    # --- Bills (vendor invoices) ---
    bills = []
    bill_counter = 0
    for i in range(10):
        bill_counter += 1
        vnd_id = random.choice(vendor_ids)
        bill_date = _random_date_in_range(THREE_MONTHS_AGO, TODAY - timedelta(days=5))
        due_date = bill_date + timedelta(days=random.choice([14, 30]))
        amount = Decimal(str(random.randint(200000, 2000000)))

        if due_date < TODAY - timedelta(days=15):
            status = random.choice(["paid", "paid", "overdue"])
        elif due_date < TODAY:
            status = random.choice(["unpaid", "paid"])
        else:
            status = "unpaid"

        bills.append({
            "id": uuid.uuid5(BUSINESS_ID, f"bill-{bill_counter}"),
            "business_id": BUSINESS_ID,
            "vendor_id": vnd_id,
            "amount": amount,
            "due_date": due_date,
            "status": status,
        })

    # --- Bank transactions (matching some sales) ---
    bank_transactions = []
    bank_counter = 0
    for txn in transactions:
        if txn["amount"] > 0 and txn["source"] in ("mpesa", "pos") and random.random() < 0.7:
            bank_counter += 1
            bank_transactions.append({
                "id": uuid.uuid5(BUSINESS_ID, f"bank-{bank_counter}"),
                "business_id": BUSINESS_ID,
                "source": "bank",
                "txn_date": txn["txn_date"],
                "description": f"Bank deposit - {txn['description']}",
                "amount": txn["amount"],
                "currency": "TZS",
                "counterparty": txn["counterparty"],
                "ai_category": txn["ai_category"],
                "ai_confidence": Decimal("0.90"),
                "status": "categorized",
                "created_at": txn["created_at"] + timedelta(hours=1),
            })

    return {
        "business": business,
        "user": user,
        "accounts": accounts,
        "customers": customers,
        "vendors": vendors,
        "transactions": transactions + bank_transactions,
        "invoices": invoices,
        "bills": bills,
    }
