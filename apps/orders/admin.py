from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderLine, OrderAudit


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    readonly_fields = ["extension"]
    autocomplete_fields = ["product"]


class OrderAuditInline(admin.TabularInline):
    model = OrderAudit
    extra = 0
    readonly_fields = ["timestamp", "operator", "event_code", "notes"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


QUEUE_COLORS = {
    "OEQ": "#6c757d",  # gray
    "MGQ": "#28a745",  # green
    "CHQ": "#dc3545",  # red
    "PTQ": "#007bff",  # blue
    "IVQ": "#17a2b8",  # teal
}


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "customer",
        "order_date",
        "po_number",
        "colored_queue_status",
        "subtotal",
        "placed_by",
    ]
    list_filter = ["queue_status", "placed_by", "ship_via"]
    search_fields = ["order_number", "customer__name", "customer__customer_number", "po_number"]
    readonly_fields = ["entry_date", "created_at", "updated_at", "subtotal"]
    autocomplete_fields = ["customer"]
    date_hierarchy = "order_date"
    inlines = [OrderLineInline, OrderAuditInline]

    fieldsets = (
        ("Order Info", {
            "fields": (
                "order_number", "customer", "order_date", "required_date",
                "po_number", "placed_by", "email", "queue_status",
            )
        }),
        ("Ship To", {
            "fields": (
                "ship_to_line_1", "ship_to_line_2", "ship_to_city",
                "ship_to_state", "ship_to_zip", "ship_to_country",
                "is_drop_ship",
            )
        }),
        ("Terms & Shipping", {
            "fields": ("terms", "freight_terms", "ship_via", "shipping_cost")
        }),
        ("Sales", {
            "fields": (
                "salesman", "affiliation",
                "territory_1", "territory_2", "territory_3",
                "special_discounts", "special_instructions",
            )
        }),
        ("Totals", {
            "fields": ("subtotal",)
        }),
        ("Timestamps", {
            "fields": ("entry_date", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Queue Status")
    def colored_queue_status(self, obj):
        color = QUEUE_COLORS.get(obj.queue_status, "#000000")
        label = obj.get_queue_status_display()
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; '
            'border-radius:3px; font-weight:bold;">{}</span>',
            color,
            label,
        )
