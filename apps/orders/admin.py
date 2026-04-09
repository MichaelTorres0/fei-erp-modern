import datetime
from decimal import Decimal

from django.contrib import admin, messages
from django.utils.html import format_html
from .models import Order, OrderLine, OrderAudit
from .services import check_credit, sync_customer_open_orders, VALID_TRANSITIONS
from apps.pricing.services import calculate_price
from apps.products.services import get_availability


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 1
    autocomplete_fields = ["product"]
    readonly_fields = ["extension"]
    fields = [
        "line_number", "product", "warehouse_code",
        "qty_ordered", "qty_open", "qty_shipped", "backorder_qty",
        "unit_price", "discount_1", "discount_2", "net_price", "cost",
        "extension",
    ]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Set warehouse_code to use WarehouseInventory choices."""
        if db_field.name == "warehouse_code":
            kwargs["widget"] = admin.widgets.AdminTextInputWidget()
            field = super().formfield_for_dbfield(db_field, request, **kwargs)
            field.initial = "NY"
            return field
        return super().formfield_for_dbfield(db_field, request, **kwargs)


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
    readonly_fields = [
        "order_number", "entry_date", "created_at", "updated_at",
        "subtotal", "credit_info_display",
    ]
    autocomplete_fields = ["customer"]
    date_hierarchy = "order_date"
    inlines = [OrderLineInline, OrderAuditInline]

    class Media:
        js = ("orders/js/order_admin.js",)
        css = {"all": ("orders/css/order_admin.css",)}

    fieldsets = (
        ("Order Info", {
            "fields": (
                "order_number", "customer", "order_date", "required_date",
                "po_number", "placed_by", "email", "queue_status",
                "credit_info_display",
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

    @admin.display(description="Credit Info")
    def credit_info_display(self, obj):
        if not obj.pk or not obj.customer_id:
            return "-"
        c = obj.customer
        color = "#28a745" if c.available_credit > 0 else "#dc3545"
        return format_html(
            '<div style="line-height:1.6">'
            'Credit Code: <b>{}</b> &nbsp;|&nbsp; '
            'Limit: <b>${:,.2f}</b> &nbsp;|&nbsp; '
            'AR Balance: <b>${:,.2f}</b> &nbsp;|&nbsp; '
            'Open Orders: <b>${:,.2f}</b><br>'
            'Over 90: <b>${:,.2f}</b> &nbsp;|&nbsp; '
            'Available: <span style="color:{}; font-weight:bold">${:,.2f}</span>'
            '</div>',
            c.credit_code or "—",
            c.credit_limit,
            c.ar_balance,
            c.open_order_amount,
            c.over_90_balance,
            color,
            c.available_credit,
        )

    def get_readonly_fields(self, request, obj=None):
        """Make order_number readonly always (auto-generated for new, fixed for existing)."""
        base = list(self.readonly_fields)
        if obj and obj.pk:
            # Existing order: also show credit info
            return base
        else:
            # New order: order_number will be auto-generated on save
            return base

    def get_changeform_initial_data(self, request):
        """Provide sensible defaults for new orders."""
        return {
            "order_date": datetime.date.today(),
            "queue_status": "OEQ",
            "placed_by": request.user.username,
        }

    def save_model(self, request, obj, form, change):
        """Auto-generate order number for new orders and run credit check."""
        if not change:
            # New order — auto-generate order number
            if not obj.order_number:
                from .services import _next_order_number
                obj.order_number = _next_order_number()

        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        """
        Auto-fill pricing on order lines, auto-increment line numbers,
        recalculate subtotal, and run credit check.
        """
        instances = formset.save(commit=False)
        order = form.instance
        customer = order.customer

        # Determine next line number
        existing_max = 0
        for line in OrderLine.objects.filter(order=order):
            if line.line_number > existing_max:
                existing_max = line.line_number

        next_line = existing_max + 1

        for instance in instances:
            if isinstance(instance, OrderLine):
                # Auto-assign line_number if not set
                if not instance.line_number or instance.line_number == 0:
                    instance.line_number = next_line
                    next_line += 1

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

                # Default warehouse_code
                if not instance.warehouse_code:
                    instance.warehouse_code = "NY"

                # Calculate extension
                instance.extension = instance.net_price * instance.qty_ordered

                instance.save()

        # Handle deleted objects
        for obj in formset.deleted_objects:
            obj.delete()

        # Update order subtotal from all lines
        if instances or formset.deleted_objects:
            total = sum(
                line.extension for line in OrderLine.objects.filter(order=order)
            )
            order.subtotal = total
            order.save(update_fields=["subtotal"])

        formset.save_m2m()

    def save_related(self, request, form, formsets, change):
        """After all formsets saved, run credit check, sync open orders, check inventory."""
        super().save_related(request, form, formsets, change)

        order = form.instance

        if not change and order.queue_status == "OEQ":
            # New order — run credit check and route
            credit_result = check_credit(order.customer, order.subtotal)
            order.queue_status = credit_result.queue
            order.save(update_fields=["queue_status"])

            OrderAudit.objects.create(
                order=order,
                operator=request.user.username,
                event_code=order.queue_status,
                notes=f"Admin order entry: {credit_result.reason}",
            )

            if credit_result.approved:
                messages.success(request, f"Credit approved — routed to {credit_result.queue}. {credit_result.reason}")
            else:
                messages.warning(request, f"Credit hold — routed to {credit_result.queue}. {credit_result.reason}")

            # Check route_to_ptq annex flag
            customer = order.customer
            if credit_result.approved and hasattr(customer, "annex") and customer.annex.route_to_ptq:
                order.queue_status = "PTQ"
                order.save(update_fields=["queue_status"])
                OrderAudit.objects.create(
                    order=order,
                    operator="SYSTEM",
                    event_code="PTQ",
                    notes="Auto-routed to PTQ (customer annex flag)",
                )
                messages.info(request, "Customer has route_to_ptq flag — auto-routed to Pick Ticket queue.")

        elif change:
            # Existing order — validate queue transition if status changed
            if "queue_status" in form.changed_data:
                old_status = form.initial.get("queue_status", "OEQ")
                new_status = order.queue_status
                allowed = VALID_TRANSITIONS.get(old_status, [])

                if new_status != old_status and new_status not in allowed:
                    # Revert the invalid transition
                    order.queue_status = old_status
                    order.save(update_fields=["queue_status"])
                    messages.error(
                        request,
                        f"Invalid queue transition: {old_status} → {new_status}. "
                        f"Allowed transitions from {old_status}: {', '.join(allowed) if allowed else 'none'}",
                    )
                elif new_status != old_status:
                    OrderAudit.objects.create(
                        order=order,
                        operator=request.user.username,
                        event_code=new_status,
                        notes=f"Manual transition from {old_status}",
                    )
                    messages.success(request, f"Queue transitioned: {old_status} → {new_status}")

        # Always sync customer open order amount
        sync_customer_open_orders(order.customer)

        # Check inventory on order lines and warn if insufficient
        for line in order.lines.all():
            availability = get_availability(line.product, line.warehouse_code)
            if line.warehouse_code in availability:
                avail = availability[line.warehouse_code]["available"]
                if line.qty_ordered > avail:
                    messages.warning(
                        request,
                        f"Inventory warning: {line.product.product_number} in {line.warehouse_code} — "
                        f"ordered {line.qty_ordered}, only {avail} available.",
                    )
