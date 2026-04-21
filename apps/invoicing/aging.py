import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from django.db.models import F

from .models import Invoice


AGING_BUCKETS = [
    ("current", 0, 30),
    ("days_31_60", 31, 60),
    ("days_61_90", 61, 90),
    ("over_90", 91, None),
]


@dataclass
class AgingBuckets:
    current: Decimal = Decimal("0")
    days_31_60: Decimal = Decimal("0")
    days_61_90: Decimal = Decimal("0")
    over_90: Decimal = Decimal("0")

    @property
    def total(self) -> Decimal:
        return self.current + self.days_31_60 + self.days_61_90 + self.over_90

    def as_dict(self) -> dict:
        return {
            "current": self.current,
            "days_31_60": self.days_31_60,
            "days_61_90": self.days_61_90,
            "over_90": self.over_90,
            "total": self.total,
        }


@dataclass
class CustomerAging:
    customer_id: int
    customer_number: str
    customer_name: str
    buckets: AgingBuckets = field(default_factory=AgingBuckets)
    invoice_count: int = 0


def _bucket_for_days(days: int) -> str:
    if days <= 30:
        return "current"
    if days <= 60:
        return "days_31_60"
    if days <= 90:
        return "days_61_90"
    return "over_90"


def age_invoice(invoice: Invoice, as_of: Optional[datetime.date] = None) -> int:
    """Return age in days for an invoice relative to as_of (default today).

    Uses due_date when present, otherwise invoice_date. Negative means not yet due.
    """
    if as_of is None:
        as_of = datetime.date.today()
    reference = invoice.due_date or invoice.invoice_date
    return (as_of - reference).days


def ar_aging_by_customer(as_of: Optional[datetime.date] = None) -> List[CustomerAging]:
    """Bucket all OPEN invoice amounts by customer into aging ranges.

    Returns rows sorted by total outstanding (descending).
    """
    if as_of is None:
        as_of = datetime.date.today()

    open_invoices = (
        Invoice.objects.filter(status="OPEN")
        .annotate(outstanding=F("total") - F("amount_paid"))
        .filter(outstanding__gt=0)
        .select_related("customer")
    )

    by_customer: dict[int, CustomerAging] = {}
    for inv in open_invoices:
        customer = inv.customer
        row = by_customer.setdefault(
            customer.id,
            CustomerAging(
                customer_id=customer.id,
                customer_number=customer.customer_number,
                customer_name=customer.name,
            ),
        )
        days = age_invoice(inv, as_of=as_of)
        bucket = _bucket_for_days(days)
        outstanding = Decimal(str(inv.total)) - Decimal(str(inv.amount_paid))
        setattr(row.buckets, bucket, getattr(row.buckets, bucket) + outstanding)
        row.invoice_count += 1

    rows = list(by_customer.values())
    rows.sort(key=lambda r: r.buckets.total, reverse=True)
    return rows


def ar_aging_totals(as_of: Optional[datetime.date] = None) -> AgingBuckets:
    """Aggregate aging totals across all customers."""
    totals = AgingBuckets()
    for row in ar_aging_by_customer(as_of=as_of):
        totals.current += row.buckets.current
        totals.days_31_60 += row.buckets.days_31_60
        totals.days_61_90 += row.buckets.days_61_90
        totals.over_90 += row.buckets.over_90
    return totals


def sync_over_90_balances(as_of: Optional[datetime.date] = None) -> int:
    """Recalculate customer.over_90_balance from open invoices aged 90+.

    Credit-check uses this field. Returns the number of customers updated.
    """
    from apps.customers.models import Customer

    if as_of is None:
        as_of = datetime.date.today()

    rows = ar_aging_by_customer(as_of=as_of)
    by_customer = {r.customer_id: r.buckets.over_90 for r in rows}

    updated = 0
    for customer in Customer.objects.all():
        new_value = by_customer.get(customer.id, Decimal("0"))
        if Decimal(str(customer.over_90_balance)) != new_value:
            customer.over_90_balance = new_value
            customer.save(update_fields=["over_90_balance"])
            updated += 1
    return updated
