import pytest
from decimal import Decimal
from apps.customers.tests.factories import CustomerFactory
from apps.products.tests.factories import ProductFactory
from apps.pricing.tests.factories import (
    CustomerSpecialPriceFactory,
    AffiliationPriceFactory,
)
from apps.pricing.services import calculate_price

pytestmark = pytest.mark.django_db


class TestTier1CustomerSpecial:
    def test_customer_special_price_takes_priority(self):
        customer = CustomerFactory()
        product = ProductFactory(list_price=50.00)
        CustomerSpecialPriceFactory(
            customer=customer, product=product,
            gross_price=30.00, discount_1=10, net_price=27.00,
        )
        result = calculate_price(customer, product)
        assert result.gross == Decimal("30.00")
        assert result.net == Decimal("27.00")
        assert result.source == "customer_special"

    def test_special_overrides_affiliation(self):
        customer = CustomerFactory(affiliation="DIST")
        product = ProductFactory(list_price=50.00)
        CustomerSpecialPriceFactory(
            customer=customer, product=product,
            gross_price=25.00, net_price=25.00,
        )
        AffiliationPriceFactory(
            affiliation_code="DIST", product=product,
            gross_price=35.00, net_price=35.00,
        )
        result = calculate_price(customer, product)
        assert result.source == "customer_special"
        assert result.gross == Decimal("25.00")


class TestTier2Affiliation:
    def test_affiliation_price_used(self):
        customer = CustomerFactory(affiliation="DIST")
        product = ProductFactory(list_price=50.00)
        AffiliationPriceFactory(
            affiliation_code="DIST", product=product,
            gross_price=35.00, discount_1=5, net_price=33.25,
        )
        result = calculate_price(customer, product)
        assert result.gross == Decimal("35.00")
        assert result.net == Decimal("33.25")
        assert result.source == "affiliation"

    def test_affiliation_not_matched_falls_through(self):
        customer = CustomerFactory(affiliation="DIST")
        product = ProductFactory(list_price=50.00)
        result = calculate_price(customer, product)
        assert result.source != "affiliation"

    def test_no_affiliation_skips_tier(self):
        customer = CustomerFactory(affiliation="")
        product = ProductFactory(list_price=50.00)
        result = calculate_price(customer, product)
        assert result.source != "affiliation"


class TestTier3CompanyCodeF:
    def test_default_uses_price_a(self):
        customer = CustomerFactory(company_code="F")
        product = ProductFactory(list_price=50.00, price_a=40.00, price_b=35.00)
        result = calculate_price(customer, product)
        assert result.gross == Decimal("40.0000")
        assert result.source == "company_code_F"

    def test_high_total_uses_price_b(self):
        customer = CustomerFactory(company_code="F")
        product = ProductFactory(list_price=50.00, price_a=40.00, price_b=35.00)
        result = calculate_price(customer, product, order_total=Decimal("250000"))
        assert result.gross == Decimal("35.0000")
        assert result.source == "company_code_F"

    def test_price_a_null_falls_to_list(self):
        customer = CustomerFactory(company_code="F")
        product = ProductFactory(list_price=50.00, price_a=None, price_b=None)
        result = calculate_price(customer, product)
        assert result.gross == Decimal("50.0000")
        assert result.source == "company_code_F"


class TestTier3CompanyCodeB:
    def test_best_uses_dealer_price(self):
        customer = CustomerFactory(company_code="B")
        product = ProductFactory(list_price=50.00, dealer_price=30.00)
        result = calculate_price(customer, product)
        assert result.gross == Decimal("30.0000")
        assert result.source == "company_code_B"


class TestTier3CompanyCodeC:
    def test_cleo_uses_dealer_price(self):
        customer = CustomerFactory(company_code="C")
        product = ProductFactory(list_price=50.00, dealer_price=30.00)
        result = calculate_price(customer, product)
        assert result.gross == Decimal("30.0000")
        assert result.source == "company_code_C"


class TestTier3CompanyCodeW:
    def test_whitely_uses_dealer_price(self):
        customer = CustomerFactory(company_code="W")
        product = ProductFactory(list_price=50.00, dealer_price=30.00)
        result = calculate_price(customer, product)
        assert result.gross == Decimal("30.0000")
        assert result.source == "company_code_W"


class TestTier4PriceLevel:
    def test_price_level_L_uses_list(self):
        customer = CustomerFactory(company_code="F", price_level="L")
        product = ProductFactory(list_price=50.00, price_a=40.00)
        result = calculate_price(customer, product)
        assert result.gross == Decimal("50.0000")
        assert result.source == "price_level"

    def test_price_level_A_uses_price_a(self):
        customer = CustomerFactory(company_code="F", price_level="A")
        product = ProductFactory(list_price=50.00, price_a=40.00)
        result = calculate_price(customer, product)
        assert result.gross == Decimal("40.0000")
        assert result.source == "price_level"

    def test_price_level_B_uses_price_b(self):
        customer = CustomerFactory(company_code="F", price_level="B")
        product = ProductFactory(list_price=50.00, price_b=35.00)
        result = calculate_price(customer, product)
        assert result.gross == Decimal("35.0000")
        assert result.source == "price_level"

    def test_price_level_X_uses_dealer(self):
        customer = CustomerFactory(company_code="F", price_level="X")
        product = ProductFactory(list_price=50.00, dealer_price=30.00)
        result = calculate_price(customer, product)
        assert result.gross == Decimal("30.0000")
        assert result.source == "price_level"


class TestTier5BaseProduct:
    def test_falls_back_to_list_price(self):
        customer = CustomerFactory()
        product = ProductFactory(list_price=50.00)
        result = calculate_price(customer, product)
        assert result.gross == Decimal("50.0000")
        assert result.net == Decimal("50.0000")
        assert result.source == "company_code_F"

    def test_different_customers_different_prices(self):
        product = ProductFactory(list_price=50.00)
        cust_a = CustomerFactory()
        cust_b = CustomerFactory()
        CustomerSpecialPriceFactory(
            customer=cust_a, product=product,
            gross_price=30.00, net_price=30.00,
        )
        result_a = calculate_price(cust_a, product)
        result_b = calculate_price(cust_b, product)
        assert result_a.gross == Decimal("30.00")
        assert result_b.gross == Decimal("50.0000")


class TestKitPricing:
    def test_kit_prices_by_components(self):
        from apps.products.tests.factories import KitComponentFactory
        customer = CustomerFactory()
        kit = ProductFactory(is_kit=True, list_price=100.00)
        comp_a = ProductFactory(list_price=30.00)
        comp_b = ProductFactory(list_price=20.00)
        KitComponentFactory(parent_product=kit, component_product=comp_a, quantity_per_kit=2)
        KitComponentFactory(parent_product=kit, component_product=comp_b, quantity_per_kit=1)
        result = calculate_price(customer, kit)
        assert result.gross == Decimal("80.0000")
        assert result.source == "kit_component_sum"

    def test_kit_with_special_component_pricing(self):
        from apps.products.tests.factories import KitComponentFactory
        customer = CustomerFactory()
        kit = ProductFactory(is_kit=True, list_price=100.00)
        comp_a = ProductFactory(list_price=30.00)
        KitComponentFactory(parent_product=kit, component_product=comp_a, quantity_per_kit=2)
        CustomerSpecialPriceFactory(
            customer=customer, product=comp_a,
            gross_price=20.00, net_price=18.00,
        )
        result = calculate_price(customer, kit)
        assert result.net == Decimal("36.0000")
        assert result.source == "kit_component_sum"

    def test_non_kit_ignores_kit_pricing(self):
        customer = CustomerFactory()
        product = ProductFactory(is_kit=False, list_price=50.00)
        result = calculate_price(customer, product)
        assert result.source != "kit_component_sum"
