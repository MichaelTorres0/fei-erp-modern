import pytest
from decimal import Decimal
from apps.products.tests.factories import (
    ProductFactory,
    KitComponentFactory,
    WarehouseInventoryFactory,
)
from apps.products.services import get_availability, get_kit_availability

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
