import factory
from apps.pricing.models import CustomerSpecialPrice, CustomerPriceHistory, AffiliationPrice
from apps.customers.tests.factories import CustomerFactory
from apps.products.tests.factories import ProductFactory


class CustomerSpecialPriceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomerSpecialPrice

    customer = factory.SubFactory(CustomerFactory)
    product = factory.SubFactory(ProductFactory)
    gross_price = factory.LazyFunction(lambda: 25.00)
    net_price = factory.LazyFunction(lambda: 25.00)


class CustomerPriceHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomerPriceHistory

    customer = factory.SubFactory(CustomerFactory)
    product = factory.SubFactory(ProductFactory)


class AffiliationPriceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AffiliationPrice

    affiliation_code = "DIST"
    product = factory.SubFactory(ProductFactory)
    gross_price = factory.LazyFunction(lambda: 35.00)
    net_price = factory.LazyFunction(lambda: 35.00)
