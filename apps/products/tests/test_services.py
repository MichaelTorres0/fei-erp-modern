import pytest
from decimal import Decimal
from apps.products.tests.factories import (
    ProductFactory,
    KitComponentFactory,
    WarehouseInventoryFactory,
)
from apps.products.services import get_availability, get_kit_availability, allocate_inventory, release_commitments
from apps.products.models import InventoryCommitment
from apps.orders.tests.factories import OrderFactory, OrderLineFactory

pytestmark = pytest.mark.django_db


class TestGetAvailability:
    def test_simple_product_no_orders(self):
        inv = WarehouseInventoryFactory(on_hand_qty=100, warehouse_code="NY")
        result = get_availability(inv.product)
        assert result["NY"]["on_hand"] == 100
        assert result["NY"]["committed"] == 0
        assert result["NY"]["available"] == 100

    def test_specific_warehouse(self):
        product = ProductFactory()
        WarehouseInventoryFactory(product=product, warehouse_code="NY", on_hand_qty=100)
        WarehouseInventoryFactory(product=product, warehouse_code="FL", on_hand_qty=50)
        result = get_availability(product, warehouse_code="NY")
        assert "NY" in result
        assert "FL" not in result

    def test_multiple_warehouses(self):
        product = ProductFactory()
        WarehouseInventoryFactory(product=product, warehouse_code="NY", on_hand_qty=100)
        WarehouseInventoryFactory(product=product, warehouse_code="FL", on_hand_qty=50)
        result = get_availability(product)
        assert result["NY"]["on_hand"] == 100
        assert result["FL"]["on_hand"] == 50


class TestGetKitAvailability:
    def test_kit_limited_by_min_component(self):
        kit = ProductFactory(is_kit=True)
        comp_a = ProductFactory()
        comp_b = ProductFactory()
        KitComponentFactory(parent_product=kit, component_product=comp_a, quantity_per_kit=2)
        KitComponentFactory(parent_product=kit, component_product=comp_b, quantity_per_kit=1)
        WarehouseInventoryFactory(product=comp_a, warehouse_code="NY", on_hand_qty=20)
        WarehouseInventoryFactory(product=comp_b, warehouse_code="NY", on_hand_qty=5)
        result = get_kit_availability(kit, "NY")
        assert result == 5

    def test_kit_no_inventory(self):
        kit = ProductFactory(is_kit=True)
        comp = ProductFactory()
        KitComponentFactory(parent_product=kit, component_product=comp, quantity_per_kit=1)
        result = get_kit_availability(kit, "NY")
        assert result == 0

    def test_non_kit_returns_none(self):
        product = ProductFactory(is_kit=False)
        result = get_kit_availability(product, "NY")
        assert result is None


class TestGetKitAvailabilityNested:
    def test_nested_kit(self):
        """A kit containing another kit."""
        # Inner kit: 2x comp_a per kit
        inner_kit = ProductFactory(product_number="INNER-KIT", is_kit=True)
        comp_a = ProductFactory(product_number="COMP-A")
        KitComponentFactory(parent_product=inner_kit, component_product=comp_a, quantity_per_kit=2)
        WarehouseInventoryFactory(product=comp_a, warehouse_code="NY", on_hand_qty=20)
        # Inner kit availability: 20/2 = 10

        # Outer kit: 1x inner_kit + 1x comp_b
        outer_kit = ProductFactory(product_number="OUTER-KIT", is_kit=True)
        comp_b = ProductFactory(product_number="COMP-B")
        KitComponentFactory(parent_product=outer_kit, component_product=inner_kit, quantity_per_kit=1)
        KitComponentFactory(parent_product=outer_kit, component_product=comp_b, quantity_per_kit=1)
        WarehouseInventoryFactory(product=comp_b, warehouse_code="NY", on_hand_qty=5)

        # Outer kit limited by min(inner_kit=10, comp_b=5) = 5
        result = get_kit_availability(outer_kit, "NY")
        assert result == 5

    def test_circular_reference_returns_zero(self):
        """Circular kit references don't infinite loop."""
        kit_a = ProductFactory(product_number="CIRC-A", is_kit=True)
        kit_b = ProductFactory(product_number="CIRC-B", is_kit=True)
        KitComponentFactory(parent_product=kit_a, component_product=kit_b, quantity_per_kit=1)
        KitComponentFactory(parent_product=kit_b, component_product=kit_a, quantity_per_kit=1)

        result = get_kit_availability(kit_a, "NY")
        assert result == 0


class TestAllocateInventory:
    def test_full_allocation(self):
        product = ProductFactory()
        WarehouseInventoryFactory(product=product, warehouse_code="NY", on_hand_qty=100)
        order = OrderFactory()
        line = OrderLineFactory(order=order, product=product, qty_ordered=20, qty_open=20, warehouse_code="NY")
        result = allocate_inventory(line)
        assert result.committed_qty == 20
        assert result.backorder_qty == 0
        commitment = InventoryCommitment.objects.get(order_line=line)
        assert commitment.committed_qty == 20

    def test_partial_allocation(self):
        product = ProductFactory()
        WarehouseInventoryFactory(product=product, warehouse_code="NY", on_hand_qty=15)
        order = OrderFactory()
        line = OrderLineFactory(order=order, product=product, qty_ordered=25, qty_open=25, warehouse_code="NY")
        result = allocate_inventory(line)
        assert result.committed_qty == 15
        assert result.backorder_qty == 10
        line.refresh_from_db()
        assert line.qty_open == 15
        assert line.backorder_qty == 10

    def test_zero_stock_full_backorder(self):
        product = ProductFactory()
        WarehouseInventoryFactory(product=product, warehouse_code="NY", on_hand_qty=0)
        order = OrderFactory()
        line = OrderLineFactory(order=order, product=product, qty_ordered=10, qty_open=10, warehouse_code="NY")
        result = allocate_inventory(line)
        assert result.committed_qty == 0
        assert result.backorder_qty == 10

    def test_no_warehouse_record_full_backorder(self):
        product = ProductFactory()
        order = OrderFactory()
        line = OrderLineFactory(order=order, product=product, qty_ordered=5, qty_open=5, warehouse_code="NY")
        result = allocate_inventory(line)
        assert result.committed_qty == 0
        assert result.backorder_qty == 5

    def test_considers_existing_commitments(self):
        product = ProductFactory()
        WarehouseInventoryFactory(product=product, warehouse_code="NY", on_hand_qty=50)
        existing_order = OrderFactory()
        existing_line = OrderLineFactory(order=existing_order, product=product, qty_ordered=30, qty_open=30, warehouse_code="NY")
        allocate_inventory(existing_line)

        new_order = OrderFactory()
        new_line = OrderLineFactory(order=new_order, product=product, qty_ordered=25, qty_open=25, warehouse_code="NY")
        result = allocate_inventory(new_line)
        assert result.committed_qty == 20
        assert result.backorder_qty == 5


class TestReleaseCommitments:
    def test_release_clears_commitments(self):
        product = ProductFactory()
        WarehouseInventoryFactory(product=product, warehouse_code="NY", on_hand_qty=100)
        order = OrderFactory()
        line = OrderLineFactory(order=order, product=product, qty_ordered=10, qty_open=10, warehouse_code="NY")
        allocate_inventory(line)
        assert InventoryCommitment.objects.filter(order_line=line).count() == 1
        release_commitments(order)
        assert InventoryCommitment.objects.filter(order_line=line).count() == 0

    def test_release_frees_inventory(self):
        product = ProductFactory()
        WarehouseInventoryFactory(product=product, warehouse_code="NY", on_hand_qty=30)
        order1 = OrderFactory()
        line1 = OrderLineFactory(order=order1, product=product, qty_ordered=30, qty_open=30, warehouse_code="NY")
        allocate_inventory(line1)

        order2 = OrderFactory()
        line2 = OrderLineFactory(order=order2, product=product, qty_ordered=20, qty_open=20, warehouse_code="NY")
        result = allocate_inventory(line2)
        assert result.committed_qty == 0
        assert result.backorder_qty == 20

        release_commitments(order1)
        InventoryCommitment.objects.filter(order_line=line2).delete()
        result2 = allocate_inventory(line2)
        assert result2.committed_qty == 20
        assert result2.backorder_qty == 0
