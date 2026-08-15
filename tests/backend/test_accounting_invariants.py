"""
FinPilot AI — Accounting Invariant Tests

CRITICAL: These tests enforce the double-entry accounting invariants.
Phase 3 is NOT complete until ALL these tests pass.
"""

import uuid
import pytest
from decimal import Decimal
from datetime import date
from sqlalchemy import text
from sqlalchemy.orm import Session


class TestDebitCreditInvariant:
    """Debits must equal credits at journal_entry level and business level."""

    def test_journal_entry_debits_equal_credits(self, db_session: Session):
        """A valid journal entry MUST have sum(debit) == sum(credit)."""
        business_id = uuid.uuid4()
        account_a = uuid.uuid4()
        account_b = uuid.uuid4()

        db_session.execute(text("""
            INSERT INTO businesses (id, name, currency, country, created_at)
            VALUES (:id, 'Test Biz', 'TZS', 'TZ', now())
        """), {"id": str(business_id)})

        for acc_id, code, name, atype in [
            (account_a, "1000", "Cash", "asset"),
            (account_b, "4000", "Sales Revenue", "revenue"),
        ]:
            db_session.execute(text("""
                INSERT INTO chart_of_accounts (id, business_id, code, name, account_type)
                VALUES (:id, :bid, :code, :name, :type)
            """), {"id": str(acc_id), "bid": str(business_id), "code": code, "name": name, "type": atype})

        entry_id = uuid.uuid4()
        db_session.execute(text("""
            INSERT INTO journal_entries (id, business_id, entry_date, memo, created_by, is_draft, created_at)
            VALUES (:id, :bid, :date, 'Test sale', 'system', false, now())
        """), {"id": str(entry_id), "bid": str(business_id), "date": date.today()})

        db_session.execute(text("""
            INSERT INTO journal_lines (id, journal_entry_id, account_id, debit, credit)
            VALUES (:id, :eid, :aid, :debit, 0)
        """), {"id": str(uuid.uuid4()), "eid": str(entry_id), "aid": str(account_a), "debit": Decimal("100000")})

        db_session.execute(text("""
            INSERT INTO journal_lines (id, journal_entry_id, account_id, debit, credit)
            VALUES (:id, :eid, :aid, 0, :credit)
        """), {"id": str(uuid.uuid4()), "eid": str(entry_id), "aid": str(account_b), "credit": Decimal("100000")})

        db_session.commit()

        result = db_session.execute(text("""
            SELECT SUM(debit) as total_debit, SUM(credit) as total_credit
            FROM journal_lines WHERE journal_entry_id = :eid
        """), {"eid": str(entry_id)})

        row = result.fetchone()
        assert row.total_debit == row.total_credit, (
            f"INVARIANT VIOLATION: debit={row.total_debit} != credit={row.total_credit}"
        )

    def test_unbalanced_entry_rejected_by_check_constraint(self, db_session: Session):
        """debit > 0 AND credit > 0 violates CHECK constraint."""
        business_id = uuid.uuid4()
        account_a = uuid.uuid4()

        db_session.execute(text("""
            INSERT INTO businesses (id, name, currency, country, created_at)
            VALUES (:id, 'Test Biz', 'TZS', 'TZ', now())
        """), {"id": str(business_id)})

        db_session.execute(text("""
            INSERT INTO chart_of_accounts (id, business_id, code, name, account_type)
            VALUES (:id, :bid, '1000', 'Cash', 'asset')
        """), {"id": str(account_a), "bid": str(business_id)})

        entry_id = uuid.uuid4()
        db_session.execute(text("""
            INSERT INTO journal_entries (id, business_id, entry_date, memo, created_by, is_draft, created_at)
            VALUES (:id, :bid, :date, 'Unbalanced test', 'system', false, now())
        """), {"id": str(entry_id), "bid": str(business_id), "date": date.today()})

        with pytest.raises(Exception):
            db_session.execute(text("""
                INSERT INTO journal_lines (id, journal_entry_id, account_id, debit, credit)
                VALUES (:id, :eid, :aid, 100000, 50000)
            """), {"id": str(uuid.uuid4()), "eid": str(entry_id), "aid": str(account_a)})
            db_session.commit()

    def test_negative_debit_rejected(self, db_session: Session):
        """Negative debit amounts violate CHECK constraint."""
        business_id = uuid.uuid4()
        account_a = uuid.uuid4()

        db_session.execute(text("""
            INSERT INTO businesses (id, name, currency, country, created_at)
            VALUES (:id, 'Test Biz', 'TZS', 'TZ', now())
        """), {"id": str(business_id)})

        db_session.execute(text("""
            INSERT INTO chart_of_accounts (id, business_id, code, name, account_type)
            VALUES (:id, :bid, '1000', 'Cash', 'asset')
        """), {"id": str(account_a), "bid": str(business_id)})

        entry_id = uuid.uuid4()
        db_session.execute(text("""
            INSERT INTO journal_entries (id, business_id, entry_date, memo, created_by, is_draft, created_at)
            VALUES (:id, :bid, :date, 'Negative test', 'system', false, now())
        """), {"id": str(entry_id), "bid": str(business_id), "date": date.today()})

        with pytest.raises(Exception):
            db_session.execute(text("""
                INSERT INTO journal_lines (id, journal_entry_id, account_id, debit, credit)
                VALUES (:id, :eid, :aid, -100000, 0)
            """), {"id": str(uuid.uuid4()), "eid": str(entry_id), "aid": str(account_a)})
            db_session.commit()


class TestBusinessLevelBalancing:
    """Total debits across all journal entries for a business must equal total credits."""

    def test_business_total_debits_equal_credits(self, db_session: Session):
        """Across all posted entries, sum(debit) == sum(credit) for the business."""
        business_id = uuid.uuid4()
        account_a = uuid.uuid4()
        account_b = uuid.uuid4()

        db_session.execute(text("""
            INSERT INTO businesses (id, name, currency, country, created_at)
            VALUES (:id, 'Test Biz', 'TZS', 'TZ', now())
        """), {"id": str(business_id)})

        for acc_id, code, name, atype in [
            (account_a, "1000", "Cash", "asset"),
            (account_b, "4000", "Sales", "revenue"),
        ]:
            db_session.execute(text("""
                INSERT INTO chart_of_accounts (id, business_id, code, name, account_type)
                VALUES (:id, :bid, :code, :name, :type)
            """), {"id": str(acc_id), "bid": str(business_id), "code": code, "name": name, "type": atype})

        amounts = [Decimal("50000"), Decimal("120000"), Decimal("75000")]
        for amount in amounts:
            entry_id = uuid.uuid4()
            db_session.execute(text("""
                INSERT INTO journal_entries (id, business_id, entry_date, memo, created_by, is_draft, created_at)
                VALUES (:id, :bid, :date, 'test', 'system', false, now())
            """), {"id": str(entry_id), "bid": str(business_id), "date": date.today()})

            db_session.execute(text("""
                INSERT INTO journal_lines (id, journal_entry_id, account_id, debit, credit)
                VALUES (:id, :eid, :aid, :amount, 0)
            """), {"id": str(uuid.uuid4()), "eid": str(entry_id), "aid": str(account_a), "amount": amount})

            db_session.execute(text("""
                INSERT INTO journal_lines (id, journal_entry_id, account_id, debit, credit)
                VALUES (:id, :eid, :aid, 0, :amount)
            """), {"id": str(uuid.uuid4()), "eid": str(entry_id), "aid": str(account_b), "amount": amount})

        db_session.commit()

        result = db_session.execute(text("""
            SELECT SUM(jl.debit) as total_debit, SUM(jl.credit) as total_credit
            FROM journal_lines jl
            JOIN journal_entries je ON jl.journal_entry_id = je.id
            WHERE je.business_id = :bid
        """), {"bid": str(business_id)})

        row = result.fetchone()
        assert row.total_debit == row.total_credit, (
            f"BUSINESS-LEVEL INVARIANT: debit={row.total_debit} != credit={row.total_credit}"
        )


class TestTransactionStatus:
    """Transaction status lifecycle must be enforced."""

    def test_valid_status_values(self, db_session: Session):
        """Only pending, categorized, posted, flagged are valid statuses."""
        business_id = uuid.uuid4()
        db_session.execute(text("""
            INSERT INTO businesses (id, name, currency, country, created_at)
            VALUES (:id, 'Test Biz', 'TZS', 'TZ', now())
        """), {"id": str(business_id)})

        for status in ["pending", "categorized", "posted", "flagged"]:
            db_session.execute(text("""
                INSERT INTO transactions (id, business_id, source, txn_date, amount, currency, status, created_at)
                VALUES (:id, :bid, 'test', :date, 1000, 'TZS', :status, now())
            """), {
                "id": str(uuid.uuid4()),
                "bid": str(business_id),
                "date": date.today(),
                "status": status,
            })

        db_session.commit()

    def test_invalid_status_rejected(self, db_session: Session):
        """Invalid transaction status must be rejected by CHECK constraint."""
        business_id = uuid.uuid4()
        db_session.execute(text("""
            INSERT INTO businesses (id, name, currency, country, created_at)
            VALUES (:id, 'Test Biz', 'TZS', 'TZ', now())
        """), {"id": str(business_id)})

        with pytest.raises(Exception):
            db_session.execute(text("""
                INSERT INTO transactions (id, business_id, source, txn_date, amount, currency, status, created_at)
                VALUES (:id, :bid, 'test', :date, 1000, 'TZS', 'invalid_status', now())
            """), {
                "id": str(uuid.uuid4()),
                "bid": str(business_id),
                "date": date.today(),
            })
            db_session.commit()
