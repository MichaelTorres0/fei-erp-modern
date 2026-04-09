import pytest
from django.urls import reverse
from apps.customers.tests.factories import CustomerFactory
from apps.products.tests.factories import ProductFactory
from apps.pricing.tests.factories import CustomerSpecialPriceFactory

pytestmark = pytest.mark.django_db


class TestPricingLookup:
    def test_returns_base_price(self, api_client):
        customer = CustomerFactory()
        product = ProductFactory(list_price=50.00, standard_cost=20.00)
        url = reverse("order-pricing-lookup")
        response = api_client.get(url, {"customer_id": customer.pk, "product_id": product.pk})
        assert response.status_code == 200
        data = response.json()
        assert data["unit_price"] == "50.0000"
        assert data["net_price"] == "50.0000"
        assert data["cost"] == "20.0000"
        assert data["source"] == "base_product"

    def test_returns_special_price(self, api_client):
        customer = CustomerFactory()
        product = ProductFactory(list_price=50.00, standard_cost=20.00)
        CustomerSpecialPriceFactory(
            customer=customer, product=product,
            gross_price=35.00, discount_1=10, net_price=31.50,
        )
        url = reverse("order-pricing-lookup")
        response = api_client.get(url, {"customer_id": customer.pk, "product_id": product.pk})
        assert response.status_code == 200
        data = response.json()
        assert data["unit_price"] == "35.0000"
        assert data["net_price"] == "31.5000"
        assert data["source"] == "customer_special"

    def test_missing_params_returns_400(self, api_client):
        url = reverse("order-pricing-lookup")
        response = api_client.get(url)
        assert response.status_code == 400


class TestCustomerDefaultsLookup:
    def test_returns_customer_defaults(self, api_client):
        customer = CustomerFactory(
            terms_code="N30", salesman="JSmith",
            affiliation="DIST", credit_code="A",
        )
        url = reverse("order-customer-defaults-lookup")
        response = api_client.get(url, {"customer_id": customer.pk})
        assert response.status_code == 200
        data = response.json()
        assert data["terms_code"] == "N30"
        assert data["salesman"] == "JSmith"
        assert data["affiliation"] == "DIST"
        assert data["credit_code"] == "A"

    def test_missing_customer_returns_400(self, api_client):
        url = reverse("order-customer-defaults-lookup")
        response = api_client.get(url)
        assert response.status_code == 400
