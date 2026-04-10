from django.db import models


class Product(models.Model):
    product_number = models.CharField(max_length=50, unique=True)
    sku = models.CharField(max_length=50, blank=True, default="")
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=50, blank=True, default="")
    list_price = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    dealer_price = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    price_a = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    price_b = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    standard_cost = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    map_price = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    price_code = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Manufacturers Direct price code (from PRICE.CODES)"
    )
    is_drop_ship = models.BooleanField(default=False)
    is_kit = models.BooleanField(default=False)
    is_obsolete = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product_number"]

    def __str__(self):
        return f"{self.product_number} - {self.description}"


class ProductAnnex(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="annex"
    )
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    length = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    depth = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    country_of_origin = models.CharField(max_length=10, blank=True, default="")
    upc_code = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        verbose_name = "product annex"
        verbose_name_plural = "product annexes"

    def __str__(self):
        return f"Annex for {self.product.product_number}"


class KitComponent(models.Model):
    parent_product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="components"
    )
    component_product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="used_in_kits"
    )
    quantity_per_kit = models.DecimalField(max_digits=10, decimal_places=2, default=1)

    class Meta:
        unique_together = ["parent_product", "component_product"]

    def __str__(self):
        return f"{self.parent_product.product_number} contains {self.quantity_per_kit}x {self.component_product.product_number}"


class WarehouseInventory(models.Model):
    WAREHOUSE_CHOICES = [
        ("NY", "New York"),
        ("FL", "Florida"),
        ("D", "Drop Ship"),
        ("OH", "Ohio"),
    ]

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="warehouse_inventory"
    )
    warehouse_code = models.CharField(max_length=10, choices=WAREHOUSE_CHOICES)
    on_hand_qty = models.IntegerField(default=0)
    standard_cost = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    mtd_units = models.IntegerField(default=0)
    mtd_dollars = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ytd_units = models.IntegerField(default=0)
    ytd_dollars = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_activity_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ["product", "warehouse_code"]
        verbose_name = "warehouse inventory"
        verbose_name_plural = "warehouse inventory"

    def __str__(self):
        return f"{self.product.product_number} @ {self.warehouse_code}: {self.on_hand_qty}"


class InventoryCommitment(models.Model):
    """
    Explicit per-order-line inventory allocation against a warehouse.
    Maps to legacy WAREHOUSE fields WH(18-20).
    """
    order_line = models.OneToOneField(
        "orders.OrderLine", on_delete=models.CASCADE, related_name="commitment"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="commitments"
    )
    warehouse_code = models.CharField(max_length=10)
    committed_qty = models.IntegerField(default=0, help_text="Quantity allocated from on-hand")
    backorder_qty = models.IntegerField(default=0, help_text="Quantity awaiting stock")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "inventory commitment"

    def __str__(self):
        return (
            f"{self.product.product_number} @ {self.warehouse_code}: "
            f"committed={self.committed_qty}, backorder={self.backorder_qty}"
        )
