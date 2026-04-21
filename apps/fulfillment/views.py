from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import PickTicket
from .serializers import PickTicketSerializer
from .services import mark_picked, mark_shipped


class PickTicketViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PickTicket.objects.select_related("order__customer").prefetch_related("lines__product")
    serializer_class = PickTicketSerializer
    filterset_fields = ["status", "warehouse_code", "is_backorder"]
    search_fields = ["ticket_number", "order__order_number", "tracking_number"]
    ordering_fields = ["ticket_number", "created_at", "shipped_at"]

    @action(detail=True, methods=["post"])
    def pick(self, request, pk=None):
        ticket = self.get_object()
        if ticket.status != "OPEN":
            return Response(
                {"error": f"Cannot pick ticket in {ticket.status} status"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        operator = request.data.get("operator", "system")
        line_picks = request.data.get("line_picks")
        if line_picks:
            line_picks = {int(k): int(v) for k, v in line_picks.items()}
        ticket = mark_picked(ticket, operator=operator, line_picks=line_picks or None)
        return Response(PickTicketSerializer(ticket).data)

    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        ticket = self.get_object()
        if ticket.status not in ("PICKED", "PACKED"):
            return Response(
                {"error": f"Cannot ship ticket in {ticket.status} status — must be PICKED or PACKED"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        tracking = request.data.get("tracking_number", "")
        operator = request.data.get("operator", "system")
        ticket = mark_shipped(ticket, tracking_number=tracking, operator=operator)
        return Response(PickTicketSerializer(ticket).data)
