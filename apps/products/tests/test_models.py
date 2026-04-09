import pytest
from apps.products.tests.factories import (
    ProductFactory,
    ProductAnnexFactory,
    KitComponentFactory,
    WarehouseInventoryFactory,
)

pytestmark = pytest.mark.django_db


class TestProduct:
    def test_create_product(self):
        product = ProductFactory(product_number="ABC-100", description="Test Widget")
        assert product.product_number == "ABC-100"
        assert product.is_active is True
        assert product.is_kit is False

    def test_product_str(self):
        product = ProductFactory(product_number="ABC-100", description="Test Widget")
        assert str(product) == "ABC-100 - Test Widget"

    def test_product_number_unique(self):
        ProductFactory(product_number="ABC-100")
        with pytest.raises(Exception):
            ProductFactory(product_number="ABC-100")


class TestKitComponent:
    def test_create_kit(self):
        parent = ProductFactory(product_number="KIT-001", is_kit=True)
        comp_a = ProductFactory(product_number="COMP-A")
        comp_b = ProductFactory(product_number="COMP-B")
        KitComponentFactory(parent_product=parent, component_product=comp_a, quantity_per_kit=2)
        KitComponentFactory(parent_product=parent, component_product=comp_b, quantity_per_kit=1)
        assert parent.components.count() == 2

    def test_component_used_in_kits(self):
        comp = ProductFactory(product_number="COMP-A")
        kit1 = ProductFactory(product_number="KIT-001", is_kit=True)
        kit2 = ProductFactory(product_number="KIT-002", is_kit=True)
        KitComponentFactory(parent_product=kit1, component_product=comp)
        KitComponentFactory(parent_product=kit2, component_product=comp)
        assert comp.used_in_kits.count() == 2


class TestWarehouseInventory:
    def test_create_inventory(self):
        inv = WarehouseInventoryFactory(
            product__product_number="ABC-100",
            warehouse_code="NY",
            on_hand_qty=50,
        )
        assert inv.product.product_number == "ABC-100"
        assert inv.warehouse_code == "NY"
        assert inv.on_hand_qty == 50

    def test_unique_product_warehouse(self):
        product = ProductFactory()
        WarehouseInventoryFactory(product=product, warehouse_code="NY")
        with pytest.raises(Exception):
            WarehouseInventoryFactory(product=product, warehouse_code="NY")

    def test_multiple_warehouses(self):
        product = ProductFactory()
        WarehouseInventoryFactory(product=product, warehouse_code="NY", on_hand_qty=50)
        WarehouseInventoryFactory(product=product, warehouse_code="FL", on_hand_qty=30)
        assert product.warehouse_inventory.count() == 2
