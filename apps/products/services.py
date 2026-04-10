from django.db.models import Sum

from apps.products.models import WarehouseInventory
from apps.orders.constants import ACTIVE_QUEUE_STATUSES


def get_availability(product, warehouse_code=None):
    """
    Calculate available inventory for a product across warehouses.

    Returns dict keyed by warehouse_code:
        {"NY": {"on_hand": 100, "committed": 30, "available": 70}, ...}
    """
    from apps.orders.models import OrderLine

    qs = WarehouseInventory.objects.filter(product=product)
    if warehouse_code:
        qs = qs.filter(warehouse_code=warehouse_code)

    result = {}
    for inv in qs:
        committed = OrderLine.objects.filter(
            product=product,
            warehouse_code=inv.warehouse_code,
            order__queue_status__in=ACTIVE_QUEUE_STATUSES,
        ).aggregate(total=Sum("qty_open"))["total"] or 0

        result[inv.warehouse_code] = {
            "on_hand": inv.on_hand_qty,
            "committed": committed,
            "available": inv.on_hand_qty - committed,
        }

    return result


def get_kit_availability(product, warehouse_code, _seen=None):
    """
    For kit products, availability = min(component_available / qty_per_kit)
    across all components. Supports nested kits with circular reference protection.
    Returns int (whole kits available) or None if not a kit.
    """
    if not product.is_kit:
        return None

    # Circular reference protection
    if _seen is None:
        _seen = set()
    if product.pk in _seen:
        return 0  # circular reference - treat as 0 availability
    _seen.add(product.pk)

    components = product.components.select_related("component_product").all()
    if not components:
        return 0

    min_kits = None
    for comp in components:
        if comp.component_product.is_kit:
            # Nested kit - recursively get its availability
            nested_avail = get_kit_availability(comp.component_product, warehouse_code, _seen)
            if nested_avail is None or nested_avail == 0:
                return 0
            kits_from_component = int(nested_avail / comp.quantity_per_kit)
        else:
            # Regular component - check warehouse inventory
            comp_availability = get_availability(comp.component_product, warehouse_code)
            if warehouse_code not in comp_availability:
                return 0
            available = comp_availability[warehouse_code]["available"]
            kits_from_component = int(available / comp.quantity_per_kit)

        if min_kits is None or kits_from_component < min_kits:
            min_kits = kits_from_component

    return min_kits if min_kits is not None else 0
