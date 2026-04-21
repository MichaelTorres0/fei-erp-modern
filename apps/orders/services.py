from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

from django.db import transaction
from django.db.models import Sum

from apps.orders.models import Order, OrderLine, OrderAudit
from apps.pricing.services import calculate_price
from apps.products.models import Product


# Valid queue transitions (from -> allowed destinations)
VALID_TRANSITIONS = {
    "OEQ": ["MGQ", "CHQ"],
    "CHQ": ["MGQ"],
    "MGQ": ["PTQ"],
    "PTQ": ["IVQ"],
    "IVQ": [],
}

# Queue statuses that count toward open order amount
OPEN_QUEUE_STATUSES = ["OEQ", "MGQ", "CHQ", "PTQ"]

# Credit codes that always go to credit hold
HOLD_CREDIT_CODES = {"D", "C", "Z", "H"}


@dataclass
class CreditCheckResult:
    approved: bool
    queue: str  # "MGQ" or "CHQ"
    reason: str


@dataclass
class InventoryWarning:
    product_number: str
    warehouse_code: str
    requested: int
    available: int


def check_credit(customer, order_total: Decimal) -> CreditCheckResult:
    """
    Simplified credit check based on legacy ORDER.SUBMIT lines 465-477.
    """
    if customer.credit_code == "A":
        return CreditCheckResult(approved=True, queue="MGQ", reason="Credit code A: auto-approved")

    if customer.credit_code in HOLD_CREDIT_CODES:
        return CreditCheckResult(
            approved=False, queue="CHQ",
            reason=f"Credit code {customer.credit_code}: auto-hold",
        )

    if Decimal(str(customer.over_90_balance)) > 0:
        return CreditCheckResult(
            approved=False, queue="CHQ",
            reason=f"Over 90-day balance: ${customer.over_90_balance}",
        )

    total_exposure = Decimal(str(customer.ar_balance)) + Decimal(str(customer.open_order_amount)) + order_total
    if total_exposure > Decimal(str(customer.credit_limit)):
        return CreditCheckResult(
            approved=False, queue="CHQ",
            reason=f"Credit limit exceeded: ${total_exposure} > ${customer.credit_limit}",
        )

    return CreditCheckResult(approved=True, queue="MGQ", reason="Credit check passed")


def sync_customer_open_orders(customer):
    """
    Recalculate customer.open_order_amount from all active orders.
    This keeps credit exposure accurate.
    """
    total = Order.objects.filter(
        customer=customer,
        queue_status__in=OPEN_QUEUE_STATUSES,
    ).aggregate(total=Sum("subtotal"))["total"] or Decimal("0")

    customer.open_order_amount = total
    customer.save(update_fields=["open_order_amount"])
    return total


def check_inventory(lines) -> List[InventoryWarning]:
    """
    Check if requested quantities are available. Returns warnings (non-blocking).
    """
    from apps.products.services import get_availability

    warnings = []
    for line_data in lines:
        product = Product.objects.get(pk=line_data["product_id"])
        warehouse = line_data.get("warehouse_code", "NY")
        qty = line_data["qty_ordered"]

        availability = get_availability(product, warehouse)
        if warehouse in availability:
            available = availability[warehouse]["available"]
            if qty > available:
                warnings.append(InventoryWarning(
                    product_number=product.product_number,
                    warehouse_code=warehouse,
                    requested=qty,
                    available=available,
                ))
        else:
            warnings.append(InventoryWarning(
                product_number=product.product_number,
                warehouse_code=warehouse,
                requested=qty,
                available=0,
            ))

    return warnings


def _next_order_number() -> str:
    """Generate next sequential order number."""
    last = Order.objects.order_by("-id").values_list("order_number", flat=True).first()
    if last and last.startswith("ORD-"):
        try:
            seq = int(last.split("-")[1]) + 1
        except (IndexError, ValueError):
            seq = 1
    else:
        seq = 1
    return f"ORD-{seq:06d}"


@transaction.atomic
def create_order(customer, lines, placed_by="SYSTEM", **header_fields) -> Order:
    """
    Create an order with lines, pricing, and credit check routing.
    Handles drop-ship auto-detection and route_to_ptq annex flag.
    Returns (order, inventory_warnings).
    """
    import datetime

    # Check if any line is drop-ship
    has_drop_ship = False
    for line_data in lines:
        product = Product.objects.get(pk=line_data["product_id"])
        if product.is_drop_ship:
            has_drop_ship = True
            break

    order = Order.objects.create(
        order_number=_next_order_number(),
        customer=customer,
        placed_by=placed_by,
        order_date=header_fields.get("order_date", datetime.date.today()),
        terms=header_fields.get("terms", customer.terms_code),
        salesman=header_fields.get("salesman", customer.salesman),
        affiliation=customer.affiliation,
        territory_1=customer.territory_1,
        territory_2=customer.territory_2,
        territory_3=customer.territory_3,
        ship_via=header_fields.get("ship_via", customer.default_ship_via),
        freight_terms=header_fields.get("freight_terms", customer.freight_terms),
        po_number=header_fields.get("po_number", ""),
        email=header_fields.get("email", customer.email),
        is_drop_ship=has_drop_ship,
        queue_status="OEQ",
    )

    subtotal = Decimal("0")
    for idx, line_data in enumerate(lines, start=1):
        product = Product.objects.get(pk=line_data["product_id"])
        price_result = calculate_price(customer, product)

        qty = line_data["qty_ordered"]
        extension = price_result.net * qty

        # Auto-route drop-ship products to D warehouse
        warehouse = line_data.get("warehouse_code", "NY")
        if product.is_drop_ship:
            warehouse = "D"

        OrderLine.objects.create(
            order=order,
            line_number=idx,
            product=product,
            unit_price=price_result.gross,
            discount_1=price_result.discount_1,
            discount_2=price_result.discount_2,
            net_price=price_result.net,
            cost=product.standard_cost,
            qty_ordered=qty,
            qty_open=qty,
            warehouse_code=warehouse,
            extension=extension,
        )
        subtotal += extension

    order.subtotal = subtotal
    order.save(update_fields=["subtotal"])

    # Run credit check and route
    credit_result = check_credit(customer, subtotal)
    order.queue_status = credit_result.queue
    order.save(update_fields=["queue_status"])

    OrderAudit.objects.create(
        order=order,
        operator=placed_by,
        event_code=order.queue_status,
        notes=credit_result.reason,
    )

    # Check route_to_ptq annex flag — if set and credit approved, skip MGQ
    if credit_result.approved and hasattr(customer, "annex") and customer.annex.route_to_ptq:
        order.queue_status = "PTQ"
        order.save(update_fields=["queue_status"])
        OrderAudit.objects.create(
            order=order,
            operator="SYSTEM",
            event_code="PTQ",
            notes="Auto-routed to PTQ (customer annex flag)",
        )

    # Sync customer open order amount
    sync_customer_open_orders(customer)

    # Check inventory (non-blocking warnings)
    inventory_warnings = check_inventory(lines)

    return order


def transition_queue(order, new_status, operator) -> Order:
    """Validated queue state transition with audit trail."""
    allowed = VALID_TRANSITIONS.get(order.queue_status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Invalid queue transition: {order.queue_status} -> {new_status}. "
            f"Allowed: {allowed}"
        )

    old_status = order.queue_status
    order.queue_status = new_status
    order.save(update_fields=["queue_status", "updated_at"])

    OrderAudit.objects.create(
        order=order,
        operator=operator,
        event_code=new_status,
        notes=f"Transitioned from {old_status}",
    )

    # Auto-generate pick ticket when entering PTQ
    if new_status == "PTQ":
        from apps.fulfillment.services import generate_pick_ticket_from_order
        generate_pick_ticket_from_order(order)

    # Sync customer open order amount when order leaves active queues
    if new_status == "IVQ":
        sync_customer_open_orders(order.customer)
        # Auto-generate invoice
        from apps.invoicing.services import generate_invoice_from_order
        generate_invoice_from_order(order, operator=operator)

    return order
