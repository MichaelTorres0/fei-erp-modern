from decimal import Decimal

import pytest

from apps.customers.models import Customer, CustomerAnnex
from apps.fulfillment.services import mark_picked, mark_shipped
from apps.invoicing.models import Invoice
from apps.orders.services import create_order, transition_queue
from apps.products.models import Product, WarehouseInventory
from apps.returns.models import RMA
from apps.returns.services import (
    cancel_rma,
    create_rma,
    issue_credit_memo,
    receive_rma,
)


@pytest.fixture
def customer(db):
    c = Customer.objects.create(
        customer_number="RMA-TEST",
        name="RMA Test Corp",
        credit_code="A",
        credit_limit=Decimal("100000"),
        terms_code="N30",
    )
    CustomerAnnex.objects.create(customer=c)
    return c


@pytest.fixture
def product(db):
    p = Product.objects.create(
        product_number="RMA-PROD",
        description="RMA Test Product",
        list_price=Decimal("40.0000"),
        standard_cost=Decimal("15.0000"),
    )
    WarehouseInventory.objects.create(product=p, warehouse_code="NY", on_hand_qty=100)
    return p


def _shipped_invoice(customer, product, qty=5):
    """Helper: create an order, push it all the way to a shipped invoice."""
    order = create_order(
        customer=customer,
        lines=[{"product_id": product.id, "qty_ordered": qty}],
    )
    transition_queue(order, "PTQ", "TEST")
    ticket = order.pick_tickets.first()
    mark_picked(ticket, operator="TEST")
    mark_shipped(ticket, tracking_number="TRK", operator="TEST")
    order.refresh_from_db()
    return order.invoice


@pytest.mark.django_db
class TestCreateRMA:
    def test_authorize_rma_calculates_credit(self, customer, product):
        invoice = _shipped_invoice(customer, product, qty=5)
        line = invoice.lines.first()

        rma = create_rma(
            invoice=invoice,
            lines=[{"invoice_line_id": line.id, "qty_returned": 2}],
            reason="DEFECTIVE",
            operator="CS-01",
        )

        assert rma.rma_number.startswith("RMA-")
        assert rma.status == "OPEN"
        assert rma.customer == customer
        assert rma.invoice == invoice
        assert rma.credit_amount == Decimal("80.00")  # 2 * 40.00
        assert rma.lines.count() == 1
        assert rma.lines.first().qty_returned == 2

    def test_rejects_qty_exceeding_invoiced(self, customer, product):
        invoice = _shipped_invoice(customer, product, qty=5)
        line = invoice.lines.first()
        with pytest.raises(ValueError, match="cannot return"):
            create_rma(
                invoice=invoice,
                lines=[{"invoice_line_id": line.id, "qty_returned": 6}],
            )

    def test_rejects_cumulative_qty_exceeding_invoiced(self, customer, product):
        invoice = _shipped_invoice(customer, product, qty=5)
        line = invoice.lines.first()
        create_rma(
            invoice=invoice,
            lines=[{"invoice_line_id": line.id, "qty_returned": 3}],
        )
        # Only 2 available now, asking for 3 should fail
        with pytest.raises(ValueError, match="cannot return"):
            create_rma(
                invoice=invoice,
                lines=[{"invoice_line_id": line.id, "qty_returned": 3}],
            )

    def test_cancelled_rmas_do_not_block_new_returns(self, customer, product):
        invoice = _shipped_invoice(customer, product, qty=5)
        line = invoice.lines.first()
        rma = create_rma(
            invoice=invoice,
            lines=[{"invoice_line_id": line.id, "qty_returned": 4}],
        )
        cancel_rma(rma, reason="wrong RMA")
        # All 5 should be available again
        rma2 = create_rma(
            invoice=invoice,
            lines=[{"invoice_line_id": line.id, "qty_returned": 5}],
        )
        assert rma2.credit_amount == Decimal("200.00")

    def test_requires_at_least_one_line(self, customer, product):
        invoice = _shipped_invoice(customer, product, qty=2)
        with pytest.raises(ValueError):
            create_rma(invoice=invoice, lines=[])


@pytest.mark.django_db
class TestReceiveRMA:
    def test_receive_sets_qty_received_and_restocks(self, customer, product):
        invoice = _shipped_invoice(customer, product, qty=5)
        # Inventory was deducted on ship (100 - 5 = 95)
        inv_after_ship = WarehouseInventory.objects.get(product=product, warehouse_code="NY")
        assert inv_after_ship.on_hand_qty == 95

        line = invoice.lines.first()
        rma = create_rma(
            invoice=invoice,
            lines=[{"invoice_line_id": line.id, "qty_returned": 3}],
            restock_to_warehouse="NY",
        )
        receive_rma(rma)

        rma.refresh_from_db()
        assert rma.status == "RECEIVED"
        assert rma.received_date is not None
        assert rma.lines.first().qty_received == 3

        inv_after_rma = WarehouseInventory.objects.get(product=product, warehouse_code="NY")
        assert inv_after_rma.on_hand_qty == 98  # 95 + 3 restocked

    def test_receive_skips_restock_when_flag_false(self, customer, product):
        invoice = _shipped_invoice(customer, product, qty=5)
        line = invoice.lines.first()
        rma = create_rma(
            invoice=invoice,
            lines=[{"invoice_line_id": line.id, "qty_returned": 2, "restock": False}],
            restock_to_warehouse="NY",
        )
        inv_before = WarehouseInventory.objects.get(product=product, warehouse_code="NY").on_hand_qty
        receive_rma(rma)
        inv_after = WarehouseInventory.objects.get(product=product, warehouse_code="NY").on_hand_qty
        assert inv_after == inv_before  # no restock

    def test_cannot_receive_non_open_rma(self, customer, product):
        invoice = _shipped_invoice(customer, product, qty=2)
        line = invoice.lines.first()
        rma = create_rma(
            invoice=invoice,
            lines=[{"invoice_line_id": line.id, "qty_returned": 1}],
        )
        receive_rma(rma)
        with pytest.raises(ValueError, match="Cannot receive"):
            receive_rma(rma)


@pytest.mark.django_db
class TestIssueCreditMemo:
    def test_credit_memo_reduces_ar_and_ytd(self, customer, product):
        invoice = _shipped_invoice(customer, product, qty=5)
        customer.refresh_from_db()
        ar_before = customer.ar_balance
        ytd_before = customer.ytd_sales
        assert ar_before == Decimal("200.00")  # 5 * 40.00

        line = invoice.lines.first()
        rma = create_rma(
            invoice=invoice,
            lines=[{"invoice_line_id": line.id, "qty_returned": 2}],
        )
        receive_rma(rma)
        issue_credit_memo(rma, operator="CS-01")

        rma.refresh_from_db()
        assert rma.status == "CREDITED"
        assert rma.credit_memo_number.startswith("CM-")
        assert rma.credited_date is not None

        customer.refresh_from_db()
        assert customer.ar_balance == ar_before - Decimal("80.00")
        assert customer.ytd_sales == ytd_before - Decimal("80.00")

    def test_credit_memo_applied_against_invoice(self, customer, product):
        invoice = _shipped_invoice(customer, product, qty=5)  # total $200
        line = invoice.lines.first()
        rma = create_rma(
            invoice=invoice,
            lines=[{"invoice_line_id": line.id, "qty_returned": 2}],
        )
        receive_rma(rma)
        issue_credit_memo(rma)

        invoice.refresh_from_db()
        assert invoice.amount_paid == Decimal("80.00")
        assert invoice.status == "OPEN"
        assert invoice.amount_due == Decimal("120.00")

    def test_full_credit_marks_invoice_paid(self, customer, product):
        invoice = _shipped_invoice(customer, product, qty=3)  # total $120
        line = invoice.lines.first()
        rma = create_rma(
            invoice=invoice,
            lines=[{"invoice_line_id": line.id, "qty_returned": 3}],
        )
        receive_rma(rma)
        issue_credit_memo(rma)

        invoice.refresh_from_db()
        assert invoice.status == "PAID"
        assert invoice.amount_due == Decimal("0.00")

    def test_cannot_credit_before_receiving(self, customer, product):
        invoice = _shipped_invoice(customer, product, qty=2)
        line = invoice.lines.first()
        rma = create_rma(
            invoice=invoice,
            lines=[{"invoice_line_id": line.id, "qty_returned": 1}],
        )
        with pytest.raises(ValueError, match="Cannot issue"):
            issue_credit_memo(rma)


@pytest.mark.django_db
class TestCancelRMA:
    def test_cancel_sets_status(self, customer, product):
        invoice = _shipped_invoice(customer, product, qty=2)
        line = invoice.lines.first()
        rma = create_rma(
            invoice=invoice,
            lines=[{"invoice_line_id": line.id, "qty_returned": 1}],
        )
        cancel_rma(rma, reason="customer changed mind")
        rma.refresh_from_db()
        assert rma.status == "CANCELLED"
        assert "customer changed mind" in rma.notes

    def test_cannot_cancel_credited_rma(self, customer, product):
        invoice = _shipped_invoice(customer, product, qty=2)
        line = invoice.lines.first()
        rma = create_rma(
            invoice=invoice,
            lines=[{"invoice_line_id": line.id, "qty_returned": 1}],
        )
        receive_rma(rma)
        issue_credit_memo(rma)
        with pytest.raises(ValueError, match="already been credited"):
            cancel_rma(rma)
