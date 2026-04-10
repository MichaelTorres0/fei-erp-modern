import pytest
from apps.pricing.tests.factories import CustomerSpecialPriceFactory, AffiliationPriceFactory

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


class TestAffiliationPrice:
    def test_create_affiliation_price(self):
        ap = AffiliationPriceFactory(
            affiliation_code="DIST",
            gross_price=35.00,
            net_price=31.50,
        )
        assert ap.affiliation_code == "DIST"
        assert ap.net_price == 31.50

    def test_unique_affiliation_product(self):
        ap = AffiliationPriceFactory(affiliation_code="DIST")
        with pytest.raises(Exception):
            AffiliationPriceFactory(
                affiliation_code="DIST", product=ap.product
            )
