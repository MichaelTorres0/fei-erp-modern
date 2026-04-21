import datetime

from django.db import transaction
from django.db.models import Sum
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
def generate_pick_ticket_from_order(order, is_backorder=False) -> PickTicket:
    """Generate a PickTicket from an Order.

    For the initial ticket (is_backorder=False), uses the full qty_open on each
    order line.  If a non-cancelled ticket already exists it is returned.

    For backorder follow-ups, a new ticket is created with whatever qty_open
    remains on each line.
    """
    if not is_backorder:
        existing = order.pick_tickets.exclude(status="CANCELLED").first()
        if existing:
            return existing

    warehouse_counts = {}
    for line in order.lines.all():
        warehouse_counts[line.warehouse_code] = warehouse_counts.get(line.warehouse_code, 0) + 1
    primary_warehouse = max(warehouse_counts, key=warehouse_counts.get) if warehouse_counts else "NY"

    ticket = PickTicket.objects.create(
        ticket_number=_next_ticket_number(),
        order=order,
        warehouse_code=primary_warehouse,
        status="OPEN",
        is_backorder=is_backorder,
    )

    for order_line in order.lines.all().order_by("line_number"):
        qty = order_line.qty_open if is_backorder else order_line.qty_ordered
        if qty <= 0:
            continue
        PickTicketLine.objects.create(
            pick_ticket=ticket,
            line_number=order_line.line_number,
            product=order_line.product,
            warehouse_code=order_line.warehouse_code,
            qty_ordered=qty,
            qty_picked=0,
        )

    return ticket


@transaction.atomic
def mark_picked(ticket: PickTicket, operator: str = "SYSTEM", line_picks: dict = None) -> PickTicket:
    """Mark pick ticket as picked.

    If line_picks is None (default), does a full pick: qty_picked = qty_ordered.
    If line_picks is provided, it maps line_number -> qty_picked for partial picks.
    """
    for line in ticket.lines.all():
        if line_picks is not None:
            line.qty_picked = min(line_picks.get(line.line_number, 0), line.qty_ordered)
        else:
            line.qty_picked = line.qty_ordered
        line.save(update_fields=["qty_picked"])

    ticket.status = "PICKED"
    ticket.picked_at = timezone.now()
    ticket.assigned_to = operator
    ticket.save(update_fields=["status", "picked_at", "assigned_to"])

    _sync_order_quantities(ticket.order)
    return ticket


def _sync_order_quantities(order):
    """Recalculate order line qty_shipped / qty_open / backorder_qty from all
    shipped + picked tickets."""
    for order_line in order.lines.all():
        total_picked = (
            PickTicketLine.objects.filter(
                pick_ticket__order=order,
                pick_ticket__status__in=["PICKED", "PACKED", "SHIPPED"],
                product=order_line.product,
                line_number=order_line.line_number,
            ).aggregate(total=Sum("qty_picked"))["total"]
            or 0
        )
        order_line.qty_shipped = total_picked
        order_line.qty_open = max(0, order_line.qty_ordered - total_picked)
        order_line.backorder_qty = order_line.qty_open
        order_line.save(update_fields=["qty_shipped", "qty_open", "backorder_qty"])


@transaction.atomic
def mark_shipped(ticket: PickTicket, tracking_number: str = "", operator: str = "SYSTEM") -> PickTicket:
    """Mark pick ticket as shipped, deduct inventory, and move order to IVQ
    when all qty has been shipped (no remaining backorders)."""
    from apps.orders.services import transition_queue

    ticket.status = "SHIPPED"
    ticket.shipped_at = timezone.now()
    ticket.tracking_number = tracking_number
    ticket.save(update_fields=["status", "shipped_at", "tracking_number"])

    from apps.products.models import WarehouseInventory
    for line in ticket.lines.all():
        if line.qty_picked <= 0:
            continue
        try:
            inv = WarehouseInventory.objects.get(
                product=line.product,
                warehouse_code=line.warehouse_code,
            )
            inv.on_hand_qty = max(0, inv.on_hand_qty - line.qty_picked)
            inv.last_activity_date = datetime.date.today()
            inv.save(update_fields=["on_hand_qty", "last_activity_date"])
        except WarehouseInventory.DoesNotExist:
            pass

    _sync_order_quantities(ticket.order)

    # Only transition to IVQ when all order qty has been shipped
    order = ticket.order
    total_open = sum(l.qty_open for l in order.lines.all())
    if total_open == 0:
        transition_queue(order, "IVQ", operator)
    else:
        # Generate backorder pick ticket for remaining qty
        generate_pick_ticket_from_order(order, is_backorder=True)

    return ticket
