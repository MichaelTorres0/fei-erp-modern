from rest_framework import serializers

from .models import Invoice, InvoiceLine


class InvoiceLineSerializer(serializers.ModelSerializer):
    product_number = serializers.CharField(source="product.product_number", read_only=True)

    class Meta:
        model = InvoiceLine
        fields = [
            "id", "line_number", "product", "product_number", "description",
            "qty_shipped", "unit_price", "net_price", "extension",
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)
    customer_number = serializers.CharField(source="customer.customer_number", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    amount_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = "__all__"
