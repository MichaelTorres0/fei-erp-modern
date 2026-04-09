import pytest
from decimal import Decimal
from apps.customers.tests.factories import CustomerFactory
from apps.products.tests.factories import ProductFactory
from apps.pricing.tests.factories import CustomerSpecialPriceFactory
from apps.pricing.services import calculate_price

pytestmark = pytest.mark.django_db


class TestCalculatePrice:
    def test_customer_special_price_takes_priority(self):
        customer = CustomerFactory()
        product = ProductFactory(list_price=50.00)
        CustomerSpecialPriceFactory(
            customer=customer,
            product=product,
            gross_price=30.00,
            discount_1=10,
            net_price=27.00,
        )
        result = calculate_price(customer, product)
        assert result.gross == Decimal("30.00")
        assert result.net == Decimal("27.00")
        assert result.source == "customer_special"

    def test_falls_back_to_list_price(self):
        customer = CustomerFactory()
        product = ProductFactory(list_price=50.00)
        result = calculate_price(customer, product)
        assert result.gross == Decimal("50.0000")
        assert result.net == Decimal("50.0000")
        assert result.source == "base_product"

    def test_different_customers_different_prices(self):
        product = ProductFactory(list_price=50.00)
        cust_a = CustomerFactory()
        cust_b = CustomerFactory()
        CustomerSpecialPriceFactory(customer=cust_a, product=product, gross_price=30.00, net_price=30.00)
        result_a = calculate_price(cust_a, product)
        result_b = calculate_price(cust_b, product)
        assert result_a.gross == Decimal("30.00")
        assert result_b.gross == Decimal("50.0000")
