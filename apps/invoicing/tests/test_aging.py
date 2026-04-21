import datetime
from decimal import Decimal

import pytest

from apps.customers.models import Customer, CustomerAnnex
from apps.invoicing.aging import (
    age_invoice,
    ar_aging_by_customer,
    ar_aging_totals,
    sync_over_90_balances,
)
from apps.invoicing.models import Invoice


@pytest.fixture
def customer(db):
    c = Customer.objects.create(
        customer_number="AGE-TEST",
        name="Aging Test Corp",
        credit_code="A",
        credit_limit=Decimal("100000"),
        terms_code="N30",
    )
    CustomerAnnex.objects.create(customer=c)
    return c


def _make_invoice(customer, order_number_seq, invoice_date, total, amount_paid=Decimal("0")):
    """Create an invoice without an order (for isolated aging tests)."""
    from apps.orders.models import Order
    order = Order.objects.create(
        order_number=f"AGE-ORD-{order_number_seq:04d}",
        customer=customer,
        placed_by="TEST",
        order_date=invoice_date,
        terms="N30",
        queue_status="IVQ",
    )
    return Invoice.objects.create(
        invoice_number=f"AGE-INV-{order_number_seq:04d}",
        order=order,
        customer=customer,
        invoice_date=invoice_date,
        due_date=invoice_date + datetime.timedelta(days=30),
        subtotal=total,
        total=total,
        amount_paid=amount_paid,
        status="OPEN" if amount_paid < total else "PAID",
        terms="N30",
    )


@pytest.mark.django_db
class TestAgeInvoice:
    def test_age_uses_due_date_when_present(self, customer):
        today = datetime.date.today()
        inv = _make_invoice(customer, 1, today - datetime.timedelta(days=45), Decimal("100"))
        assert age_invoice(inv) == 45 - 30

    def test_age_relative_to_as_of(self, customer):
        today = datetime.date.today()
        inv = _make_invoice(customer, 2, today - datetime.timedelta(days=100), Decimal("50"))
        as_of = today - datetime.timedelta(days=50)
        assert age_invoice(inv, as_of=as_of) == 50 - 30


@pytest.mark.django_db
class TestArAgingByCustomer:
    def test_empty_when_no_open_invoices(self, customer):
        assert ar_aging_by_customer() == []

    def test_buckets_by_due_date(self, customer):
        today = datetime.date.today()
        _make_invoice(customer, 10, today - datetime.timedelta(days=10), Decimal("100"))   # current
        _make_invoice(customer, 11, today - datetime.timedelta(days=75), Decimal("200"))   # 31-60 (45d past due)
        _make_invoice(customer, 12, today - datetime.timedelta(days=110), Decimal("300"))  # 61-90 (80d past due)
        _make_invoice(customer, 13, today - datetime.timedelta(days=200), Decimal("400"))  # over 90

        rows = ar_aging_by_customer()
        assert len(rows) == 1
        row = rows[0]
        assert row.customer_number == "AGE-TEST"
        assert row.invoice_count == 4
        assert row.buckets.current == Decimal("100.00")
        assert row.buckets.days_31_60 == Decimal("200.00")
        assert row.buckets.days_61_90 == Decimal("300.00")
        assert row.buckets.over_90 == Decimal("400.00")
        assert row.buckets.total == Decimal("1000.00")

    def test_excludes_paid_invoices(self, customer):
        today = datetime.date.today()
        # Fully paid — should be excluded even though it's OPEN-dated
        inv = _make_invoice(customer, 20, today - datetime.timedelta(days=10), Decimal("500"), amount_paid=Decimal("500"))
        # Partially paid — remaining outstanding should count
        inv2 = _make_invoice(customer, 21, today - datetime.timedelta(days=5), Decimal("400"), amount_paid=Decimal("100"))
        rows = ar_aging_by_customer()
        assert len(rows) == 1
        assert rows[0].buckets.current == Decimal("300.00")

    def test_sorts_by_total_desc(self, db):
        today = datetime.date.today()
        c1 = Customer.objects.create(customer_number="AGE-A", name="A", credit_limit=Decimal("0"))
        c2 = Customer.objects.create(customer_number="AGE-B", name="B", credit_limit=Decimal("0"))
        CustomerAnnex.objects.create(customer=c1)
        CustomerAnnex.objects.create(customer=c2)
        _make_invoice(c1, 100, today - datetime.timedelta(days=5), Decimal("100"))
        _make_invoice(c2, 101, today - datetime.timedelta(days=5), Decimal("5000"))

        rows = ar_aging_by_customer()
        assert [r.customer_number for r in rows] == ["AGE-B", "AGE-A"]


@pytest.mark.django_db
class TestArAgingTotals:
    def test_totals_sum_across_customers(self, db):
        today = datetime.date.today()
        c1 = Customer.objects.create(customer_number="AGE-X", name="X", credit_limit=Decimal("0"))
        c2 = Customer.objects.create(customer_number="AGE-Y", name="Y", credit_limit=Decimal("0"))
        CustomerAnnex.objects.create(customer=c1)
        CustomerAnnex.objects.create(customer=c2)
        _make_invoice(c1, 200, today - datetime.timedelta(days=10), Decimal("100"))
        _make_invoice(c2, 201, today - datetime.timedelta(days=200), Decimal("800"))

        totals = ar_aging_totals()
        assert totals.current == Decimal("100.00")
        assert totals.over_90 == Decimal("800.00")
        assert totals.total == Decimal("900.00")


@pytest.mark.django_db
class TestSyncOver90Balances:
    def test_over_90_balance_synced_from_aging(self, customer):
        today = datetime.date.today()
        _make_invoice(customer, 300, today - datetime.timedelta(days=10), Decimal("100"))
        _make_invoice(customer, 301, today - datetime.timedelta(days=200), Decimal("750"))

        updated = sync_over_90_balances()
        customer.refresh_from_db()
        assert customer.over_90_balance == Decimal("750.00")
        assert updated == 1

    def test_customer_with_no_over_90_resets_to_zero(self, customer):
        customer.over_90_balance = Decimal("999.99")
        customer.save(update_fields=["over_90_balance"])
        today = datetime.date.today()
        _make_invoice(customer, 400, today - datetime.timedelta(days=10), Decimal("100"))

        sync_over_90_balances()
        customer.refresh_from_db()
        assert customer.over_90_balance == Decimal("0.00")
