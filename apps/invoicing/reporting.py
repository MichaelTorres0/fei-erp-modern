"""Sales reporting queries — aggregates from InvoiceLine / Invoice data."""

from decimal import Decimal

from django.db.models import F, Sum, Value
from django.db.models.functions import Coalesce

from .models import Invoice, InvoiceLine


def _zero():
    return Coalesce(Sum("extension"), Value(Decimal("0")))


def _cost():
    return Coalesce(Sum(F("qty_shipped") * F("product__standard_cost")), Value(Decimal("0")))


def sales_by_salesperson(year: int = None):
    """Revenue and margin by salesperson from invoiced order lines.

    Returns list of dicts sorted by revenue desc.
    """
    qs = InvoiceLine.objects.filter(invoice__status__in=["OPEN", "PAID"])
    if year:
        qs = qs.filter(invoice__invoice_date__year=year)

    rows = (
        qs.values(salesman=F("invoice__order__salesman"))
        .annotate(revenue=_zero(), cost=_cost(), line_count=Sum(Value(1)))
        .order_by("-revenue")
    )
    result = []
    for r in rows:
        revenue = r["revenue"]
        cost = r["cost"]
        margin = revenue - cost
        margin_pct = (margin / revenue * 100) if revenue else Decimal("0")
        result.append({
            "salesman": r["salesman"] or "(unassigned)",
            "revenue": revenue,
            "cost": cost,
            "margin": margin,
            "margin_pct": round(margin_pct, 1),
            "line_count": r["line_count"],
        })
    return result


def sales_by_territory(year: int = None):
    """Revenue by territory_1 from invoiced orders."""
    qs = Invoice.objects.filter(status__in=["OPEN", "PAID"])
    if year:
        qs = qs.filter(invoice_date__year=year)

    rows = (
        qs.values(territory=F("order__territory_1"))
        .annotate(revenue=Coalesce(Sum("total"), Value(Decimal("0"))), count=Sum(Value(1)))
        .order_by("-revenue")
    )
    return [
        {
            "territory": r["territory"] or "(unassigned)",
            "revenue": r["revenue"],
            "invoice_count": r["count"],
        }
        for r in rows
    ]


def sales_by_product(year: int = None, limit: int = 20):
    """Top products by invoiced revenue."""
    qs = InvoiceLine.objects.filter(invoice__status__in=["OPEN", "PAID"])
    if year:
        qs = qs.filter(invoice__invoice_date__year=year)

    rows = (
        qs.values(
            product_number=F("product__product_number"),
            product_desc=F("product__description"),
        )
        .annotate(
            revenue=_zero(),
            cost=_cost(),
            qty=Coalesce(Sum("qty_shipped"), Value(0)),
        )
        .order_by("-revenue")[:limit]
    )
    result = []
    for r in rows:
        revenue = r["revenue"]
        cost = r["cost"]
        margin = revenue - cost
        margin_pct = (margin / revenue * 100) if revenue else Decimal("0")
        result.append({
            "product_number": r["product_number"],
            "description": (r["product_desc"] or "")[:60],
            "revenue": revenue,
            "cost": cost,
            "margin": margin,
            "margin_pct": round(margin_pct, 1),
            "qty": r["qty"],
        })
    return result
