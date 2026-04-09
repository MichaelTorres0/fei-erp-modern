import pytest
from apps.customers.tests.factories import CustomerFactory, CustomerAnnexFactory

pytestmark = pytest.mark.django_db


class TestCustomer:
    def test_create_customer(self):
        customer = CustomerFactory(customer_number="F10001", name="Acme Corp")
        assert customer.customer_number == "F10001"
        assert customer.name == "Acme Corp"
        assert customer.is_active is True

    def test_customer_str(self):
        customer = CustomerFactory(customer_number="F10001", name="Acme Corp")
        assert str(customer) == "F10001 - Acme Corp"

    def test_customer_number_unique(self):
        CustomerFactory(customer_number="F10001")
        with pytest.raises(Exception):
            CustomerFactory(customer_number="F10001")

    def test_credit_exposure(self):
        customer = CustomerFactory(
            ar_balance=5000.00,
            open_order_amount=3000.00,
        )
        assert customer.credit_exposure == 8000.00

    def test_available_credit(self):
        customer = CustomerFactory(
            credit_limit=10000.00,
            ar_balance=5000.00,
            open_order_amount=3000.00,
        )
        assert customer.available_credit == 2000.00


class TestCustomerAnnex:
    def test_create_annex(self):
        annex = CustomerAnnexFactory(
            customer__customer_number="F10001",
            predictive_picking=True,
        )
        assert annex.customer.customer_number == "F10001"
        assert annex.predictive_picking is True

    def test_annex_one_to_one(self):
        annex = CustomerAnnexFactory()
        assert annex.customer.annex == annex
