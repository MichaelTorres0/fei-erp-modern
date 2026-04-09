from rest_framework import serializers
from .models import Customer, CustomerAnnex


class CustomerAnnexSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAnnex
        exclude = ["id", "customer"]


class CustomerSerializer(serializers.ModelSerializer):
    annex = CustomerAnnexSerializer(read_only=True)
    credit_exposure = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    available_credit = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Customer
        fields = "__all__"
