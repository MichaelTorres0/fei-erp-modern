from django.contrib import admin
from .models import Customer, CustomerAnnex


class CustomerAnnexInline(admin.StackedInline):
    model = CustomerAnnex
    can_delete = False
    verbose_name = "Extended Attributes"
    verbose_name_plural = "Extended Attributes"


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        "customer_number",
        "name",
        "city",
        "state",
        "credit_code",
        "ar_balance",
        "credit_limit",
        "affiliation",
        "company_code",
        "price_level",
        "is_active",
    ]
    list_filter = ["credit_code", "state", "affiliation", "is_active"]
    search_fields = ["customer_number", "name", "city", "phone", "email"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [CustomerAnnexInline]

    fieldsets = (
        ("Identity", {
            "fields": ("customer_number", "name", "attention", "email", "phone", "fax")
        }),
        ("Address", {
            "fields": ("address_line_1", "address_line_2", "city", "state", "zip_code", "country")
        }),
        ("Financial", {
            "fields": (
                "terms_code", "credit_code", "credit_limit",
                "ar_balance", "open_order_amount", "over_90_balance",
                "ytd_sales", "last_payment_date", "last_payment_amount",
                "company_code", "price_level",
            )
        }),
        ("Sales & Shipping", {
            "fields": (
                "salesman", "affiliation", "freight_terms", "default_ship_via",
                "special_discounts", "resale_number", "backorder_flag",
                "territory_1", "territory_2", "territory_3",
            )
        }),
        ("Status", {
            "fields": ("is_active", "created_at", "updated_at")
        }),
    )
