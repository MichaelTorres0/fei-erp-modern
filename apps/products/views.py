from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Product
from .serializers import ProductSerializer, KitComponentSerializer
from .services import get_availability


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("annex").filter(is_active=True)
    serializer_class = ProductSerializer
    filterset_fields = ["category", "is_drop_ship", "is_kit", "is_obsolete"]
    search_fields = ["product_number", "sku", "description"]
    ordering_fields = ["product_number", "list_price", "dealer_price"]

    @action(detail=True, methods=["get"])
    def inventory(self, request, pk=None):
        product = self.get_object()
        warehouse_code = request.query_params.get("warehouse")
        availability = get_availability(product, warehouse_code)
        return Response(availability)

    @action(detail=True, methods=["get"], url_path="kit-components")
    def kit_components(self, request, pk=None):
        product = self.get_object()
        components = product.components.select_related("component_product").all()
        serializer = KitComponentSerializer(components, many=True)
        return Response(serializer.data)
