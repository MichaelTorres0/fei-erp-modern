import datetime
from decimal import Decimal
from typing import Iterable

from django.db import transaction
from django.db.models import Sum

from apps.invoicing.models import Invoice, InvoiceLine
from apps.products.models import WarehouseInventory

from .models import RMA, RMALine


def _next_rma_number() -> str:
    last = RMA.objects.order_by("-id").values_list("rma_number", flat=True).first()
    if last and last.startswith("RMA-"):
        try:
            seq = int(last.split("-")[1]) + 1
        except (IndexError, ValueError):
            seq = 1
    else:
        seq = 1
    return f"RMA-{seq:06d}"


def _next_credit_memo_number() -> str:
    last = (
        RMA.objects.exclude(credit_memo_number="")
        .order_by("-id")
        .values_list("credit_memo_number", flat=True)
        .first()
    )
    if last and last.startswith("CM-"):
        try:
            seq = int(last.split("-")[1]) + 1
        except (IndexError, ValueError):
            seq = 1
    else:
        seq = 1
    return f"CM-{seq:06d}"


@transaction.atomic
def create_rma(
    invoice: Invoice,
    lines: Iterable[dict],
    reason: str = "OTHER",
    restock_to_warehouse: str = "NY",
    operator: str = "SYSTEM",
    notes: str = "",
) -> RMA:
    """Authorize a return for selected invoice lines.

    Each `lines` entry: {"invoice_line_id": int, "qty_returned": int, "restock": bool (opt)}.
    Qty cannot exceed invoiced qty, and the per-line total across active RMAs cannot
    exceed the invoiced qty.
    """
    line_specs = list(lines)
    if not line_specs:
        raise ValueError("At least one line is required to create an RMA")

    rma = RMA(
        rma_number=_next_rma_number(),
        invoice=invoice,
        customer=invoice.customer,
        reason=reason,
        status="OPEN",
        issued_date=datetime.date.today(),
        restock_to_warehouse=restock_to_warehouse,
        created_by=operator,
        notes=notes,
    )
    rma.save()

    total = Decimal("0")
    for idx, spec in enumerate(line_specs, start=1):
        invoice_line = InvoiceLine.objects.get(pk=spec["invoice_line_id"], invoice=invoice)
        qty = int(spec["qty_returned"])
        if qty <= 0:
            raise ValueError(f"Line {idx}: qty_returned must be positive")

        already_returned = RMALine.objects.filter(
            invoice_line=invoice_line,
            rma__status__in=["OPEN", "RECEIVED", "CREDITED"],
        ).aggregate(total=Sum("qty_returned"))["total"] or 0
        available = invoice_line.qty_shipped - already_returned
        if qty > available:
            raise ValueError(
                f"Line {idx}: cannot return {qty} of {invoice_line.product.product_number}; "
                f"only {available} available (invoiced {invoice_line.qty_shipped}, "
                f"already returned {already_returned})"
            )

        extension = Decimal(str(invoice_line.net_price)) * qty
        RMALine.objects.create(
            rma=rma,
            line_number=idx,
            invoice_line=invoice_line,
            product=invoice_line.product,
            qty_returned=qty,
            unit_price=invoice_line.net_price,
            restock=spec.get("restock", True),
            extension=extension,
        )
        total += extension

    rma.credit_amount = total
    rma.save(update_fields=["credit_amount"])
    return rma


@transaction.atomic
def receive_rma(rma: RMA, operator: str = "SYSTEM") -> RMA:
    """Mark goods as received. Optionally restocks inventory per-line."""
    if rma.status != "OPEN":
        raise ValueError(f"Cannot receive RMA in {rma.status} status")

    for line in rma.lines.all():
        line.qty_received = line.qty_returned
        line.save(update_fields=["qty_received"])

        if line.restock and rma.restock_to_warehouse:
            inv, _ = WarehouseInventory.objects.get_or_create(
                product=line.product,
                warehouse_code=rma.restock_to_warehouse,
                defaults={"on_hand_qty": 0},
            )
            inv.on_hand_qty = inv.on_hand_qty + line.qty_received
            inv.last_activity_date = datetime.date.today()
            inv.save(update_fields=["on_hand_qty", "last_activity_date"])

    rma.status = "RECEIVED"
    rma.received_date = datetime.date.today()
    rma.save(update_fields=["status", "received_date"])
    return rma


@transaction.atomic
def issue_credit_memo(rma: RMA, operator: str = "SYSTEM") -> RMA:
    """Issue a credit memo against the original invoice.

    Reduces customer.ar_balance by the credit amount. If the resulting invoice
    balance becomes fully credited + paid, mark the invoice PAID.
    """
    if rma.status != "RECEIVED":
        raise ValueError(f"Cannot issue credit memo for RMA in {rma.status} status")

    rma.credit_memo_number = _next_credit_memo_number()
    rma.credited_date = datetime.date.today()
    rma.status = "CREDITED"
    rma.save(update_fields=["credit_memo_number", "credited_date", "status"])

    credit = Decimal(str(rma.credit_amount))

    customer = rma.customer
    customer.ar_balance = Decimal(str(customer.ar_balance)) - credit
    customer.ytd_sales = Decimal(str(customer.ytd_sales)) - credit
    customer.save(update_fields=["ar_balance", "ytd_sales"])

    # Apply credit against the invoice (treated like a payment for tracking purposes)
    invoice = rma.invoice
    invoice.amount_paid = Decimal(str(invoice.amount_paid)) + credit
    if invoice.amount_paid >= invoice.total:
        invoice.status = "PAID"
    invoice.save(update_fields=["amount_paid", "status"])

    return rma


@transaction.atomic
def cancel_rma(rma: RMA, operator: str = "SYSTEM", reason: str = "") -> RMA:
    """Cancel an RMA before it's credited. No-op if already credited."""
    if rma.status == "CREDITED":
        raise ValueError("Cannot cancel an RMA that has already been credited")
    rma.status = "CANCELLED"
    if reason:
        rma.notes = (rma.notes + "\n" if rma.notes else "") + f"Cancelled: {reason}"
    rma.save(update_fields=["status", "notes"])
    return rma
