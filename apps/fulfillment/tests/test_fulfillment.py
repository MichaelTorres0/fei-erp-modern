from decimal import Decimal

import pytest

from apps.customers.models import Customer, CustomerAnnex
from apps.fulfillment.models import PickTicket, PickTicketLine
from apps.fulfillment.services import generate_pick_ticket_from_order, mark_picked, mark_shipped
from apps.orders.services import create_order, transition_queue
from apps.products.models import Product, WarehouseInventory


@pytest.fixture
def customer(db):
    c = Customer.objects.create(
        customer_number="FF-TEST",
        name="Fulfillment Test Corp",
        credit_code="A",
        credit_limit=Decimal("100000"),
    )
    CustomerAnnex.objects.create(customer=c)
    return c


@pytest.fixture
def product(db):
    p = Product.objects.create(
        product_number="FF-PROD",
        description="Fulfillment Test Product",
        list_price=Decimal("25.0000"),
        standard_cost=Decimal("10.0000"),
    )
    WarehouseInventory.objects.create(product=p, warehouse_code="NY", on_hand_qty=100)
    return p


@pytest.mark.django_db
class TestPickTicketGeneration:
    def test_generate_from_order(self, customer, product):
        order = create_order(
            customer=customer,
            lines=[{"product_id": product.id, "qty_ordered": 5}],
        )
        ticket = generate_pick_ticket_from_order(order)

        assert ticket.ticket_number.startswith("PT-")
        assert ticket.order == order
        assert ticket.status == "OPEN"
        assert ticket.warehouse_code == "NY"
        assert ticket.lines.count() == 1
        line = ticket.lines.first()
        assert line.qty_ordered == 5
        assert line.qty_picked == 0

    def test_pick_ticket_auto_generated_on_ptq(self, customer, product):
        order = create_order(
            customer=customer,
            lines=[{"product_id": product.id, "qty_ordered": 2}],
        )
        transition_queue(order, "PTQ", "TEST")

        order.refresh_from_db()
        assert hasattr(order, "pick_ticket")
        assert order.pick_ticket.status == "OPEN"

    def test_generate_idempotent(self, customer, product):
        order = create_order(
            customer=customer,
            lines=[{"product_id": product.id, "qty_ordered": 1}],
        )
        t1 = generate_pick_ticket_from_order(order)
        t2 = generate_pick_ticket_from_order(order)
        assert t1.id == t2.id


@pytest.mark.django_db
class TestPickAndShipWorkflow:
    def test_mark_picked_updates_qty_shipped_on_order(self, customer, product):
        order = create_order(
            customer=customer,
            lines=[{"product_id": product.id, "qty_ordered": 3}],
        )
        transition_queue(order, "PTQ", "TEST")
        ticket = order.pick_ticket

        mark_picked(ticket, operator="PICKER_01")

        ticket.refresh_from_db()
        assert ticket.status == "PICKED"
        assert ticket.assigned_to == "PICKER_01"
        assert ticket.picked_at is not None

        order.refresh_from_db()
        for line in order.lines.all():
            assert line.qty_shipped == line.qty_ordered
            assert line.qty_open == 0

    def test_mark_shipped_transitions_order_and_creates_invoice(self, customer, product):
        order = create_order(
            customer=customer,
            lines=[{"product_id": product.id, "qty_ordered": 2}],
        )
        transition_queue(order, "PTQ", "TEST")
        ticket = order.pick_ticket
        mark_picked(ticket, operator="PICKER_01")

        mark_shipped(ticket, tracking_number="1Z999AA1", operator="SHIPPER_01")

        ticket.refresh_from_db()
        assert ticket.status == "SHIPPED"
        assert ticket.tracking_number == "1Z999AA1"

        order.refresh_from_db()
        assert order.queue_status == "IVQ"
        assert hasattr(order, "invoice")

    def test_shipping_deducts_inventory(self, customer, product):
        inv_before = WarehouseInventory.objects.get(product=product, warehouse_code="NY")
        on_hand_before = inv_before.on_hand_qty

        order = create_order(
            customer=customer,
            lines=[{"product_id": product.id, "qty_ordered": 10}],
        )
        transition_queue(order, "PTQ", "TEST")
        ticket = order.pick_ticket
        mark_picked(ticket, operator="TEST")
        mark_shipped(ticket, tracking_number="TRACK123", operator="TEST")

        inv_after = WarehouseInventory.objects.get(product=product, warehouse_code="NY")
        assert inv_after.on_hand_qty == on_hand_before - 10
