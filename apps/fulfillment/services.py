import datetime

from django.db import transaction
from django.utils import timezone

from .models import PickTicket, PickTicketLine


def _next_ticket_number() -> str:
    last = PickTicket.objects.order_by("-id").values_list("ticket_number", flat=True).first()
    if last and last.startswith("PT-"):
        try:
            seq = int(last.split("-")[1]) + 1
        except (IndexError, ValueError):
            seq = 1
    else:
        seq = 1
    return f"PT-{seq:06d}"


@transaction.atomic
def generate_pick_ticket_from_order(order) -> PickTicket:
    """
    Generate a PickTicket from an Order in PTQ status.
    Uses primary warehouse from lines (most common warehouse_code).
    """
    if hasattr(order, "pick_ticket"):
        return order.pick_ticket

    # Determine primary warehouse from order lines
    warehouse_counts = {}
    for line in order.lines.all():
        warehouse_counts[line.warehouse_code] = warehouse_counts.get(line.warehouse_code, 0) + 1
    primary_warehouse = max(warehouse_counts, key=warehouse_counts.get) if warehouse_counts else "NY"

    ticket = PickTicket.objects.create(
        ticket_number=_next_ticket_number(),
        order=order,
        warehouse_code=primary_warehouse,
        status="OPEN",
    )

    for order_line in order.lines.all().order_by("line_number"):
        PickTicketLine.objects.create(
            pick_ticket=ticket,
            line_number=order_line.line_number,
            product=order_line.product,
            warehouse_code=order_line.warehouse_code,
            qty_ordered=order_line.qty_ordered,
            qty_picked=0,
        )

    return ticket


@transaction.atomic
def mark_picked(ticket: PickTicket, operator: str = "SYSTEM") -> PickTicket:
    """Mark pick ticket as picked. Sets qty_picked = qty_ordered on all lines."""
    for line in ticket.lines.all():
        line.qty_picked = line.qty_ordered
        line.save(update_fields=["qty_picked"])

    ticket.status = "PICKED"
    ticket.picked_at = timezone.now()
    ticket.assigned_to = operator
    ticket.save(update_fields=["status", "picked_at", "assigned_to"])

    # Update order line qty_shipped to match picked
    order = ticket.order
    for order_line in order.lines.all():
        order_line.qty_shipped = order_line.qty_ordered
        order_line.qty_open = 0
        order_line.save(update_fields=["qty_shipped", "qty_open"])

    return ticket


@transaction.atomic
def mark_shipped(ticket: PickTicket, tracking_number: str = "", operator: str = "SYSTEM") -> PickTicket:
    """Mark pick ticket as shipped. Transitions order to IVQ (which generates invoice)."""
    from apps.orders.services import transition_queue

    ticket.status = "SHIPPED"
    ticket.shipped_at = timezone.now()
    ticket.tracking_number = tracking_number
    ticket.save(update_fields=["status", "shipped_at", "tracking_number"])

    # Deduct shipped qty from warehouse inventory
    from apps.products.models import WarehouseInventory
    for line in ticket.lines.all():
        try:
            inv = WarehouseInventory.objects.get(
                product=line.product,
                warehouse_code=line.warehouse_code,
            )
            inv.on_hand_qty = max(0, inv.on_hand_qty - line.qty_picked)
            inv.last_activity_date = datetime.date.today()
            inv.save(update_fields=["on_hand_qty", "last_activity_date"])
        except WarehouseInventory.DoesNotExist:
            pass  # Drop-ship products may not have warehouse inventory

    # Transition order PTQ -> IVQ (auto-generates invoice via orders.services)
    transition_queue(ticket.order, "IVQ", operator)

    return ticket
