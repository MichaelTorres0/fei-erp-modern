from rest_framework import serializers

from .models import RMA, RMALine


class RMALineSerializer(serializers.ModelSerializer):
    product_number = serializers.CharField(source="product.product_number", read_only=True)
    product_description = serializers.CharField(source="product.description", read_only=True)

    class Meta:
        model = RMALine
        fields = [
            "id",
            "line_number",
            "invoice_line",
            "product",
            "product_number",
            "product_description",
            "qty_returned",
            "qty_received",
            "unit_price",
            "restock",
            "extension",
        ]


class RMASerializer(serializers.ModelSerializer):
    customer_number = serializers.CharField(source="customer.customer_number", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True)
    lines = RMALineSerializer(many=True, read_only=True)

    class Meta:
        model = RMA
        fields = [
            "id",
            "rma_number",
            "invoice",
            "invoice_number",
            "customer",
            "customer_number",
            "customer_name",
            "reason",
            "status",
            "issued_date",
            "received_date",
            "credited_date",
            "restock_to_warehouse",
            "credit_memo_number",
            "credit_amount",
            "notes",
            "created_by",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
