import pytest
from apps.pricing.tests.factories import CustomerSpecialPriceFactory

pytestmark = pytest.mark.django_db


class TestCustomerSpecialPrice:
    def test_create_special_price(self):
        sp = CustomerSpecialPriceFactory(gross_price=25.00, net_price=22.50, discount_1=10)
        assert sp.gross_price == 25.00
        assert sp.net_price == 22.50
        assert sp.discount_1 == 10

    def test_unique_customer_product(self):
        sp = CustomerSpecialPriceFactory()
        with pytest.raises(Exception):
            CustomerSpecialPriceFactory(customer=sp.customer, product=sp.product)
