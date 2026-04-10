from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from apps.pricing.models import CustomerSpecialPrice, AffiliationPrice


PRICE_B_THRESHOLD = Decimal("200000")


@dataclass
class PriceResult:
    gross: Decimal
    discount_1: Decimal
    discount_2: Decimal
    net: Decimal
    source: str


def _resolve_price_level(price_level: str, product) -> Optional[Decimal]:
    """Resolve a price level code to a product price."""
    mapping = {
        "L": product.list_price,
        "A": product.price_a,
        "B": product.price_b,
        "X": product.dealer_price,
    }
    price = mapping.get(price_level)
    if price is not None and price > 0:
        return price
    return None


def calculate_price(
    customer, product, order_total: Optional[Decimal] = None
) -> PriceResult:
    """
    Five-tier pricing hierarchy matching legacy CALC.PRICE/CALC.PRICE2:

    1. Customer special pricing — highest priority
    2. Affiliation pricing — group-based
    3. Company code routing — F(A/B threshold), B(BEST/dealer), C(CLEO/dealer), W(Whitely/dealer)
    4. Customer price_level override — L/A/B/X
    5. Base product list price — fallback

    Kit products: price = sum of component prices (each component priced through this hierarchy).
    """
    # --- Kit pricing: sum component prices ---
    if product.is_kit:
        components = product.components.select_related("component_product").all()
        if components.exists():
            total_gross = Decimal("0")
            total_net = Decimal("0")
            for comp in components:
                comp_result = calculate_price(customer, comp.component_product, order_total)
                total_gross += comp_result.gross * comp.quantity_per_kit
                total_net += comp_result.net * comp.quantity_per_kit
            return PriceResult(
                gross=total_gross.quantize(Decimal("0.0001")),
                discount_1=Decimal("0"),
                discount_2=Decimal("0"),
                net=total_net.quantize(Decimal("0.0001")),
                source="kit_component_sum",
            )

    # --- Tier 1: Customer special pricing ---
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

    # --- Tier 2: Affiliation pricing ---
    if customer.affiliation:
        aff_price = AffiliationPrice.objects.filter(
            affiliation_code=customer.affiliation, product=product
        ).first()
        if aff_price:
            return PriceResult(
                gross=aff_price.gross_price,
                discount_1=aff_price.discount_1,
                discount_2=aff_price.discount_2,
                net=aff_price.net_price,
                source="affiliation",
            )

    # --- Tier 3: Company code routing ---
    company_code = getattr(customer, "company_code", "F") or "F"

    if company_code == "B":
        price = product.dealer_price if product.dealer_price else product.list_price
        return PriceResult(
            gross=price, discount_1=Decimal("0"), discount_2=Decimal("0"),
            net=price, source="company_code_B",
        )

    if company_code == "C":
        price = product.dealer_price if product.dealer_price else product.list_price
        return PriceResult(
            gross=price, discount_1=Decimal("0"), discount_2=Decimal("0"),
            net=price, source="company_code_C",
        )

    if company_code == "W":
        price = product.dealer_price if product.dealer_price else product.list_price
        return PriceResult(
            gross=price, discount_1=Decimal("0"), discount_2=Decimal("0"),
            net=price, source="company_code_W",
        )

    # Company code F (Fabrication - default)
    # --- Tier 4: Customer price_level override ---
    price_level = getattr(customer, "price_level", "") or ""
    if price_level:
        resolved = _resolve_price_level(price_level, product)
        if resolved is not None:
            return PriceResult(
                gross=resolved, discount_1=Decimal("0"), discount_2=Decimal("0"),
                net=resolved, source="price_level",
            )

    # Company code F: A/B threshold pricing
    if order_total is not None and order_total > PRICE_B_THRESHOLD:
        price = product.price_b if product.price_b else product.list_price
    else:
        price = product.price_a if product.price_a else product.list_price

    return PriceResult(
        gross=price, discount_1=Decimal("0"), discount_2=Decimal("0"),
        net=price, source="company_code_F",
    )
