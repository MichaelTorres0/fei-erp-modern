from django.contrib import admin
from django.utils.html import format_html

from .models import RMA, RMALine


STATUS_COLORS = {
    "OPEN": "#f59e0b",
    "RECEIVED": "#3b82f6",
    "CREDITED": "#10b981",
    "CANCELLED": "#6b7280",
}


class RMALineInline(admin.TabularInline):
    model = RMALine
    extra = 0
    autocomplete_fields = ["product"]
    readonly_fields = ["line_number", "extension"]
    fields = [
        "line_number",
        "invoice_line",
        "product",
        "qty_returned",
        "qty_received",
        "unit_price",
        "restock",
        "extension",
    ]


@admin.register(RMA)
class RMAAdmin(admin.ModelAdmin):
    list_display = [
        "rma_number",
        "invoice",
        "customer",
        "reason",
        "issued_date",
        "credit_amount",
        "credit_memo_number",
        "colored_status",
    ]
    list_filter = ["status", "reason", "issued_date"]
    search_fields = [
        "rma_number",
        "credit_memo_number",
        "invoice__invoice_number",
        "customer__customer_number",
        "customer__name",
    ]
    autocomplete_fields = ["invoice", "customer"]
    readonly_fields = [
        "rma_number",
        "credit_memo_number",
        "credit_amount",
        "credited_date",
        "received_date",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "issued_date"
    inlines = [RMALineInline]

    fieldsets = (
        ("RMA Info", {
            "fields": (
                "rma_number", "invoice", "customer", "status", "reason",
                "issued_date", "received_date", "credited_date",
            )
        }),
        ("Credit", {
            "fields": ("credit_memo_number", "credit_amount", "restock_to_warehouse"),
        }),
        ("Notes", {"fields": ("created_by", "notes")}),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
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
