from django.contrib import admin
from .models import CustomerSpecialPrice, CustomerPriceHistory


@admin.register(CustomerSpecialPrice)
class CustomerSpecialPriceAdmin(admin.ModelAdmin):
    list_display = ["customer", "product", "gross_price", "discount_1", "net_price"]
    search_fields = [
        "customer__customer_number",
        "customer__name",
        "product__product_number",
    ]
    autocomplete_fields = ["customer", "product"]


@admin.register(CustomerPriceHistory)
class CustomerPriceHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "customer",
        "product",
        "last_net_price",
        "last_order_date",
        "quote_net_price",
        "quote_date",
    ]
    search_fields = [
        "customer__customer_number",
        "product__product_number",
    ]
