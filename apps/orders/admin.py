from decimal import Decimal

from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderLine, OrderAudit
from apps.pricing.services import calculate_price


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 1
    autocomplete_fields = ["product"]
    readonly_fields = ["extension"]

    def get_readonly_fields(self, request, obj=None):
        """Extension is always read-only (calculated)."""
        return ["extension"]


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

    class Media:
        js = ("orders/js/order_admin.js",)

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

    def save_formset(self, request, form, formset, change):
        """
        Auto-fill pricing on order lines if not already set.
        This is the backend fallback for the JS auto-fill.
        """
        instances = formset.save(commit=False)

        order = form.instance
        customer = order.customer

        subtotal = Decimal("0")
        for instance in instances:
            if isinstance(instance, OrderLine):
                # Auto-fill pricing if unit_price is 0 (not yet set)
                if not instance.unit_price or instance.unit_price == 0:
                    price_result = calculate_price(customer, instance.product)
                    instance.unit_price = price_result.gross
                    instance.discount_1 = price_result.discount_1
                    instance.discount_2 = price_result.discount_2
                    instance.net_price = price_result.net
                    instance.cost = instance.product.standard_cost

                # Auto-fill qty_open if not set
                if not instance.qty_open:
                    instance.qty_open = instance.qty_ordered

                # Calculate extension
                instance.extension = instance.net_price * instance.qty_ordered

                instance.save()
                subtotal += instance.extension

        # Handle deleted objects
        for obj in formset.deleted_objects:
            obj.delete()

        # Update order subtotal from all lines (not just new ones)
        if instances or formset.deleted_objects:
            total = sum(
                line.extension for line in OrderLine.objects.filter(order=order)
            )
            order.subtotal = total
            order.save(update_fields=["subtotal"])

        formset.save_m2m()
