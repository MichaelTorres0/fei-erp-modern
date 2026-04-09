from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.select_related("annex").filter(is_active=True)
    serializer_class = CustomerSerializer
    filterset_fields = ["credit_code", "state", "affiliation", "is_active"]
    search_fields = ["customer_number", "name", "city", "phone", "email"]
    ordering_fields = ["customer_number", "name", "city", "ar_balance"]

    @action(detail=True, methods=["get"])
    def orders(self, request, pk=None):
        customer = self.get_object()
        from apps.orders.models import Order
        from apps.orders.serializers import OrderSerializer
        orders = Order.objects.filter(customer=customer).select_related("customer").prefetch_related("lines__product", "audit_trail")
        page = self.paginate_queryset(orders)
        if page is not None:
            serializer = OrderSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
