import factory
from apps.customers.models import Customer, CustomerAnnex


class CustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Customer

    customer_number = factory.Sequence(lambda n: f"C{n:05d}")
    name = factory.Faker("company")
    address_line_1 = factory.Faker("street_address")
    city = factory.Faker("city")
    state = factory.Faker("state_abbr")
    zip_code = factory.Faker("zipcode")
    email = factory.Faker("company_email")
    terms_code = "N30"
    credit_code = ""
    credit_limit = factory.LazyFunction(lambda: 10000.00)
    ar_balance = factory.LazyFunction(lambda: 0.00)
    open_order_amount = factory.LazyFunction(lambda: 0.00)
    over_90_balance = factory.LazyFunction(lambda: 0.00)


class CustomerAnnexFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomerAnnex

    customer = factory.SubFactory(CustomerFactory)
