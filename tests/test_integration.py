"""
End-to-end integration tests that exercise full business workflows
across all modules: Customer -> Product -> Pricing -> Order -> Queue.
"""
from decimal import Decimal

import pytest
from django.test import TestCase

from apps.customers.models import Customer, CustomerAnnex
from apps.customers.tests.factories import CustomerFactory
from apps.orders.models import Order, OrderLine, OrderAudit
from apps.orders.services import (
    create_order,
    transition_queue,
    check_credit,
    check_inventory,
    sync_customer_open_orders,
)
from apps.pricing.models import CustomerSpecialPrice, AffiliationPrice
from apps.products.models import Product, KitComponent, WarehouseInventory, InventoryCommitment
from apps.products.services import get_availability, get_kit_availability
from apps.products.tests.factories import ProductFactory


@pytest.mark.django_db
class TestOrderCreationWorkflow:
    """Full order creation workflow: pricing lookup -> credit check -> queue routing."""

    def setup_method(self):
        self.customer = Customer.objects.create(
            customer_number="INT-001",
            name="Integration Test Corp",
            city="New York",
            state="NY",
            credit_code="A",
            credit_limit=Decimal("50000"),
            ar_balance=Decimal("5000"),
            terms_code="N30",
            salesman="TestRep",
            affiliation="TEST",
        )
        CustomerAnnex.objects.create(customer=self.customer)

        self.product = Product.objects.create(
            product_number="INT-P001",
            description="Test Product",
            list_price=Decimal("100.0000"),
            standard_cost=Decimal("40.0000"),
        )
        WarehouseInventory.objects.create(
            product=self.product,
            warehouse_code="NY",
            on_hand_qty=100,
        )

    def test_full_order_lifecycle(self):
        """Order creation -> credit check -> queue transitions -> IVQ."""
        order = create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.id, "qty_ordered": 10}],
            placed_by="INTEGRATION",
        )

        # Verify order created with correct pricing
        assert order.subtotal == Decimal("1000.00")
        line = order.lines.first()
        assert line.net_price == Decimal("100.0000")
        assert line.extension == Decimal("1000.00")
        assert line.qty_open == 10

        # Credit code A -> auto-approved to MGQ
        assert order.queue_status == "MGQ"

        # Customer open_order_amount updated
        self.customer.refresh_from_db()
        assert self.customer.open_order_amount == Decimal("1000.00")

        # Transition through queue: MGQ -> PTQ -> IVQ
        transition_queue(order, "PTQ", "INTEGRATION")
        assert order.queue_status == "PTQ"

        transition_queue(order, "IVQ", "INTEGRATION")
        assert order.queue_status == "IVQ"

        # Open order amount cleared after IVQ
        self.customer.refresh_from_db()
        assert self.customer.open_order_amount == Decimal("0")

        # Audit trail has full history
        audits = list(order.audit_trail.values_list("event_code", flat=True))
        assert audits == ["MGQ", "PTQ", "IVQ"]

    def test_special_pricing_applied(self):
        """Customer special pricing overrides base product price."""
        CustomerSpecialPrice.objects.create(
            customer=self.customer,
            product=self.product,
            gross_price=Decimal("90.0000"),
            discount_1=Decimal("10.00"),
            net_price=Decimal("81.0000"),
        )

        order = create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.id, "qty_ordered": 5}],
        )

        line = order.lines.first()
        assert line.unit_price == Decimal("90.0000")
        assert line.net_price == Decimal("81.0000")
        assert line.extension == Decimal("405.00")
        assert order.subtotal == Decimal("405.00")

    def test_credit_hold_workflow(self):
        """Order exceeding credit limit goes to CHQ, then released to MGQ."""
        self.customer.credit_code = ""
        self.customer.credit_limit = Decimal("500")
        self.customer.save()

        order = create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.id, "qty_ordered": 10}],
        )

        # Subtotal $1000 > credit limit $500 -> CHQ
        assert order.queue_status == "CHQ"

        # Release from credit hold
        transition_queue(order, "MGQ", "CREDIT_MGR")
        assert order.queue_status == "MGQ"

        # Verify audit trail
        events = list(order.audit_trail.values_list("event_code", flat=True))
        assert events == ["CHQ", "MGQ"]

    def test_invalid_queue_transition_rejected(self):
        """Invalid queue transitions raise ValueError."""
        order = create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.id, "qty_ordered": 1}],
        )
        assert order.queue_status == "MGQ"

        with pytest.raises(ValueError, match="Invalid queue transition"):
            transition_queue(order, "IVQ", "TEST")  # MGQ -> IVQ not allowed

    def test_multiple_orders_accumulate_open_amount(self):
        """Multiple open orders accumulate in customer open_order_amount."""
        order1 = create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.id, "qty_ordered": 5}],
        )
        self.customer.refresh_from_db()
        assert self.customer.open_order_amount == Decimal("500.00")

        order2 = create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.id, "qty_ordered": 3}],
        )
        self.customer.refresh_from_db()
        assert self.customer.open_order_amount == Decimal("800.00")

        # Invoice order1
        transition_queue(order1, "PTQ", "TEST")
        transition_queue(order1, "IVQ", "TEST")
        self.customer.refresh_from_db()
        assert self.customer.open_order_amount == Decimal("300.00")


@pytest.mark.django_db
class TestDropShipWorkflow:
    """Drop-ship order handling."""

    def setup_method(self):
        self.customer = Customer.objects.create(
            customer_number="DS-001",
            name="Drop Ship Customer",
            credit_code="A",
            credit_limit=Decimal("100000"),
        )
        CustomerAnnex.objects.create(customer=self.customer)

        self.ds_product = Product.objects.create(
            product_number="DS-P001",
            description="Drop Ship Product",
            list_price=Decimal("500.0000"),
            standard_cost=Decimal("250.0000"),
            is_drop_ship=True,
        )
        WarehouseInventory.objects.create(
            product=self.ds_product,
            warehouse_code="D",
            on_hand_qty=0,
        )

    def test_drop_ship_auto_routing(self):
        """Drop-ship products auto-route to D warehouse and flag order."""
        order = create_order(
            customer=self.customer,
            lines=[{"product_id": self.ds_product.id, "qty_ordered": 1}],
        )

        assert order.is_drop_ship is True
        line = order.lines.first()
        assert line.warehouse_code == "D"


@pytest.mark.django_db
class TestRouteToPickTicket:
    """Customer annex route_to_ptq flag."""

    def setup_method(self):
        self.customer = Customer.objects.create(
            customer_number="PTQ-001",
            name="PTQ Customer",
            credit_code="A",
            credit_limit=Decimal("100000"),
        )
        self.annex = CustomerAnnex.objects.create(
            customer=self.customer,
            route_to_ptq=True,
        )

        self.product = Product.objects.create(
            product_number="PTQ-P001",
            description="PTQ Product",
            list_price=Decimal("50.0000"),
            standard_cost=Decimal("20.0000"),
        )
        WarehouseInventory.objects.create(
            product=self.product,
            warehouse_code="NY",
            on_hand_qty=100,
        )

    def test_route_to_ptq_bypasses_mgq(self):
        """Customer with route_to_ptq skips MGQ and goes straight to PTQ."""
        order = create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.id, "qty_ordered": 2}],
        )

        assert order.queue_status == "PTQ"
        audits = list(order.audit_trail.values_list("event_code", flat=True))
        assert "MGQ" in audits  # First routed to MGQ by credit check
        assert "PTQ" in audits  # Then auto-routed to PTQ by annex flag


@pytest.mark.django_db
class TestInventoryIntegration:
    """Inventory availability checks integrated with order flow."""

    def setup_method(self):
        self.customer = Customer.objects.create(
            customer_number="INV-001",
            name="Inventory Test Corp",
            credit_code="A",
            credit_limit=Decimal("100000"),
        )
        CustomerAnnex.objects.create(customer=self.customer)

        self.product = Product.objects.create(
            product_number="INV-P001",
            description="Inventory Product",
            list_price=Decimal("25.0000"),
            standard_cost=Decimal("10.0000"),
        )
        WarehouseInventory.objects.create(
            product=self.product,
            warehouse_code="NY",
            on_hand_qty=50,
        )

    def test_inventory_check_warns_on_insufficient_stock(self):
        """check_inventory returns warnings when stock is insufficient."""
        warnings = check_inventory([
            {"product_id": self.product.id, "qty_ordered": 100, "warehouse_code": "NY"},
        ])
        assert len(warnings) == 1
        assert warnings[0].requested == 100
        assert warnings[0].available == 50

    def test_inventory_check_clean_when_sufficient(self):
        """check_inventory returns no warnings when stock is sufficient."""
        warnings = check_inventory([
            {"product_id": self.product.id, "qty_ordered": 10, "warehouse_code": "NY"},
        ])
        assert len(warnings) == 0

    def test_orders_reduce_available_inventory(self):
        """Creating orders reduces available inventory (committed qty increases)."""
        avail_before = get_availability(self.product, "NY")
        assert avail_before["NY"]["available"] == 50

        create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.id, "qty_ordered": 20}],
        )

        avail_after = get_availability(self.product, "NY")
        assert avail_after["NY"]["available"] == 30  # 50 - 20 committed

    def test_invoiced_orders_release_committed_inventory(self):
        """Orders that reach IVQ release committed inventory."""
        order = create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.id, "qty_ordered": 20}],
        )
        assert get_availability(self.product, "NY")["NY"]["available"] == 30

        transition_queue(order, "PTQ", "TEST")
        transition_queue(order, "IVQ", "TEST")

        # IVQ is not in ACTIVE_QUEUE_STATUSES, so committed drops
        assert get_availability(self.product, "NY")["NY"]["available"] == 50


@pytest.mark.django_db
class TestKitOrderWorkflow:
    """Kit product ordering with component inventory tracking."""

    def setup_method(self):
        self.customer = Customer.objects.create(
            customer_number="KIT-001",
            name="Kit Test Corp",
            credit_code="A",
            credit_limit=Decimal("100000"),
        )
        CustomerAnnex.objects.create(customer=self.customer)

        self.comp_a = Product.objects.create(
            product_number="KIT-CA",
            description="Component A",
            list_price=Decimal("10.0000"),
            standard_cost=Decimal("4.0000"),
        )
        self.comp_b = Product.objects.create(
            product_number="KIT-CB",
            description="Component B",
            list_price=Decimal("20.0000"),
            standard_cost=Decimal("8.0000"),
        )
        self.kit = Product.objects.create(
            product_number="KIT-PARENT",
            description="Test Kit",
            list_price=Decimal("35.0000"),
            standard_cost=Decimal("15.0000"),
            is_kit=True,
        )
        KitComponent.objects.create(parent_product=self.kit, component_product=self.comp_a, quantity_per_kit=2)
        KitComponent.objects.create(parent_product=self.kit, component_product=self.comp_b, quantity_per_kit=1)

        WarehouseInventory.objects.create(product=self.comp_a, warehouse_code="NY", on_hand_qty=100)
        WarehouseInventory.objects.create(product=self.comp_b, warehouse_code="NY", on_hand_qty=30)

    def test_kit_availability_limited_by_bottleneck(self):
        """Kit availability is limited by the component with least stock."""
        # comp_a: 100 / 2 per kit = 50 kits
        # comp_b: 30 / 1 per kit = 30 kits
        # Kit availability = min(50, 30) = 30
        avail = get_kit_availability(self.kit, "NY")
        assert avail == 30


@pytest.mark.django_db
class TestCreditCheckEdgeCases:
    """Credit check edge cases across different customer profiles."""

    def test_credit_code_d_always_holds(self):
        customer = Customer.objects.create(
            customer_number="CC-D",
            name="D-code customer",
            credit_code="D",
            credit_limit=Decimal("999999"),
        )
        result = check_credit(customer, Decimal("1"))
        assert not result.approved
        assert result.queue == "CHQ"

    def test_over_90_holds_even_with_plenty_of_credit(self):
        customer = Customer.objects.create(
            customer_number="CC-90",
            name="Over 90 customer",
            credit_code="",
            credit_limit=Decimal("999999"),
            over_90_balance=Decimal("100"),
        )
        result = check_credit(customer, Decimal("1"))
        assert not result.approved
        assert "Over 90" in result.reason

    def test_exposure_includes_ar_and_open_orders(self):
        customer = Customer.objects.create(
            customer_number="CC-EXP",
            name="Exposure test",
            credit_code="",
            credit_limit=Decimal("1000"),
            ar_balance=Decimal("400"),
            open_order_amount=Decimal("400"),
        )
        # 400 AR + 400 open + 300 new = 1100 > 1000 limit
        result = check_credit(customer, Decimal("300"))
        assert not result.approved
        assert "exceeded" in result.reason


@pytest.mark.django_db
class TestPricingTierIntegration:
    """Verify full pricing hierarchy in order context."""

    def setup_method(self):
        self.product = Product.objects.create(
            product_number="PT-001", description="Pricing Test Product",
            list_price=Decimal("100.0000"), dealer_price=Decimal("60.0000"),
            price_a=Decimal("80.0000"), price_b=Decimal("70.0000"),
            standard_cost=Decimal("30.0000"),
        )
        WarehouseInventory.objects.create(
            product=self.product, warehouse_code="NY", on_hand_qty=500,
        )

    def test_tier_cascade_special_to_affiliation_to_company(self):
        cust_special = Customer.objects.create(
            customer_number="PT-SP", name="Special Price Customer",
            credit_code="A", credit_limit=Decimal("999999"),
        )
        CustomerAnnex.objects.create(customer=cust_special)
        CustomerSpecialPrice.objects.create(
            customer=cust_special, product=self.product,
            gross_price=Decimal("50.0000"), net_price=Decimal("50.0000"),
        )

        cust_aff = Customer.objects.create(
            customer_number="PT-AF", name="Affiliation Customer",
            credit_code="A", credit_limit=Decimal("999999"),
            affiliation="TEST_AFF",
        )
        CustomerAnnex.objects.create(customer=cust_aff)
        AffiliationPrice.objects.create(
            affiliation_code="TEST_AFF", product=self.product,
            gross_price=Decimal("65.0000"), net_price=Decimal("65.0000"),
        )

        cust_best = Customer.objects.create(
            customer_number="PT-BC", name="BEST Customer",
            credit_code="A", credit_limit=Decimal("999999"),
            company_code="B",
        )
        CustomerAnnex.objects.create(customer=cust_best)

        cust_default = Customer.objects.create(
            customer_number="PT-DF", name="Default Customer",
            credit_code="A", credit_limit=Decimal("999999"),
        )
        CustomerAnnex.objects.create(customer=cust_default)

        lines = [{"product_id": self.product.pk, "qty_ordered": 1}]

        o1 = create_order(customer=cust_special, lines=lines)
        o2 = create_order(customer=cust_aff, lines=lines)
        o3 = create_order(customer=cust_best, lines=lines)
        o4 = create_order(customer=cust_default, lines=lines)

        assert o1.lines.first().net_price == Decimal("50.0000")
        assert o2.lines.first().net_price == Decimal("65.0000")
        assert o3.lines.first().net_price == Decimal("60.0000")
        assert o4.lines.first().net_price == Decimal("80.0000")


@pytest.mark.django_db
class TestExtendedQueueIntegration:
    def setup_method(self):
        self.customer = Customer.objects.create(
            customer_number="QI-001", name="Queue Test Corp",
            credit_code="A", credit_limit=Decimal("100000"),
        )
        CustomerAnnex.objects.create(customer=self.customer)
        self.product = Product.objects.create(
            product_number="QI-P001", description="Queue Test Product",
            list_price=Decimal("50.0000"), standard_cost=Decimal("20.0000"),
        )
        WarehouseInventory.objects.create(
            product=self.product, warehouse_code="NY", on_hand_qty=100,
        )

    def test_freight_quote_flow(self):
        order = create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.pk, "qty_ordered": 5}],
        )
        assert order.queue_status == "MGQ"
        transition_queue(order, "FQQ", "SHIPPING")
        transition_queue(order, "PTQ", "SHIPPING")
        transition_queue(order, "IVQ", "WAREHOUSE")
        assert order.queue_status == "IVQ"

    def test_sales_review_flow(self):
        order = create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.pk, "qty_ordered": 1}],
        )
        transition_queue(order, "SRQ", "ADMIN")
        transition_queue(order, "MGQ", "SALES_MGR")
        transition_queue(order, "PTQ", "ADMIN")
        assert order.queue_status == "PTQ"

    def test_problem_queue_flow(self):
        order = create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.pk, "qty_ordered": 1}],
        )
        transition_queue(order, "PTQ", "ADMIN")
        transition_queue(order, "PQ", "WAREHOUSE")
        transition_queue(order, "PTQ", "WAREHOUSE")
        transition_queue(order, "IVQ", "WAREHOUSE")
        assert order.queue_status == "IVQ"


@pytest.mark.django_db
class TestInventoryCommitmentIntegration:
    def setup_method(self):
        self.customer = Customer.objects.create(
            customer_number="IC-001", name="Commitment Test Corp",
            credit_code="A", credit_limit=Decimal("100000"),
            backorder_flag=True,
        )
        CustomerAnnex.objects.create(customer=self.customer)
        self.product = Product.objects.create(
            product_number="IC-P001", description="Commitment Product",
            list_price=Decimal("50.0000"), standard_cost=Decimal("20.0000"),
        )
        WarehouseInventory.objects.create(
            product=self.product, warehouse_code="NY", on_hand_qty=40,
        )

    def test_commitment_lifecycle(self):
        order = create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.pk, "qty_ordered": 15}],
        )
        assert InventoryCommitment.objects.filter(order_line__order=order).count() == 1
        c = InventoryCommitment.objects.get(order_line__order=order)
        assert c.committed_qty == 15
        assert c.backorder_qty == 0

        avail = get_availability(self.product, "NY")
        assert avail["NY"]["committed"] == 15
        assert avail["NY"]["available"] == 25

        transition_queue(order, "PTQ", "TEST")
        transition_queue(order, "IVQ", "TEST")

        assert InventoryCommitment.objects.filter(order_line__order=order).count() == 0
        avail = get_availability(self.product, "NY")
        assert avail["NY"]["committed"] == 0
        assert avail["NY"]["available"] == 40

    def test_backorder_split(self):
        order = create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.pk, "qty_ordered": 60}],
        )
        line = order.lines.first()
        assert line.qty_open == 40
        assert line.backorder_qty == 20

        c = InventoryCommitment.objects.get(order_line=line)
        assert c.committed_qty == 40
        assert c.backorder_qty == 20

    def test_multiple_orders_compete_for_stock(self):
        o1 = create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.pk, "qty_ordered": 30}],
        )
        o2 = create_order(
            customer=self.customer,
            lines=[{"product_id": self.product.pk, "qty_ordered": 25}],
        )
        assert o1.lines.first().qty_open == 30
        assert o1.lines.first().backorder_qty == 0
        assert o2.lines.first().qty_open == 10
        assert o2.lines.first().backorder_qty == 15
