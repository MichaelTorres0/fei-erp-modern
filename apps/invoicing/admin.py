from django.contrib import admin
from django.utils.html import format_html

from .models import Invoice, InvoiceLine


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    readonly_fields = ["line_number", "product", "description", "qty_shipped", "unit_price", "net_price", "extension"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


STATUS_COLORS = {
    "OPEN": "#f59e0b",
    "PAID": "#10b981",
    "VOID": "#6b7280",
}


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "invoice_number",
        "order",
        "customer",
        "invoice_date",
        "due_date",
        "total",
        "amount_paid",
        "amount_due_display",
        "colored_status",
    ]
    list_filter = ["status", "invoice_date"]
    search_fields = [
        "invoice_number",
        "order__order_number",
        "customer__customer_number",
        "customer__name",
        "po_number",
    ]
    readonly_fields = [
        "invoice_number", "order", "customer", "subtotal", "total",
        "created_at", "updated_at", "amount_due_display",
    ]
    date_hierarchy = "invoice_date"
    inlines = [InvoiceLineInline]

    fieldsets = (
        ("Invoice Info", {
            "fields": (
                "invoice_number", "order", "customer", "status",
                "invoice_date", "due_date", "po_number", "terms",
            )
        }),
        ("Amounts", {
            "fields": (
                "subtotal", "shipping_cost", "tax_amount", "total",
                "amount_paid", "amount_due_display",
            )
        }),
        ("Notes", {"fields": ("notes",)}),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Amount Due")
    def amount_due_display(self, obj):
        if not obj.pk:
            return "-"
        due = obj.amount_due
        color = "#10b981" if due <= 0 else "#ef4444"
        return format_html('<span style="color:{}; font-weight:bold;">${:,.2f}</span>', color, due)

    @admin.display(description="Status")
    def colored_status(self, obj):
        color = STATUS_COLORS.get(obj.status, "#000000")
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; '
            'border-radius:3px; font-weight:bold;">{}</span>',
            color,
            obj.status,
        )
