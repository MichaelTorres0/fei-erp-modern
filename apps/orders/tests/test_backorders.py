import pytest
from decimal import Decimal
from apps.customers.tests.factories import CustomerFactory
from apps.products.tests.factories import ProductFactory, WarehouseInventoryFactory
from apps.orders.services import create_order
from apps.products.models import InventoryCommitment

pytestmark = pytest.mark.django_db


class TestBackorderRouting:
    def test_partial_stock_with_backorder_flag(self):
        """Customer allows backorders + partial stock -> backorder lines."""
        customer = CustomerFactory(credit_code="A", backorder_flag=True)
        product = ProductFactory(list_price=25.00)
        WarehouseInventoryFactory(product=product, warehouse_code="NY", on_hand_qty=5)
        lines = [{"product_id": product.pk, "qty_ordered": 20, "warehouse_code": "NY"}]
        order = create_order(customer=customer, lines=lines, placed_by="TEST")
        line = order.lines.first()
        assert line.qty_open == 5
        assert line.backorder_qty == 15
        assert order.audit_trail.filter(notes__icontains="backorder").exists()

    def test_no_stock_with_backorder_flag(self):
        """No stock + backorders allowed -> full backorder."""
        customer = CustomerFactory(credit_code="A", backorder_flag=True)
        product = ProductFactory(list_price=25.00)
        WarehouseInventoryFactory(product=product, warehouse_code="NY", on_hand_qty=0)
        lines = [{"product_id": product.pk, "qty_ordered": 10, "warehouse_code": "NY"}]
        order = create_order(customer=customer, lines=lines, placed_by="TEST")
        line = order.lines.first()
        assert line.qty_open == 0
        assert line.backorder_qty == 10

    def test_partial_stock_without_backorder_flag(self):
        """Customer doesn't allow backorders -> no backorder qty."""
        customer = CustomerFactory(credit_code="A", backorder_flag=False)
        product = ProductFactory(list_price=25.00)
        WarehouseInventoryFactory(product=product, warehouse_code="NY", on_hand_qty=5)
        lines = [{"product_id": product.pk, "qty_ordered": 20, "warehouse_code": "NY"}]
        order = create_order(customer=customer, lines=lines, placed_by="TEST")
        line = order.lines.first()
        assert line.qty_open == 5
        assert line.backorder_qty == 0

    def test_sufficient_stock_no_backorder(self):
        """Enough stock -> no backorder."""
        customer = CustomerFactory(credit_code="A", backorder_flag=True)
        product = ProductFactory(list_price=25.00)
        WarehouseInventoryFactory(product=product, warehouse_code="NY", on_hand_qty=100)
        lines = [{"product_id": product.pk, "qty_ordered": 20, "warehouse_code": "NY"}]
        order = create_order(customer=customer, lines=lines, placed_by="TEST")
        line = order.lines.first()
        assert line.qty_open == 20
        assert line.backorder_qty == 0

    def test_multi_line_mixed_backorder(self):
        """One line has stock, another doesn't."""
        customer = CustomerFactory(credit_code="A", backorder_flag=True)
        prod_a = ProductFactory(list_price=25.00)
        prod_b = ProductFactory(list_price=50.00)
        WarehouseInventoryFactory(product=prod_a, warehouse_code="NY", on_hand_qty=100)
        WarehouseInventoryFactory(product=prod_b, warehouse_code="NY", on_hand_qty=3)
        lines = [
            {"product_id": prod_a.pk, "qty_ordered": 10, "warehouse_code": "NY"},
            {"product_id": prod_b.pk, "qty_ordered": 10, "warehouse_code": "NY"},
        ]
        order = create_order(customer=customer, lines=lines, placed_by="TEST")
        line_a = order.lines.get(product=prod_a)
        line_b = order.lines.get(product=prod_b)
        assert line_a.qty_open == 10
        assert line_a.backorder_qty == 0
        assert line_b.qty_open == 3
        assert line_b.backorder_qty == 7
