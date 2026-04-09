from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

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

# Credit codes that always go to credit hold
HOLD_CREDIT_CODES = {"D", "C", "Z", "H"}


@dataclass
class CreditCheckResult:
    approved: bool
    queue: str  # "MGQ" or "CHQ"
    reason: str


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
    """
    import datetime
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
        queue_status="OEQ",
    )

    subtotal = Decimal("0")
    for idx, line_data in enumerate(lines, start=1):
        product = Product.objects.get(pk=line_data["product_id"])
        price_result = calculate_price(customer, product)

        qty = line_data["qty_ordered"]
        extension = price_result.net * qty

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
            warehouse_code=line_data.get("warehouse_code", "NY"),
            extension=extension,
        )
        subtotal += extension

    order.subtotal = subtotal
    order.save(update_fields=["subtotal"])

    credit_result = check_credit(customer, subtotal)
    order.queue_status = credit_result.queue
    order.save(update_fields=["queue_status"])

    OrderAudit.objects.create(
        order=order,
        operator=placed_by,
        event_code=order.queue_status,
        notes=credit_result.reason,
    )

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

    return order
