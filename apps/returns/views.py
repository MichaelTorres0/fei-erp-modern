from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.invoicing.models import Invoice

from .models import RMA
from .serializers import RMASerializer
from .services import cancel_rma, create_rma, issue_credit_memo, receive_rma


class RMAViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        RMA.objects.select_related("customer", "invoice")
        .prefetch_related("lines__product")
    )
    serializer_class = RMASerializer
    filterset_fields = ["status", "customer", "reason"]
    search_fields = [
        "rma_number",
        "credit_memo_number",
        "invoice__invoice_number",
        "customer__customer_number",
        "customer__name",
    ]
    ordering_fields = ["rma_number", "issued_date", "credit_amount"]

    def create(self, request, *args, **kwargs):
        invoice_id = request.data.get("invoice_id")
        lines = request.data.get("lines") or []
        if not invoice_id:
            return Response({"error": "invoice_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not lines:
            return Response({"error": "at least one line is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invoice = Invoice.objects.get(pk=invoice_id)
        except Invoice.DoesNotExist:
            return Response({"error": "invoice not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            rma = create_rma(
                invoice=invoice,
                lines=lines,
                reason=request.data.get("reason", "OTHER"),
                restock_to_warehouse=request.data.get("restock_to_warehouse", "NY"),
                operator=request.data.get("operator", "api"),
                notes=request.data.get("notes", ""),
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(RMASerializer(rma).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        rma = self.get_object()
        try:
            rma = receive_rma(rma, operator=request.data.get("operator", "api"))
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RMASerializer(rma).data)

    @action(detail=True, methods=["post"], url_path="issue-credit")
    def issue_credit(self, request, pk=None):
        rma = self.get_object()
        try:
            rma = issue_credit_memo(rma, operator=request.data.get("operator", "api"))
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RMASerializer(rma).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        rma = self.get_object()
        try:
            rma = cancel_rma(
                rma,
                operator=request.data.get("operator", "api"),
                reason=request.data.get("reason", ""),
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RMASerializer(rma).data)
