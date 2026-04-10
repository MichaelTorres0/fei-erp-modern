import pytest
from decimal import Decimal
from datetime import date
from apps.customers.tests.factories import CustomerFactory
from apps.products.tests.factories import ProductFactory, WarehouseInventoryFactory
from apps.pricing.tests.factories import CustomerSpecialPriceFactory
from apps.orders.tests.factories import OrderFactory
from apps.orders.services import check_credit, create_order, transition_queue
from apps.orders.models import Order

pytestmark = pytest.mark.django_db


class TestCheckCredit:
    def test_credit_code_a_auto_approves(self):
        customer = CustomerFactory(credit_code="A")
        result = check_credit(customer, Decimal("99999.99"))
        assert result.approved is True
        assert result.queue == "MGQ"

    def test_credit_code_d_auto_holds(self):
        customer = CustomerFactory(credit_code="D")
        result = check_credit(customer, Decimal("1.00"))
        assert result.approved is False
        assert result.queue == "CHQ"

    def test_credit_code_h_auto_holds(self):
        customer = CustomerFactory(credit_code="H")
        result = check_credit(customer, Decimal("1.00"))
        assert result.approved is False
        assert result.queue == "CHQ"

    def test_over_90_balance_holds(self):
        customer = CustomerFactory(credit_code="", over_90_balance=500.00, credit_limit=99999)
        result = check_credit(customer, Decimal("100.00"))
        assert result.approved is False
        assert result.queue == "CHQ"

    def test_exceeds_credit_limit_holds(self):
        customer = CustomerFactory(
            credit_code="",
            credit_limit=10000.00,
            ar_balance=8000.00,
            open_order_amount=1500.00,
            over_90_balance=0,
        )
        result = check_credit(customer, Decimal("1000.00"))
        assert result.approved is False
        assert result.queue == "CHQ"

    def test_within_credit_limit_approves(self):
        customer = CustomerFactory(
            credit_code="",
            credit_limit=10000.00,
            ar_balance=3000.00,
            open_order_amount=1000.00,
            over_90_balance=0,
        )
        result = check_credit(customer, Decimal("2000.00"))
        assert result.approved is True
        assert result.queue == "MGQ"


class TestCreateOrder:
    def test_create_basic_order(self):
        customer = CustomerFactory(credit_code="A", terms_code="N30", affiliation="GRP1")
        product = ProductFactory(list_price=25.00)
        WarehouseInventoryFactory(product=product, warehouse_code="NY", on_hand_qty=100)
        lines = [{"product_id": product.pk, "qty_ordered": 5, "warehouse_code": "NY"}]
        order = create_order(customer=customer, lines=lines, placed_by="TEST")
        assert order.order_number.startswith("ORD-")
        assert order.customer == customer
        assert order.affiliation == "GRP1"
        assert order.terms == "N30"
        assert order.queue_status == "MGQ"
        assert order.lines.count() == 1
        line = order.lines.first()
        assert line.qty_ordered == 5
        assert line.qty_open == 5
        assert line.net_price == Decimal("25.0000")
        assert order.subtotal == Decimal("125.00")
        assert order.audit_trail.count() >= 1

    def test_create_order_credit_hold(self):
        customer = CustomerFactory(credit_code="D")
        product = ProductFactory(list_price=10.00)
        lines = [{"product_id": product.pk, "qty_ordered": 1, "warehouse_code": "NY"}]
        order = create_order(customer=customer, lines=lines, placed_by="TEST")
        assert order.queue_status == "CHQ"

    def test_create_order_with_special_pricing(self):
        customer = CustomerFactory(credit_code="A")
        product = ProductFactory(list_price=50.00)
        CustomerSpecialPriceFactory(
            customer=customer, product=product,
            gross_price=30.00, net_price=27.00, discount_1=10,
        )
        lines = [{"product_id": product.pk, "qty_ordered": 2, "warehouse_code": "NY"}]
        order = create_order(customer=customer, lines=lines, placed_by="TEST")
        line = order.lines.first()
        assert line.unit_price == Decimal("30.00")
        assert line.net_price == Decimal("27.00")
        assert order.subtotal == Decimal("54.00")


class TestTransitionQueue:
    def test_valid_transition_oeq_to_mgq(self):
        order = OrderFactory(queue_status="OEQ")
        updated = transition_queue(order, "MGQ", "admin")
        assert updated.queue_status == "MGQ"
        assert updated.audit_trail.filter(event_code="MGQ").exists()

    def test_valid_transition_mgq_to_ptq(self):
        order = OrderFactory(queue_status="MGQ")
        updated = transition_queue(order, "PTQ", "admin")
        assert updated.queue_status == "PTQ"

    def test_invalid_transition_raises(self):
        order = OrderFactory(queue_status="OEQ")
        with pytest.raises(ValueError, match="Invalid queue transition"):
            transition_queue(order, "IVQ", "admin")

    def test_chq_to_mgq(self):
        order = OrderFactory(queue_status="CHQ")
        updated = transition_queue(order, "MGQ", "manager")
        assert updated.queue_status == "MGQ"

    def test_mgq_to_fqq(self):
        order = OrderFactory(queue_status="MGQ")
        updated = transition_queue(order, "FQQ", "admin")
        assert updated.queue_status == "FQQ"

    def test_fqq_to_ptq(self):
        order = OrderFactory(queue_status="FQQ")
        updated = transition_queue(order, "PTQ", "admin")
        assert updated.queue_status == "PTQ"

    def test_mgq_to_crdq(self):
        order = OrderFactory(queue_status="MGQ")
        updated = transition_queue(order, "CRDQ", "admin")
        assert updated.queue_status == "CRDQ"

    def test_crdq_to_ptq(self):
        order = OrderFactory(queue_status="CRDQ")
        updated = transition_queue(order, "PTQ", "admin")
        assert updated.queue_status == "PTQ"

    def test_mgq_to_srq(self):
        order = OrderFactory(queue_status="MGQ")
        updated = transition_queue(order, "SRQ", "admin")
        assert updated.queue_status == "SRQ"

    def test_srq_to_mgq(self):
        order = OrderFactory(queue_status="SRQ")
        updated = transition_queue(order, "MGQ", "admin")
        assert updated.queue_status == "MGQ"

    def test_ptq_to_boq(self):
        order = OrderFactory(queue_status="PTQ")
        updated = transition_queue(order, "BOQ", "admin")
        assert updated.queue_status == "BOQ"

    def test_boq_to_ptq(self):
        order = OrderFactory(queue_status="BOQ")
        updated = transition_queue(order, "PTQ", "admin")
        assert updated.queue_status == "PTQ"

    def test_mgq_to_pdq(self):
        order = OrderFactory(queue_status="MGQ")
        updated = transition_queue(order, "PDQ", "admin")
        assert updated.queue_status == "PDQ"

    def test_pdq_to_mgq(self):
        order = OrderFactory(queue_status="PDQ")
        updated = transition_queue(order, "MGQ", "admin")
        assert updated.queue_status == "MGQ"

    def test_ptq_to_pq(self):
        order = OrderFactory(queue_status="PTQ")
        updated = transition_queue(order, "PQ", "admin")
        assert updated.queue_status == "PQ"

    def test_pq_to_ptq(self):
        order = OrderFactory(queue_status="PQ")
        updated = transition_queue(order, "PTQ", "admin")
        assert updated.queue_status == "PTQ"
