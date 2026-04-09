from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet
from .lookups import pricing_lookup, customer_defaults_lookup

router = DefaultRouter()
router.register("", OrderViewSet, basename="order")

urlpatterns = [
    path("lookup/pricing/", pricing_lookup, name="order-pricing-lookup"),
    path("lookup/customer-defaults/", customer_defaults_lookup, name="order-customer-defaults-lookup"),
] + router.urls
