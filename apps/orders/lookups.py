from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.customers.models import Customer
from apps.products.models import Product
from apps.pricing.services import calculate_price


@require_GET
def pricing_lookup(request):
    """Return pricing for a customer+product combination."""
    customer_id = request.GET.get("customer_id")
    product_id = request.GET.get("product_id")

    if not customer_id or not product_id:
        return JsonResponse({"error": "customer_id and product_id required"}, status=400)

    try:
        customer = Customer.objects.get(pk=customer_id)
        product = Product.objects.get(pk=product_id)
    except (Customer.DoesNotExist, Product.DoesNotExist):
        return JsonResponse({"error": "Not found"}, status=404)

    result = calculate_price(customer, product)

    return JsonResponse({
        "unit_price": str(result.gross),
        "discount_1": str(result.discount_1),
        "discount_2": str(result.discount_2),
        "net_price": str(result.net),
        "cost": str(product.standard_cost),
        "source": result.source,
    })


@require_GET
def customer_defaults_lookup(request):
    """Return customer defaults for auto-populating order header."""
    customer_id = request.GET.get("customer_id")

    if not customer_id:
        return JsonResponse({"error": "customer_id required"}, status=400)

    try:
        customer = Customer.objects.get(pk=customer_id)
    except Customer.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    return JsonResponse({
        "terms_code": customer.terms_code,
        "freight_terms": customer.freight_terms,
        "salesman": customer.salesman,
        "affiliation": customer.affiliation,
        "default_ship_via": customer.default_ship_via,
        "territory_1": customer.territory_1,
        "territory_2": customer.territory_2,
        "territory_3": customer.territory_3,
        "email": customer.email,
        "credit_code": customer.credit_code,
        "credit_limit": str(customer.credit_limit),
        "ar_balance": str(customer.ar_balance),
    })
