from django.db import models


class Order(models.Model):
    QUEUE_CHOICES = [
        ("OEQ", "Order Entry"),
        ("MGQ", "Management"),
        ("CHQ", "Credit Hold"),
        ("PTQ", "Pick Ticket"),
        ("IVQ", "Invoice"),
    ]

    order_number = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.PROTECT, related_name="orders"
    )
    is_drop_ship = models.BooleanField(default=False)
    ship_to_line_1 = models.CharField(max_length=200, blank=True, default="")
    ship_to_line_2 = models.CharField(max_length=200, blank=True, default="")
    ship_to_city = models.CharField(max_length=100, blank=True, default="")
    ship_to_state = models.CharField(max_length=50, blank=True, default="")
    ship_to_zip = models.CharField(max_length=20, blank=True, default="")
    ship_to_country = models.CharField(max_length=100, blank=True, default="")
    entry_date = models.DateField(auto_now_add=True)
    order_date = models.DateField()
    required_date = models.DateField(null=True, blank=True)
    po_number = models.CharField(max_length=100, blank=True, default="")
    placed_by = models.CharField(max_length=50, default="")
    email = models.EmailField(blank=True, default="")
    ship_via = models.CharField(max_length=50, blank=True, default="")
    freight_terms = models.CharField(max_length=20, blank=True, default="")
    terms = models.CharField(max_length=20, blank=True, default="")
    salesman = models.CharField(max_length=50, blank=True, default="")
    affiliation = models.CharField(max_length=50, blank=True, default="")
    territory_1 = models.CharField(max_length=20, blank=True, default="")
    territory_2 = models.CharField(max_length=20, blank=True, default="")
    territory_3 = models.CharField(max_length=20, blank=True, default="")
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    special_instructions = models.TextField(blank=True, default="")
    special_discounts = models.CharField(max_length=200, blank=True, default="")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    queue_status = models.CharField(max_length=10, choices=QUEUE_CHOICES, default="OEQ")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order_number} ({self.customer.customer_number}) [{self.queue_status}]"


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    line_number = models.PositiveIntegerField()
    product = models.ForeignKey(
        "products.Product", on_delete=models.PROTECT, related_name="order_lines"
    )
    unit_price = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    discount_1 = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    discount_2 = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    net_price = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    qty_ordered = models.IntegerField(default=0)
    qty_open = models.IntegerField(default=0)
    qty_shipped = models.IntegerField(default=0)
    backorder_qty = models.IntegerField(default=0)
    warehouse_code = models.CharField(max_length=10, default="NY")
    extension = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ["order", "line_number"]
        ordering = ["line_number"]

    def __str__(self):
        return f"Line {self.line_number}: {self.product.product_number} x{self.qty_ordered}"


class OrderAudit(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="audit_trail")
    timestamp = models.DateTimeField(auto_now_add=True)
    operator = models.CharField(max_length=50)
    event_code = models.CharField(max_length=20)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.order.order_number} - {self.event_code} @ {self.timestamp}"
