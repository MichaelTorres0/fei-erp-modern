from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.customers.models import Customer
from .models import Order
from .serializers import OrderSerializer, OrderCreateSerializer
from .services import create_order, transition_queue


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related("customer").prefetch_related(
        "lines__product", "audit_trail"
    )
    serializer_class = OrderSerializer
    filterset_fields = ["queue_status", "placed_by", "ship_via"]
    search_fields = ["order_number", "customer__name", "po_number"]
    ordering_fields = ["order_number", "order_date", "subtotal", "created_at"]

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        customer = Customer.objects.get(pk=data["customer_id"])
        order = create_order(
            customer=customer,
            lines=data["lines"],
            placed_by=data["placed_by"],
            po_number=data.get("po_number", ""),
            ship_via=data.get("ship_via", ""),
        )

        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get("new_status")
        operator = request.data.get("operator", "system")

        if not new_status:
            return Response(
                {"error": "new_status is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = transition_queue(order, new_status, operator)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(OrderSerializer(order).data)
