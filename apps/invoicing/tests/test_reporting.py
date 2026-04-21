import datetime
from decimal import Decimal

import pytest

from apps.customers.models import Customer, CustomerAnnex
from apps.invoicing.models import Invoice, InvoiceLine
from apps.invoicing.reporting import sales_by_product, sales_by_salesperson, sales_by_territory
from apps.orders.models import Order
from apps.products.models import Product


@pytest.fixture
def setup_invoiced_data(db):
    """Create two customers, two products, and invoiced data for reporting."""
    c1 = Customer.objects.create(
        customer_number="REP-C1", name="Rep Customer 1",
        credit_code="A", credit_limit=Decimal("100000"),
        territory_1="EAST", salesman="SAL-01",
    )
    c2 = Customer.objects.create(
        customer_number="REP-C2", name="Rep Customer 2",
        credit_code="A", credit_limit=Decimal("100000"),
        territory_1="WEST", salesman="SAL-02",
    )
    CustomerAnnex.objects.create(customer=c1)
    CustomerAnnex.objects.create(customer=c2)

    p1 = Product.objects.create(
        product_number="REP-P1", description="Widget A",
        list_price=Decimal("100.0000"), standard_cost=Decimal("40.0000"),
    )
    p2 = Product.objects.create(
        product_number="REP-P2", description="Widget B",
        list_price=Decimal("200.0000"), standard_cost=Decimal("120.0000"),
    )

    today = datetime.date.today()

    # Order + Invoice for c1 (SAL-01, EAST)
    o1 = Order.objects.create(
        order_number="REP-ORD-01", customer=c1, placed_by="TEST",
        order_date=today, terms="N30", queue_status="IVQ",
        salesman="SAL-01", territory_1="EAST",
    )
    inv1 = Invoice.objects.create(
        invoice_number="REP-INV-01", order=o1, customer=c1,
        invoice_date=today, subtotal=Decimal("500"), total=Decimal("500"),
        status="OPEN",
    )
    InvoiceLine.objects.create(
        invoice=inv1, line_number=1, product=p1,
        qty_shipped=5, unit_price=Decimal("100"), net_price=Decimal("100"),
        extension=Decimal("500"),
    )

    # Order + Invoice for c2 (SAL-02, WEST)
    o2 = Order.objects.create(
        order_number="REP-ORD-02", customer=c2, placed_by="TEST",
        order_date=today, terms="N30", queue_status="IVQ",
        salesman="SAL-02", territory_1="WEST",
    )
    inv2 = Invoice.objects.create(
        invoice_number="REP-INV-02", order=o2, customer=c2,
        invoice_date=today, subtotal=Decimal("800"), total=Decimal("800"),
        status="PAID",
    )
    InvoiceLine.objects.create(
        invoice=inv2, line_number=1, product=p2,
        qty_shipped=4, unit_price=Decimal("200"), net_price=Decimal("200"),
        extension=Decimal("800"),
    )

    return {"c1": c1, "c2": c2, "p1": p1, "p2": p2, "inv1": inv1, "inv2": inv2}


@pytest.mark.django_db
class TestSalesBySalesperson:
    def test_aggregates_by_salesman(self, setup_invoiced_data):
        rows = sales_by_salesperson()
        assert len(rows) == 2
        sal02 = next(r for r in rows if r["salesman"] == "SAL-02")
        assert sal02["revenue"] == Decimal("800.00")
        # cost = 4 * 120 = 480
        assert sal02["cost"] == Decimal("480.0000")
        assert sal02["margin"] == Decimal("320.0000")

    def test_filter_by_year(self, setup_invoiced_data):
        rows = sales_by_salesperson(year=1999)
        assert len(rows) == 0

    def test_sorted_by_revenue_desc(self, setup_invoiced_data):
        rows = sales_by_salesperson()
        assert rows[0]["revenue"] >= rows[1]["revenue"]


@pytest.mark.django_db
class TestSalesByTerritory:
    def test_aggregates_by_territory(self, setup_invoiced_data):
        rows = sales_by_territory()
        assert len(rows) == 2
        east = next(r for r in rows if r["territory"] == "EAST")
        assert east["revenue"] == Decimal("500.00")
        assert east["invoice_count"] == 1


@pytest.mark.django_db
class TestSalesByProduct:
    def test_top_products_by_revenue(self, setup_invoiced_data):
        rows = sales_by_product()
        assert len(rows) == 2
        assert rows[0]["product_number"] == "REP-P2"
        assert rows[0]["revenue"] == Decimal("800.00")
        assert rows[0]["qty"] == 4

    def test_limit(self, setup_invoiced_data):
        rows = sales_by_product(limit=1)
        assert len(rows) == 1
