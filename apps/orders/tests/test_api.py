import pytest
from django.urls import reverse
from apps.customers.tests.factories import CustomerFactory
from apps.products.tests.factories import ProductFactory
from apps.orders.tests.factories import OrderFactory, OrderLineFactory

pytestmark = pytest.mark.django_db


class TestOrderAPI:
    def test_list_orders(self, api_client):
        OrderFactory.create_batch(3)
        url = reverse("order-list")
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] == 3

    def test_retrieve_order_with_lines(self, api_client):
        order = OrderFactory()
        OrderLineFactory(order=order, line_number=1)
        OrderLineFactory(order=order, line_number=2)
        url = reverse("order-detail", args=[order.pk])
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data["lines"]) == 2

    def test_create_order_via_api(self, api_client):
        customer = CustomerFactory(credit_code="A")
        product = ProductFactory(list_price=25.00)
        url = reverse("order-list")
        data = {
            "customer_id": customer.pk,
            "placed_by": "API_TEST",
            "lines": [
                {"product_id": product.pk, "qty_ordered": 3, "warehouse_code": "NY"}
            ],
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == 201
        assert response.data["queue_status"] == "MGQ"
        assert len(response.data["lines"]) == 1

    def test_filter_by_queue_status(self, api_client):
        OrderFactory(queue_status="MGQ")
        OrderFactory(queue_status="CHQ")
        OrderFactory(queue_status="MGQ")
        url = reverse("order-list")
        response = api_client.get(url, {"queue_status": "MGQ"})
        assert response.data["count"] == 2

    def test_transition_queue(self, api_client):
        order = OrderFactory(queue_status="MGQ")
        url = reverse("order-transition", args=[order.pk])
        response = api_client.post(
            url, {"new_status": "PTQ", "operator": "admin"}, format="json"
        )
        assert response.status_code == 200
        assert response.data["queue_status"] == "PTQ"

    def test_invalid_transition_returns_400(self, api_client):
        order = OrderFactory(queue_status="OEQ")
        url = reverse("order-transition", args=[order.pk])
        response = api_client.post(
            url, {"new_status": "IVQ", "operator": "admin"}, format="json"
        )
        assert response.status_code == 400
