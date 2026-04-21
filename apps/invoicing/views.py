from decimal import Decimal

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .aging import ar_aging_by_customer, ar_aging_totals
from .models import Invoice
from .serializers import InvoiceSerializer
from .services import record_payment


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Invoice.objects.select_related("customer", "order").prefetch_related("lines__product")
    serializer_class = InvoiceSerializer
    filterset_fields = ["status", "customer"]
    search_fields = ["invoice_number", "customer__name", "customer__customer_number", "po_number"]
    ordering_fields = ["invoice_number", "invoice_date", "total", "due_date"]

    @action(detail=True, methods=["post"])
    def payment(self, request, pk=None):
        invoice = self.get_object()
        amount = request.data.get("amount")
        if not amount:
            return Response({"error": "amount is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            amount_dec = Decimal(str(amount))
        except Exception:
            return Response({"error": "invalid amount"}, status=status.HTTP_400_BAD_REQUEST)
        if amount_dec <= 0:
            return Response({"error": "amount must be positive"}, status=status.HTTP_400_BAD_REQUEST)

        invoice = record_payment(invoice, amount_dec)
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=False, methods=["get"], url_path="aging")
    def aging(self, request):
        rows = ar_aging_by_customer()
        totals = ar_aging_totals()
        return Response({
            "totals": totals.as_dict(),
            "customers": [
                {
                    "customer_id": r.customer_id,
                    "customer_number": r.customer_number,
                    "customer_name": r.customer_name,
                    "invoice_count": r.invoice_count,
                    **r.buckets.as_dict(),
                }
                for r in rows
            ],
        })
