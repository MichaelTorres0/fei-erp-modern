from dataclasses import dataclass
from decimal import Decimal

from apps.pricing.models import CustomerSpecialPrice


@dataclass
class PriceResult:
    gross: Decimal
    discount_1: Decimal
    discount_2: Decimal
    net: Decimal
    source: str  # "customer_special" or "base_product"


def calculate_price(customer, product) -> PriceResult:
    """
    Two-tier pricing lookup matching legacy CALC.PRICE2 priority logic:
    1. Customer special pricing (STD.ORDERS equivalent) - highest priority
    2. Base product list price - fallback
    """
    # Priority 1: Customer special pricing
    special = CustomerSpecialPrice.objects.filter(
        customer=customer, product=product
    ).first()
    if special:
        return PriceResult(
            gross=special.gross_price,
            discount_1=special.discount_1,
            discount_2=special.discount_2,
            net=special.net_price,
            source="customer_special",
        )

    # Priority 2: Base product pricing
    return PriceResult(
        gross=product.list_price,
        discount_1=Decimal("0"),
        discount_2=Decimal("0"),
        net=product.list_price,
        source="base_product",
    )
