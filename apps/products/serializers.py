from rest_framework import serializers
from .models import Product, ProductAnnex, KitComponent, WarehouseInventory


class ProductAnnexSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAnnex
        exclude = ["id", "product"]


class WarehouseInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseInventory
        exclude = ["id"]


class KitComponentSerializer(serializers.ModelSerializer):
    component_product_number = serializers.CharField(
        source="component_product.product_number", read_only=True
    )
    component_description = serializers.CharField(
        source="component_product.description", read_only=True
    )

    class Meta:
        model = KitComponent
        fields = [
            "id",
            "component_product",
            "component_product_number",
            "component_description",
            "quantity_per_kit",
        ]


class ProductSerializer(serializers.ModelSerializer):
    annex = ProductAnnexSerializer(read_only=True)

    class Meta:
        model = Product
        fields = "__all__"
