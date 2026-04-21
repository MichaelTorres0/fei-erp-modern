from django.db import models


class PickTicket(models.Model):
    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("PICKED", "Picked"),
        ("PACKED", "Packed"),
        ("SHIPPED", "Shipped"),
        ("CANCELLED", "Cancelled"),
    ]

    ticket_number = models.CharField(max_length=20, unique=True)
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="pick_tickets",
    )
    is_backorder = models.BooleanField(default=False)
    warehouse_code = models.CharField(max_length=10)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="OPEN")
    assigned_to = models.CharField(max_length=50, blank=True, default="")
    picked_at = models.DateTimeField(null=True, blank=True)
    packed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        label = "BO-" if self.is_backorder else ""
        return f"{label}{self.ticket_number} ({self.order.order_number}) [{self.status}]"

    @property
    def has_backorder_qty(self):
        return any(l.qty_ordered > l.qty_picked for l in self.lines.all())


class PickTicketLine(models.Model):
    pick_ticket = models.ForeignKey(PickTicket, on_delete=models.CASCADE, related_name="lines")
    line_number = models.PositiveIntegerField()
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="pick_lines",
    )
    warehouse_code = models.CharField(max_length=10)
    qty_ordered = models.IntegerField(default=0)
    qty_picked = models.IntegerField(default=0)

    class Meta:
        unique_together = ["pick_ticket", "line_number"]
        ordering = ["line_number"]

    def __str__(self):
        return f"Line {self.line_number}: {self.product.product_number} x{self.qty_ordered}"
