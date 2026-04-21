import datetime
from decimal import Decimal

import pytest

from apps.customers.models import Customer, CustomerAnnex
from apps.invoicing.models import Invoice, InvoiceLine
from apps.invoicing.services import generate_invoice_from_order, record_payment
from apps.orders.services import create_order, transition_queue
from apps.products.models import Product, WarehouseInventory


@pytest.fixture
def customer(db):
    c = Customer.objects.create(
        customer_number="INV-TEST",
        name="Invoice Test Corp",
        credit_code="A",
        credit_limit=Decimal("100000"),
        terms_code="N30",
    )
    CustomerAnnex.objects.create(customer=c)
    return c


@pytest.fixture
def product(db):
    p = Product.objects.create(
        product_number="INV-PROD",
        description="Invoice Test Product",
        list_price=Decimal("50.0000"),
        standard_cost=Decimal("20.0000"),
    )
    WarehouseInventory.objects.create(product=p, warehouse_code="NY", on_hand_qty=100)
    return p


@pytest.mark.django_db
class TestInvoiceGeneration:
    def test_generate_invoice_from_order(self, customer, product):
        order = create_order(
            customer=customer,
            lines=[{"product_id": product.id, "qty_ordered": 4}],
        )
        invoice = generate_invoice_from_order(order)

        assert invoice.invoice_number.startswith("INV-")
        assert invoice.customer == customer
        assert invoice.order == order
        assert invoice.status == "OPEN"
        assert invoice.subtotal == Decimal("200.00")
        assert invoice.total == Decimal("200.00")
        assert invoice.lines.count() == 1
        line = invoice.lines.first()
        assert line.qty_shipped == 4
        assert line.extension == Decimal("200.00")

    def test_invoice_auto_computes_due_date_from_terms(self, customer, product):
        order = create_order(
            customer=customer,
            lines=[{"product_id": product.id, "qty_ordered": 1}],
        )
        invoice = generate_invoice_from_order(order)

        expected_due = invoice.invoice_date + datetime.timedelta(days=30)
        assert invoice.due_date == expected_due

    def test_invoice_updates_customer_ar_balance(self, customer, product):
        ar_before = customer.ar_balance
        ytd_before = customer.ytd_sales

        order = create_order(
            customer=customer,
            lines=[{"product_id": product.id, "qty_ordered": 2}],
        )
        invoice = generate_invoice_from_order(order)

        customer.refresh_from_db()
        assert customer.ar_balance == ar_before + invoice.total
        assert customer.ytd_sales == ytd_before + invoice.total

    def test_invoice_auto_generated_on_ivq_transition(self, customer, product):
        order = create_order(
            customer=customer,
            lines=[{"product_id": product.id, "qty_ordered": 3}],
        )
        assert not hasattr(order, "invoice") or order.invoice is None

        transition_queue(order, "PTQ", "TEST")
        transition_queue(order, "IVQ", "TEST")

        order.refresh_from_db()
        assert hasattr(order, "invoice")
        assert order.invoice.status == "OPEN"
        assert order.invoice.subtotal == Decimal("150.00")

    def test_generate_invoice_idempotent(self, customer, product):
        order = create_order(
            customer=customer,
            lines=[{"product_id": product.id, "qty_ordered": 1}],
        )
        inv1 = generate_invoice_from_order(order)
        inv2 = generate_invoice_from_order(order)
        assert inv1.id == inv2.id


@pytest.mark.django_db
class TestPayments:
    def test_full_payment_marks_paid(self, customer, product):
        order = create_order(
            customer=customer,
            lines=[{"product_id": product.id, "qty_ordered": 2}],
        )
        invoice = generate_invoice_from_order(order)

        record_payment(invoice, Decimal("100.00"))
        invoice.refresh_from_db()

        assert invoice.amount_paid == Decimal("100.00")
        assert invoice.status == "PAID"
        assert invoice.amount_due == Decimal("0.00")

    def test_partial_payment_stays_open(self, customer, product):
        order = create_order(
            customer=customer,
            lines=[{"product_id": product.id, "qty_ordered": 4}],
        )
        invoice = generate_invoice_from_order(order)

        record_payment(invoice, Decimal("50.00"))
        invoice.refresh_from_db()

        assert invoice.amount_paid == Decimal("50.00")
        assert invoice.status == "OPEN"
        assert invoice.amount_due == Decimal("150.00")

    def test_payment_reduces_customer_ar(self, customer, product):
        order = create_order(
            customer=customer,
            lines=[{"product_id": product.id, "qty_ordered": 2}],
        )
        invoice = generate_invoice_from_order(order)

        ar_after_invoice = customer.ar_balance
        record_payment(invoice, Decimal("60.00"))

        customer.refresh_from_db()
        assert customer.ar_balance == ar_after_invoice - Decimal("60.00")
        assert customer.last_payment_amount == Decimal("60.00")
        assert customer.last_payment_date == datetime.date.today()
