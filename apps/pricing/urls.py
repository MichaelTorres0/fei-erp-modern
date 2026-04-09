from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.customers.models import Customer
from apps.products.models import Product
from .services import calculate_price


@api_view(["GET"])
def calculate_price_view(request):
    customer_id = request.query_params.get("customer")
    product_id = request.query_params.get("product")
    if not customer_id or not product_id:
        return Response({"error": "customer and product query params required"}, status=400)
    try:
        customer = Customer.objects.get(pk=customer_id)
        product = Product.objects.get(pk=product_id)
    except (Customer.DoesNotExist, Product.DoesNotExist):
        return Response({"error": "customer or product not found"}, status=404)
    result = calculate_price(customer, product)
    return Response({
        "gross_price": str(result.gross),
        "discount_1": str(result.discount_1),
        "discount_2": str(result.discount_2),
        "net_price": str(result.net),
        "source": result.source,
    })


urlpatterns = [
    path("calculate/", calculate_price_view, name="pricing-calculate"),
]
