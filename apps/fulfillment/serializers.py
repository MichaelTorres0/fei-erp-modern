from rest_framework import serializers

from .models import PickTicket, PickTicketLine


class PickTicketLineSerializer(serializers.ModelSerializer):
    product_number = serializers.CharField(source="product.product_number", read_only=True)

    class Meta:
        model = PickTicketLine
        fields = [
            "id", "line_number", "product", "product_number",
            "warehouse_code", "qty_ordered", "qty_picked",
        ]


class PickTicketSerializer(serializers.ModelSerializer):
    lines = PickTicketLineSerializer(many=True, read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    customer_name = serializers.CharField(source="order.customer.name", read_only=True)

    class Meta:
        model = PickTicket
        fields = "__all__"
