#!/usr/bin/env python3
"""Seed the FinPilot AI database with Tanzania clothing shop demo data.

Usage:
    python scripts/seed_demo.py          # Seed with demo data
    python scripts/seed_demo.py --clear  # Clear existing data then seed

Requires DATABASE_URL to be set or defaults to the config value.
"""

import asyncio
import sys
import os
import uuid

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session, engine, Base
from app.models.business import Business, User
from app.models.accounting import ChartOfAccounts, Transaction, JournalEntry, JournalLine
from app.models.contacts import Customer, Vendor, Invoice, Bill
from app.models.document import Document, ExtractedRecord
from app.models.ai import Forecast, Alert, AuditLog
from app.seed.demo_data import (
    generate_demo_data,
    BUSINESS_ID,
    USER_ID,
)


async def clear_database(db: AsyncSession):
    """Delete all data from demo tables (order matters for FKs)."""
    print("  Clearing existing data...")
    tables = [
        "journal_lines",
        "journal_entries",
        "audit_log",
        "alerts",
        "forecasts",
        "extracted_records",
        "documents",
        "bills",
        "invoices",
        "transactions",
        "vendors",
        "customers",
        "chart_of_accounts",
        "users",
        "businesses",
    ]
    for table in tables:
        await db.execute(text(f"DELETE FROM {table}"))
    await db.flush()
    print("  ✓ All tables cleared")


async def seed_data(clear_first: bool = False):
    """Insert demo data into the database."""
    print("🌱 Seeding FinPilot AI demo data...")
    print(f"   Business: Mwanga Fashion House")
    print(f"   Location: Dar es Salaam, Tanzania")
    print(f"   Currency: TZS")
    print()

    data = generate_demo_data()

    async with async_session() as db:
        try:
            if clear_first:
                await clear_database(db)

            # --- Business ---
            print("  Inserting business...")
            db.add(Business(
                id=data["business"]["id"],
                name=data["business"]["name"],
                currency=data["business"]["currency"],
                country=data["business"]["country"],
                created_at=data["business"]["created_at"],
            ))
            await db.flush()
            print(f"  ✓ Business: {data['business']['name']}")

            # --- User ---
            print("  Inserting user...")
            db.add(User(
                id=data["user"]["id"],
                business_id=data["user"]["business_id"],
                email=data["user"]["email"],
                hashed_password=data["user"]["hashed_password"],
                role=data["user"]["role"],
                created_at=data["user"]["created_at"],
            ))
            await db.flush()
            print(f"  ✓ User: {data['user']['email']}")

            # --- Chart of Accounts ---
            print(f"  Inserting {len(data['accounts'])} accounts...")
            for acct in data["accounts"]:
                db.add(ChartOfAccounts(
                    id=acct["id"],
                    business_id=acct["business_id"],
                    code=acct["code"],
                    name=acct["name"],
                    account_type=acct["account_type"],
                ))
            await db.flush()
            print(f"  ✓ Chart of accounts: {len(data['accounts'])} accounts")

            # --- Customers ---
            print(f"  Inserting {len(data['customers'])} customers...")
            for cust in data["customers"]:
                db.add(Customer(
                    id=cust["id"],
                    business_id=cust["business_id"],
                    name=cust["name"],
                ))
            await db.flush()
            print(f"  ✓ Customers: {len(data['customers'])} inserted")

            # --- Vendors ---
            print(f"  Inserting {len(data['vendors'])} vendors...")
            for vnd in data["vendors"]:
                db.add(Vendor(
                    id=vnd["id"],
                    business_id=vnd["business_id"],
                    name=vnd["name"],
                ))
            await db.flush()
            print(f"  ✓ Vendors: {len(data['vendors'])} inserted")

            # --- Transactions ---
            print(f"  Inserting {len(data['transactions'])} transactions...")
            batch_size = 500
            for i in range(0, len(data["transactions"]), batch_size):
                batch = data["transactions"][i:i + batch_size]
                for txn in batch:
                    db.add(Transaction(
                        id=txn["id"],
                        business_id=txn["business_id"],
                        source=txn["source"],
                        txn_date=txn["txn_date"],
                        description=txn["description"],
                        amount=txn["amount"],
                        currency=txn["currency"],
                        counterparty=txn["counterparty"],
                        ai_category=txn["ai_category"],
                        ai_confidence=txn["ai_confidence"],
                        status=txn["status"],
                        created_at=txn["created_at"],
                    ))
                await db.flush()
                print(f"    ... {min(i + batch_size, len(data['transactions']))}/{len(data['transactions'])}")
            print(f"  ✓ Transactions: {len(data['transactions'])} inserted")

            # --- Invoices ---
            print(f"  Inserting {len(data['invoices'])} invoices...")
            for inv in data["invoices"]:
                db.add(Invoice(
                    id=inv["id"],
                    business_id=inv["business_id"],
                    customer_id=inv["customer_id"],
                    invoice_number=inv["invoice_number"],
                    issue_date=inv["issue_date"],
                    due_date=inv["due_date"],
                    subtotal=inv["subtotal"],
                    tax=inv["tax"],
                    total=inv["total"],
                    status=inv["status"],
                ))
            await db.flush()
            print(f"  ✓ Invoices: {len(data['invoices'])} inserted")

            # --- Bills ---
            print(f"  Inserting {len(data['bills'])} bills...")
            for bill in data["bills"]:
                db.add(Bill(
                    id=bill["id"],
                    business_id=bill["business_id"],
                    vendor_id=bill["vendor_id"],
                    amount=bill["amount"],
                    due_date=bill["due_date"],
                    status=bill["status"],
                ))
            await db.flush()
            print(f"  ✓ Bills: {len(data['bills'])} inserted")

            # --- Alerts ---
            print("  Inserting sample alerts...")
            alerts = [
                Alert(
                    business_id=BUSINESS_ID,
                    severity="warning",
                    title="Overdue Invoices Detected",
                    detail=f"{sum(1 for i in data['invoices'] if i['status'] == 'overdue')} invoices are past due. Follow up with customers.",
                ),
                Alert(
                    business_id=BUSINESS_ID,
                    severity="info",
                    title="Monthly Reconciliation Due",
                    detail="Run bank reconciliation for this month to ensure records match.",
                ),
                Alert(
                    business_id=BUSINESS_ID,
                    severity="critical",
                    title="VAT Filing Deadline Approaching",
                    detail="VAT return for the current period is due in 5 days. Ensure all transactions are categorized.",
                ),
            ]
            for alert in alerts:
                db.add(alert)
            await db.flush()
            print(f"  ✓ Alerts: {len(alerts)} inserted")

            await db.commit()
            print()
            print("=" * 60)
            print("✅ Demo data seeded successfully!")
            print("=" * 60)
            print()
            print("Demo Login Credentials:")
            print(f"  Email:    owner@mwangafashion.co.tz")
            print(f"  Password: Demo@2024")
            print()
            print(f"Business: {BUSINESS_ID}")
            print(f"User:     {USER_ID}")
            print()

        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error seeding data: {e}")
            raise


async def main():
    clear = "--clear" in sys.argv
    await seed_data(clear_first=clear)


if __name__ == "__main__":
    asyncio.run(main())
