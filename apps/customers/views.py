from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.select_related("annex").filter(is_active=True)
    serializer_class = CustomerSerializer
    filterset_fields = ["credit_code", "state", "affiliation", "is_active"]
    search_fields = ["customer_number", "name", "city", "phone", "email"]
    ordering_fields = ["customer_number", "name", "city", "ar_balance"]
