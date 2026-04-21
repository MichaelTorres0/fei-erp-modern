import datetime
from decimal import Decimal

from django.db import transaction

from .models import Invoice, InvoiceLine


def _next_invoice_number() -> str:
    last = Invoice.objects.order_by("-id").values_list("invoice_number", flat=True).first()
    if last and last.startswith("INV-"):
        try:
            seq = int(last.split("-")[1]) + 1
        except (IndexError, ValueError):
            seq = 1
    else:
        seq = 1
    return f"INV-{seq:06d}"


def _compute_due_date(invoice_date, terms):
    """Compute due date from terms code (e.g., 'N30' = net 30 days)."""
    if not terms:
        return None
    terms_upper = terms.upper().strip()
    if terms_upper.startswith("N"):
        try:
            days = int(terms_upper[1:])
            return invoice_date + datetime.timedelta(days=days)
        except ValueError:
            return None
    return None


@transaction.atomic
def generate_invoice_from_order(order, operator="SYSTEM") -> Invoice:
    """
    Generate an Invoice from an Order. Called when an order transitions to IVQ.
    Uses qty_shipped (or falls back to qty_ordered) for invoiced quantities.
    """
    if hasattr(order, "invoice"):
        # Already invoiced
        return order.invoice

    invoice_date = datetime.date.today()
    due_date = _compute_due_date(invoice_date, order.terms)

    invoice = Invoice.objects.create(
        invoice_number=_next_invoice_number(),
        order=order,
        customer=order.customer,
        invoice_date=invoice_date,
        due_date=due_date,
        shipping_cost=order.shipping_cost,
        terms=order.terms,
        po_number=order.po_number,
        status="OPEN",
    )

    subtotal = Decimal("0")
    for order_line in order.lines.all().order_by("line_number"):
        qty = order_line.qty_shipped if order_line.qty_shipped > 0 else order_line.qty_ordered
        extension = order_line.net_price * qty
        InvoiceLine.objects.create(
            invoice=invoice,
            line_number=order_line.line_number,
            product=order_line.product,
            description=order_line.product.description[:255],
            qty_shipped=qty,
            unit_price=order_line.unit_price,
            net_price=order_line.net_price,
            extension=extension,
        )
        subtotal += extension

    invoice.subtotal = subtotal
    invoice.total = subtotal + invoice.shipping_cost + invoice.tax_amount
    invoice.save(update_fields=["subtotal", "total"])

    # Update customer AR balance and YTD sales
    customer = order.customer
    customer.ar_balance = customer.ar_balance + invoice.total
    customer.ytd_sales = customer.ytd_sales + invoice.total
    customer.save(update_fields=["ar_balance", "ytd_sales"])

    return invoice


@transaction.atomic
def record_payment(invoice: Invoice, amount: Decimal, payment_date=None) -> Invoice:
    """Record a payment against an invoice."""
    if payment_date is None:
        payment_date = datetime.date.today()

    invoice.amount_paid = invoice.amount_paid + Decimal(str(amount))
    if invoice.amount_paid >= invoice.total:
        invoice.status = "PAID"
    invoice.save(update_fields=["amount_paid", "status"])

    # Update customer AR balance and last payment info
    customer = invoice.customer
    customer.ar_balance = customer.ar_balance - Decimal(str(amount))
    customer.last_payment_date = payment_date
    customer.last_payment_amount = Decimal(str(amount))
    customer.save(update_fields=["ar_balance", "last_payment_date", "last_payment_amount"])

    return invoice
