import pytest
from django.urls import reverse
from apps.customers.tests.factories import CustomerFactory

pytestmark = pytest.mark.django_db


class TestCustomerAPI:
    def test_list_customers(self, api_client):
        CustomerFactory.create_batch(3)
        url = reverse("customer-list")
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] == 3

    def test_retrieve_customer(self, api_client):
        customer = CustomerFactory(customer_number="F10001", name="Acme Corp")
        url = reverse("customer-detail", args=[customer.pk])
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["customer_number"] == "F10001"
        assert response.data["name"] == "Acme Corp"

    def test_create_customer(self, api_client):
        url = reverse("customer-list")
        data = {
            "customer_number": "F20001",
            "name": "Test Customer",
            "city": "New York",
            "state": "NY",
            "zip_code": "10001",
            "terms_code": "N30",
            "credit_limit": "5000.00",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == 201
        assert response.data["customer_number"] == "F20001"

    def test_update_customer(self, api_client):
        customer = CustomerFactory(name="Old Name")
        url = reverse("customer-detail", args=[customer.pk])
        response = api_client.patch(url, {"name": "New Name"}, format="json")
        assert response.status_code == 200
        assert response.data["name"] == "New Name"

    def test_search_customers(self, api_client):
        CustomerFactory(name="Acme Corp")
        CustomerFactory(name="Beta Inc")
        url = reverse("customer-list")
        response = api_client.get(url, {"search": "Acme"})
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_filter_by_credit_code(self, api_client):
        CustomerFactory(credit_code="A")
        CustomerFactory(credit_code="D")
        CustomerFactory(credit_code="A")
        url = reverse("customer-list")
        response = api_client.get(url, {"credit_code": "A"})
        assert response.status_code == 200
        assert response.data["count"] == 2
