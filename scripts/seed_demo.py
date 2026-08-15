#!/usr/bin/env python3.12
"""
Seed FinPilot AI demo data — Kariakoo clothing shop, Dar es Salaam.
Uses psycopg2-binary (synchronous) for reliability.
Handles duplicates gracefully with ON CONFLICT DO NOTHING.

Run:  PYTHONPATH=backend python3.12 scripts/seed_demo.py

Demo login:  demo@finpilot.ai / demo123456
"""

import csv
import os
import sys
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import bcrypt
import psycopg2
import psycopg2.extras

# ── paths ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = ROOT / "demo"

# ── DB connection ──────────────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5433"))
DB_NAME = os.getenv("DB_NAME", "finpilot")
DB_USER = os.getenv("DB_USER", "finpilot")
DB_PASS = os.getenv("DB_PASS", "finpilot")

DSN = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASS}"

# ── stable IDs (deterministic so re-runs are safe) ─────────────────────
DEMO_BUSINESS_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
DEMO_USER_ID = uuid.UUID("f0e1d2c3-b4a5-6789-0abc-def123456789")

ACCOUNT_IDS: dict[str, uuid.UUID] = {}
for _code in [
    "1000", "1010", "1020", "1100", "1200", "1300",
    "2000", "2100", "2200", "2300",
    "3000", "3100", "3200",
    "4000", "4100", "4200",
    "5000", "5100", "5200", "5300", "5400", "5500",
    "5600", "5700", "5800", "5900", "6000", "6100", "6200", "6300",
]:
    ACCOUNT_IDS[_code] = uuid.uuid5(DEMO_BUSINESS_ID, f"account-{_code}")

CUSTOMER_NAMES = [
    "Anna Mwangi", "Benson Ochieng", "Catherine Njeri",
    "David Kimani", "Esther Mushi", "Francis Otieno",
    "Grace Mkwawa", "Hassan Juma", "Irene Balira",
    "Joseph Mkumbwa",
]
CUSTOMER_IDS = {n: uuid.uuid5(DEMO_BUSINESS_ID, f"customer-{n}") for n in CUSTOMER_NAMES}

VENDOR_NAMES = [
    "Kariakoo Wholesalers", "Tandahimba Supply Co",
    "Mwananyamala Distributors", "Sinza Shoe Depot",
    "Mikocheni Hardware", "Kariakoo Textiles Ltd",
]
VENDOR_IDS = {n: uuid.uuid5(DEMO_BUSINESS_ID, f"vendor-{n}") for n in VENDOR_NAMES}


# ── helpers ────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def connect():
    conn = psycopg2.connect(DSN)
    conn.autocommit = False
    return conn


def insert_ignore(cur, sql, params):
    """Execute INSERT … ON CONFLICT DO NOTHING."""
    cur.execute(sql, params)


# ── seed functions ─────────────────────────────────────────────────────

def seed_business(cur):
    cur.execute("""
        INSERT INTO businesses (id, name, currency, country, created_at)
        VALUES (%s, %s, %s, %s, now())
        ON CONFLICT (id) DO NOTHING
    """, (str(DEMO_BUSINESS_ID), "Kariakoo Fashion House", "TZS", "TZ"))
    print(f"  ✓ Business: Kariakoo Fashion House")


def seed_user(cur):
    pw_hash = hash_password("demo123456")
    cur.execute("""
        INSERT INTO users (id, business_id, email, hashed_password, role, created_at)
        VALUES (%s, %s, %s, %s, %s, now())
        ON CONFLICT (email) DO UPDATE SET hashed_password = EXCLUDED.hashed_password
    """, (str(DEMO_USER_ID), str(DEMO_BUSINESS_ID), "demo@finpilot.ai", pw_hash, "owner"))
    print(f"  ✓ User: demo@finpilot.ai / demo123456")


def seed_accounts(cur):
    accounts = [
        ("1000", "Cash", "asset"),
        ("1010", "Bank - NMB Main Account", "asset"),
        ("1020", "Petty Cash", "asset"),
        ("1100", "Accounts Receivable", "asset"),
        ("1200", "Inventory - Clothing", "asset"),
        ("1300", "Prepaid Expenses", "asset"),
        ("2000", "Accounts Payable", "liability"),
        ("2100", "VAT Payable (18%)", "liability"),
        ("2200", "Loan - NMB Short Term", "liability"),
        ("2300", "CRDB Long Term Loan", "liability"),
        ("3000", "Owner's Capital", "equity"),
        ("3100", "Retained Earnings", "equity"),
        ("3200", "Owner's Drawings", "equity"),
        ("4000", "Sales Revenue - Clothing", "revenue"),
        ("4100", "Sales Revenue - Accessories", "revenue"),
        ("4200", "Other Income", "revenue"),
        ("5000", "Cost of Goods Sold", "expense"),
        ("5100", "Rent Expense", "expense"),
        ("5200", "Utilities (TANESCO/DAWASCO)", "expense"),
        ("5300", "Salary & Wages", "expense"),
        ("5400", "Transport & Delivery", "expense"),
        ("5500", "Office Supplies", "expense"),
        ("5600", "Marketing & Advertising", "expense"),
        ("5700", "Insurance", "expense"),
        ("5800", "Telephone & Internet", "expense"),
        ("5900", "Bank & M-Pesa Charges", "expense"),
        ("6000", "Depreciation", "expense"),
        ("6100", "Government Fees & Licences", "expense"),
        ("6200", "Maintenance & Repairs", "expense"),
        ("6300", "Security Services", "expense"),
    ]
    for code, name, acct_type in accounts:
        cur.execute("""
            INSERT INTO chart_of_accounts (id, business_id, code, name, account_type, parent_id)
            VALUES (%s, %s, %s, %s, %s, NULL)
            ON CONFLICT (id) DO NOTHING
        """, (str(ACCOUNT_IDS[code]), str(DEMO_BUSINESS_ID), code, name, acct_type))
    print(f"  ✓ Chart of Accounts: {len(accounts)} accounts")


def seed_contacts(cur):
    for name, cid in CUSTOMER_IDS.items():
        cur.execute("""
            INSERT INTO customers (id, business_id, name)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (str(cid), str(DEMO_BUSINESS_ID), name))
    for name, vid in VENDOR_IDS.items():
        cur.execute("""
            INSERT INTO vendors (id, business_id, name)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (str(vid), str(DEMO_BUSINESS_ID), name))
    print(f"  ✓ Customers: {len(CUSTOMER_IDS)}")
    print(f"  ✓ Vendors: {len(VENDOR_IDS)}")


def seed_transactions(cur):
    csv_path = DEMO_DIR / "sample_transactions.csv"
    if not csv_path.exists():
        print(f"  ⚠ {csv_path} not found, skipping CSV transactions")
        return 0

    count = 0
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tid = uuid.uuid5(DEMO_BUSINESS_ID, f"txn-{row['txn_date']}-{row['description'][:40]}")
            cur.execute("""
                INSERT INTO transactions (
                    id, business_id, source, document_id, txn_date, description,
                    amount, currency, counterparty, ai_category, ai_confidence, status, created_at
                ) VALUES (%s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO NOTHING
            """, (
                str(tid), str(DEMO_BUSINESS_ID),
                row.get("source", "manual"),
                row["txn_date"], row["description"],
                row["amount"], row.get("currency", "TZS"),
                row["counterparty"], row["ai_category"],
                "0.850" if row["status"] == "posted" else "0.700",
                row["status"],
            ))
            count += 1
    print(f"  ✓ Transactions: {count} from CSV")
    return count


def seed_journal_entries(cur):
    """Create balanced journal entries for key transactions."""
    today = date(2026, 8, 15)
    entries = [
        # (entry_date, memo, [(account_code, debit, credit), ...])
        (date(2026, 7, 1), "Rent payment July - Kariakoo shop",
         [("5100", 850000, 0), ("1010", 0, 850000)]),
        (date(2026, 7, 3), "Cash sale vitenge to Anna Mwangi",
         [("1000", 360000, 0), ("4000", 0, 360000)]),
        (date(2026, 7, 5), "Cash sale men shirts to Benson",
         [("1000", 500000, 0), ("4000", 0, 500000)]),
        (date(2026, 7, 4), "TANESCO electricity July",
         [("5200", 128000, 0), ("2000", 0, 128000)]),
        (date(2026, 7, 10), "Staff salary - Baraka",
         [("5300", 400000, 0), ("1010", 0, 400000)]),
        (date(2026, 7, 16), "Inventory purchase kitenge",
         [("1200", 1800000, 0), ("2000", 0, 1800000)]),
        (date(2026, 8, 1), "Rent payment August",
         [("5100", 850000, 0), ("1010", 0, 850000)]),
        (date(2026, 8, 7), "Cash sale men suits to Benson",
         [("1000", 1250000, 0), ("4000", 0, 1250000)]),
        (date(2026, 8, 10), "Insurance premium Q3",
         [("5700", 350000, 0), ("1010", 0, 350000)]),
        (date(2026, 8, 14), "Inventory purchase kitenge Aug",
         [("1200", 1500000, 0), ("2000", 0, 1500000)]),
    ]
    count = 0
    for entry_date, memo, lines in entries:
        je_id = uuid.uuid5(DEMO_BUSINESS_ID, f"je-{entry_date}-{memo[:30]}")
        cur.execute("""
            INSERT INTO journal_entries (
                id, business_id, transaction_id, entry_date, memo, created_by, is_draft, created_at
            ) VALUES (%s, %s, NULL, %s, %s, 'system', false, now())
            ON CONFLICT (id) DO NOTHING
        """, (str(je_id), str(DEMO_BUSINESS_ID), str(entry_date), memo))
        for acct_code, debit, credit in lines:
            line_id = uuid.uuid5(je_id, f"line-{acct_code}-{debit}-{credit}")
            cur.execute("""
                INSERT INTO journal_lines (id, journal_entry_id, account_id, debit, credit)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (str(line_id), str(je_id), str(ACCOUNT_IDS[acct_code]), str(debit), str(credit)))
        count += 1
    print(f"  ✓ Journal Entries: {count} (balanced)")
    return count


def seed_invoices(cur):
    csv_path = DEMO_DIR / "sample_invoices.csv"
    if not csv_path.exists():
        print(f"  ⚠ {csv_path} not found, skipping invoices")
        return 0

    # Map customer names to IDs
    name_to_id = {n.lower(): cid for n, cid in CUSTOMER_IDS.items()}

    count = 0
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            inv_id = uuid.uuid5(DEMO_BUSINESS_ID, f"inv-{row['invoice_number']}")
            cust_name = row["customer_name"].strip().lower()
            cust_id = name_to_id.get(cust_name)
            if not cust_id:
                print(f"  ⚠ Unknown customer '{row['customer_name']}' in invoice {row['invoice_number']}, skipping")
                continue
            cur.execute("""
                INSERT INTO invoices (
                    id, business_id, customer_id, document_id, invoice_number,
                    issue_date, due_date, subtotal, tax, total, status
                ) VALUES (%s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                str(inv_id), str(DEMO_BUSINESS_ID), str(cust_id),
                row["invoice_number"],
                row["issue_date"], row["due_date"],
                row["subtotal"], row["tax"], row["total"],
                row["status"],
            ))
            count += 1
    print(f"  ✓ Invoices: {count} from CSV")
    return count


def seed_alerts(cur):
    alerts = [
        ("critical", "Overdue invoice - David Kimani",
         "Invoice INV-2026-009 for TZS 442,500 was due on 2026-07-30 and is 16 days overdue.",
         {"table": "invoices", "record_type": "overdue"}),
        ("critical", "Overdue invoice - Francis Otieno",
         "Invoice INV-2026-010 for TZS 330,400 was due on 2026-08-01 and is 14 days overdue.",
         {"table": "invoices", "record_type": "overdue"}),
        ("warning", "Low inventory forecast",
         "Based on current sales velocity, stock levels for kangas and school uniforms will be depleted within 7 days. Consider reordering from Kariakoo Textiles Ltd.",
         {"table": "forecasts", "record_type": "inventory_forecast"}),
        ("warning", "Cash flow alert",
         "Outstanding receivables total TZS 3,997,650 across 6 unpaid invoices. Recommend following up on overdue accounts.",
         {"table": "invoices", "record_type": "cash_forecast"}),
        ("info", "Monthly VAT filing due",
         "TRA VAT return for July 2026 is due by August 20th. Estimated payable: TZS 450,000. File via eFDMS portal.",
         {"table": "journal_entries", "record_type": "vat_reminder"}),
        ("info", "Q3 Insurance paid",
         "Insurance premium of TZS 350,000 for Q3 2026 has been processed successfully.",
         {"table": "transactions", "record_type": "payment_confirmation"}),
    ]
    for sev, title, detail, refs in alerts:
        aid = uuid.uuid5(DEMO_BUSINESS_ID, f"alert-{title[:30]}")
        cur.execute("""
            INSERT INTO alerts (
                id, business_id, severity, title, detail, source_refs, created_at, acknowledged
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, now(), false)
            ON CONFLICT (id) DO NOTHING
        """, (str(aid), str(DEMO_BUSINESS_ID), sev, title, detail, psycopg2.extras.Json(refs)))
    print(f"  ✓ Alerts: {len(alerts)}")


# ── main ───────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  FinPilot AI — Seeding Demo Data")
    print("=" * 60)
    print(f"  DSN: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print()

    try:
        conn = connect()
    except psycopg2.OperationalError as e:
        print(f"  ✗ Cannot connect to database: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with conn.cursor() as cur:
            seed_business(cur)
            seed_user(cur)
            seed_accounts(cur)
            seed_contacts(cur)
            txn_count = seed_transactions(cur)
            je_count = seed_journal_entries(cur)
            inv_count = seed_invoices(cur)
            seed_alerts(cur)

        conn.commit()
        print()
        print("=" * 60)
        print("  ✓ Seed complete — all data committed")
        print("=" * 60)
        print(f"  Business  : Kariakoo Fashion House ({DEMO_BUSINESS_ID})")
        print(f"  Login     : demo@finpilot.ai / demo123456")
        print(f"  Accounts  : 30")
        print(f"  Customers : {len(CUSTOMER_IDS)}")
        print(f"  Vendors   : {len(VENDOR_IDS)}")
        print(f"  Txns      : {txn_count}")
        print(f"  Journals  : {je_count}")
        print(f"  Invoices  : {inv_count}")
        print(f"  Alerts    : 6")
        print("=" * 60)
    except Exception as e:
        conn.rollback()
        print(f"\n  ✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
