import factory
from apps.products.models import Product, ProductAnnex, KitComponent, WarehouseInventory, InventoryCommitment


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    product_number = factory.Sequence(lambda n: f"P{n:05d}")
    sku = factory.LazyAttribute(lambda o: o.product_number)
    description = factory.Faker("sentence", nb_words=4)
    list_price = factory.LazyFunction(lambda: 29.99)
    dealer_price = factory.LazyFunction(lambda: 19.99)
    standard_cost = factory.LazyFunction(lambda: 10.00)
    category = "GENERAL"


class ProductAnnexFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductAnnex

    product = factory.SubFactory(ProductFactory)
    weight = factory.LazyFunction(lambda: 1.5)


class KitComponentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = KitComponent

    parent_product = factory.SubFactory(ProductFactory)
    component_product = factory.SubFactory(ProductFactory)
    quantity_per_kit = factory.LazyFunction(lambda: 1)


class WarehouseInventoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WarehouseInventory

    product = factory.SubFactory(ProductFactory)
    warehouse_code = "NY"
    on_hand_qty = 100
    standard_cost = factory.LazyFunction(lambda: 10.00)


class InventoryCommitmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InventoryCommitment

    order_line = factory.SubFactory("apps.orders.tests.factories.OrderLineFactory")
    product = factory.LazyAttribute(lambda o: o.order_line.product)
    warehouse_code = "NY"
    committed_qty = 10
    backorder_qty = 0
