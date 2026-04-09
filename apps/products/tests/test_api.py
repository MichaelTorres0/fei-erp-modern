import pytest
from django.urls import reverse
from apps.products.tests.factories import (
    ProductFactory,
    WarehouseInventoryFactory,
    KitComponentFactory,
)

pytestmark = pytest.mark.django_db


class TestProductAPI:
    def test_list_products(self, api_client):
        ProductFactory.create_batch(3)
        url = reverse("product-list")
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] == 3

    def test_retrieve_product(self, api_client):
        product = ProductFactory(product_number="ABC-100")
        url = reverse("product-detail", args=[product.pk])
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["product_number"] == "ABC-100"

    def test_product_inventory_endpoint(self, api_client):
        product = ProductFactory()
        WarehouseInventoryFactory(product=product, warehouse_code="NY", on_hand_qty=100)
        WarehouseInventoryFactory(product=product, warehouse_code="FL", on_hand_qty=50)
        url = reverse("product-inventory", args=[product.pk])
        response = api_client.get(url)
        assert response.status_code == 200
        assert "NY" in response.data
        assert response.data["NY"]["on_hand"] == 100

    def test_product_kit_components_endpoint(self, api_client):
        kit = ProductFactory(is_kit=True)
        comp = ProductFactory(product_number="COMP-A")
        KitComponentFactory(parent_product=kit, component_product=comp, quantity_per_kit=2)
        url = reverse("product-kit-components", args=[kit.pk])
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["component_product_number"] == "COMP-A"
        assert response.data[0]["quantity_per_kit"] == "2.00"

    def test_filter_by_category(self, api_client):
        ProductFactory(category="WIDGETS")
        ProductFactory(category="GADGETS")
        url = reverse("product-list")
        response = api_client.get(url, {"category": "WIDGETS"})
        assert response.data["count"] == 1
