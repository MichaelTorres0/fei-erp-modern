import pytest
from apps.orders.tests.factories import OrderFactory, OrderLineFactory, OrderAuditFactory

pytestmark = pytest.mark.django_db


class TestOrder:
    def test_create_order(self):
        order = OrderFactory(order_number="ORD-000001")
        assert order.order_number == "ORD-000001"
        assert order.queue_status == "OEQ"

    def test_order_str(self):
        order = OrderFactory(order_number="ORD-000001")
        assert "ORD-000001" in str(order)

    def test_order_number_unique(self):
        OrderFactory(order_number="ORD-000001")
        with pytest.raises(Exception):
            OrderFactory(order_number="ORD-000001")


class TestOrderLine:
    def test_create_order_line(self):
        line = OrderLineFactory(qty_ordered=10, net_price=25.00)
        assert line.qty_ordered == 10
        assert line.net_price == 25.00

    def test_order_lines_relationship(self):
        order = OrderFactory()
        OrderLineFactory(order=order, line_number=1)
        OrderLineFactory(order=order, line_number=2)
        assert order.lines.count() == 2

    def test_unique_order_line_number(self):
        order = OrderFactory()
        OrderLineFactory(order=order, line_number=1)
        with pytest.raises(Exception):
            OrderLineFactory(order=order, line_number=1)


class TestOrderAudit:
    def test_create_audit_entry(self):
        audit = OrderAuditFactory(event_code="MGQ", operator="admin")
        assert audit.event_code == "MGQ"
        assert audit.operator == "admin"

    def test_audit_trail(self):
        order = OrderFactory()
        OrderAuditFactory(order=order, event_code="OEQ")
        OrderAuditFactory(order=order, event_code="MGQ")
        assert order.audit_trail.count() == 2
