from django.contrib import admin
from django.utils.html import format_html

from .models import PickTicket, PickTicketLine


class PickTicketLineInline(admin.TabularInline):
    model = PickTicketLine
    extra = 0
    readonly_fields = ["line_number", "product", "warehouse_code", "qty_ordered"]

    fields = ["line_number", "product", "warehouse_code", "qty_ordered", "qty_picked"]


STATUS_COLORS = {
    "OPEN": "#6c757d",
    "PICKED": "#f59e0b",
    "PACKED": "#3b82f6",
    "SHIPPED": "#10b981",
    "CANCELLED": "#ef4444",
}


@admin.register(PickTicket)
class PickTicketAdmin(admin.ModelAdmin):
    list_display = [
        "ticket_number",
        "order",
        "warehouse_code",
        "colored_status",
        "assigned_to",
        "picked_at",
        "shipped_at",
    ]
    list_filter = ["status", "warehouse_code"]
    search_fields = [
        "ticket_number",
        "order__order_number",
        "order__customer__name",
        "tracking_number",
    ]
    readonly_fields = [
        "ticket_number", "order", "warehouse_code",
        "created_at", "updated_at",
    ]
    inlines = [PickTicketLineInline]

    fieldsets = (
        ("Pick Ticket Info", {
            "fields": (
                "ticket_number", "order", "warehouse_code",
                "status", "assigned_to",
            )
        }),
        ("Timestamps", {
            "fields": (
                "picked_at", "packed_at", "shipped_at",
                "created_at", "updated_at",
            )
        }),
        ("Shipping", {
            "fields": ("tracking_number", "notes"),
        }),
    )

    @admin.display(description="Status")
    def colored_status(self, obj):
        color = STATUS_COLORS.get(obj.status, "#000000")
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; '
            'border-radius:3px; font-weight:bold;">{}</span>',
            color,
            obj.status,
        )
