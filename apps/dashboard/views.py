from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, F
from django.shortcuts import get_object_or_404, render

from apps.customers.models import Customer
from apps.invoicing.aging import ar_aging_by_customer, ar_aging_totals
from apps.invoicing.models import Invoice
from apps.invoicing.reporting import sales_by_product, sales_by_salesperson, sales_by_territory
from apps.orders.models import Order, OrderLine
from apps.products.models import Product, WarehouseInventory
from apps.returns.models import RMA
from apps.orders.services import OPEN_QUEUE_STATUSES


QUEUE_LABELS = {
    "OEQ": ("Order Entry", "#6c757d"),
    "MGQ": ("Management", "#28a745"),
    "CHQ": ("Credit Hold", "#dc3545"),
    "PTQ": ("Pick Ticket", "#007bff"),
    "IVQ": ("Invoiced", "#17a2b8"),
}


@staff_member_required
def home(request):
    """Main dashboard — order pipeline overview."""
    # Orders by queue with counts and totals
    queue_summary = []
    for code, (label, color) in QUEUE_LABELS.items():
        qs = Order.objects.filter(queue_status=code)
        total_value = qs.aggregate(total=Sum("subtotal"))["total"] or Decimal("0")
        queue_summary.append({
            "code": code,
            "label": label,
            "color": color,
            "count": qs.count(),
            "total_value": total_value,
        })

    # Credit hold queue — orders needing attention
    credit_hold_orders = (
        Order.objects.filter(queue_status="CHQ")
        .select_related("customer")
        .order_by("-created_at")[:10]
    )

    # Recent orders (last 10 across all queues)
    recent_orders = (
        Order.objects.select_related("customer")
        .order_by("-created_at")[:10]
    )

    # Top customers by open order value
    top_open_customers = (
        Customer.objects.filter(open_order_amount__gt=0)
        .order_by("-open_order_amount")[:5]
    )

    # Customers at or near credit limit
    at_risk_customers = []
    for c in Customer.objects.filter(is_active=True, credit_limit__gt=0):
        if c.credit_limit > 0:
            utilization = (c.credit_exposure / c.credit_limit) * 100
            if utilization >= 75:
                at_risk_customers.append({
                    "customer": c,
                    "utilization": round(float(utilization), 1),
                    "available": c.available_credit,
                })
    at_risk_customers.sort(key=lambda x: x["utilization"], reverse=True)
    at_risk_customers = at_risk_customers[:5]

    # Low inventory alerts — products where any warehouse has < 10 units
    low_inventory = (
        WarehouseInventory.objects.filter(
            on_hand_qty__lt=10,
            product__is_active=True,
        )
        .exclude(warehouse_code="D")  # Drop-ship expected to be 0
        .select_related("product")
        .order_by("on_hand_qty")[:10]
    )

    # Overall metrics
    total_open_orders = Order.objects.filter(queue_status__in=OPEN_QUEUE_STATUSES).count()
    total_open_value = (
        Order.objects.filter(queue_status__in=OPEN_QUEUE_STATUSES)
        .aggregate(total=Sum("subtotal"))["total"] or Decimal("0")
    )
    total_customers = Customer.objects.filter(is_active=True).count()
    total_products = Product.objects.filter(is_active=True).count()

    # AR aging snapshot
    aging_totals = ar_aging_totals()

    context = {
        "queue_summary": queue_summary,
        "credit_hold_orders": credit_hold_orders,
        "recent_orders": recent_orders,
        "top_open_customers": top_open_customers,
        "at_risk_customers": at_risk_customers,
        "low_inventory": low_inventory,
        "total_open_orders": total_open_orders,
        "total_open_value": total_open_value,
        "total_customers": total_customers,
        "total_products": total_products,
        "aging_totals": aging_totals,
    }
    return render(request, "dashboard/home.html", context)


@staff_member_required
def ar_aging(request):
    """AR aging report — outstanding invoice balances bucketed by age."""
    rows = ar_aging_by_customer()
    totals = ar_aging_totals()
    context = {
        "rows": rows,
        "totals": totals,
    }
    return render(request, "dashboard/ar_aging.html", context)


@staff_member_required
def order_pipeline(request):
    """Detailed order pipeline view — shows all orders grouped by queue."""
    pipeline = {}
    for code, (label, color) in QUEUE_LABELS.items():
        orders = (
            Order.objects.filter(queue_status=code)
            .select_related("customer")
            .order_by("-created_at")
        )
        pipeline[code] = {
            "label": label,
            "color": color,
            "orders": orders,
            "count": orders.count(),
            "total": orders.aggregate(total=Sum("subtotal"))["total"] or Decimal("0"),
        }

    context = {"pipeline": pipeline}
    return render(request, "dashboard/pipeline.html", context)


@staff_member_required
def inventory_overview(request):
    """Inventory overview by warehouse with committed quantities."""
    from apps.products.services import get_availability

    products = Product.objects.filter(is_active=True).order_by("product_number")
    rows = []
    for p in products:
        availability = get_availability(p)
        warehouses = {}
        total_on_hand = 0
        total_committed = 0
        for wh_code, data in availability.items():
            warehouses[wh_code] = data
            total_on_hand += data["on_hand"]
            total_committed += data["committed"]
        rows.append({
            "product": p,
            "warehouses": warehouses,
            "total_on_hand": total_on_hand,
            "total_committed": total_committed,
            "total_available": total_on_hand - total_committed,
        })

    context = {"rows": rows}
    return render(request, "dashboard/inventory.html", context)


@staff_member_required
def customer_statement(request, customer_id):
    """Unified customer statement: orders, invoices, payments, and RMAs."""
    customer = get_object_or_404(Customer, pk=customer_id)

    orders = (
        Order.objects.filter(customer=customer)
        .order_by("-order_date")
    )
    invoices = (
        Invoice.objects.filter(customer=customer)
        .order_by("-invoice_date")
    )
    rmas = (
        RMA.objects.filter(customer=customer)
        .exclude(status="CANCELLED")
        .order_by("-issued_date")
    )

    total_invoiced = invoices.aggregate(total=Sum("total"))["total"] or Decimal("0")
    total_paid = invoices.aggregate(total=Sum("amount_paid"))["total"] or Decimal("0")
    total_credits = rmas.filter(status="CREDITED").aggregate(total=Sum("credit_amount"))["total"] or Decimal("0")

    context = {
        "customer": customer,
        "orders": orders,
        "invoices": invoices,
        "rmas": rmas,
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "total_credits": total_credits,
    }
    return render(request, "dashboard/customer_statement.html", context)


@staff_member_required
def customer_list(request):
    """Customer directory for accessing statements."""
    customers = (
        Customer.objects.filter(is_active=True)
        .order_by("customer_number")
    )
    context = {"customers": customers}
    return render(request, "dashboard/customer_list.html", context)


@staff_member_required
def sales_report(request):
    """Sales analytics — YTD by salesperson, territory, and product."""
    import datetime
    year = int(request.GET.get("year", datetime.date.today().year))

    by_salesperson = sales_by_salesperson(year=year)
    by_territory = sales_by_territory(year=year)
    by_product = sales_by_product(year=year, limit=20)

    total_revenue = sum((r["revenue"] for r in by_salesperson), Decimal("0"))
    total_margin = sum((r["margin"] for r in by_salesperson), Decimal("0"))
    overall_margin_pct = (total_margin / total_revenue * 100) if total_revenue else Decimal("0")

    context = {
        "year": year,
        "by_salesperson": by_salesperson,
        "by_territory": by_territory,
        "by_product": by_product,
        "total_revenue": total_revenue,
        "total_margin": total_margin,
        "overall_margin_pct": round(overall_margin_pct, 1),
    }
    return render(request, "dashboard/sales_report.html", context)
