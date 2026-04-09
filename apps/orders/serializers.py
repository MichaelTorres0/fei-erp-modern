from rest_framework import serializers
from .models import Order, OrderLine, OrderAudit


class OrderLineSerializer(serializers.ModelSerializer):
    product_number = serializers.CharField(
        source="product.product_number", read_only=True
    )

    class Meta:
        model = OrderLine
        fields = [
            "id", "line_number", "product", "product_number",
            "unit_price", "discount_1", "discount_2", "net_price",
            "cost", "qty_ordered", "qty_open", "qty_shipped",
            "backorder_qty", "warehouse_code", "extension",
        ]


class OrderAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderAudit
        fields = ["id", "timestamp", "operator", "event_code", "notes"]


class OrderSerializer(serializers.ModelSerializer):
    lines = OrderLineSerializer(many=True, read_only=True)
    audit_trail = OrderAuditSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = Order
        fields = "__all__"


class OrderCreateSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    placed_by = serializers.CharField(max_length=50)
    po_number = serializers.CharField(max_length=100, required=False, default="")
    ship_via = serializers.CharField(max_length=50, required=False, default="")
    lines = serializers.ListField(
        child=serializers.DictField(), min_length=1
    )
