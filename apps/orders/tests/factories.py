import factory
from datetime import date
from apps.orders.models import Order, OrderLine, OrderAudit
from apps.customers.tests.factories import CustomerFactory
from apps.products.tests.factories import ProductFactory


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    order_number = factory.Sequence(lambda n: f"ORD-{n:06d}")
    customer = factory.SubFactory(CustomerFactory)
    order_date = factory.LazyFunction(date.today)
    placed_by = "SYSTEM"
    queue_status = "OEQ"


class OrderLineFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderLine

    order = factory.SubFactory(OrderFactory)
    line_number = factory.Sequence(lambda n: n + 1)
    product = factory.SubFactory(ProductFactory)
    unit_price = factory.LazyFunction(lambda: 29.99)
    net_price = factory.LazyFunction(lambda: 29.99)
    cost = factory.LazyFunction(lambda: 10.00)
    qty_ordered = 1
    qty_open = 1
    warehouse_code = "NY"
    extension = factory.LazyAttribute(lambda o: o.net_price * o.qty_ordered)


class OrderAuditFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderAudit

    order = factory.SubFactory(OrderFactory)
    operator = "SYSTEM"
    event_code = "OEQ"
