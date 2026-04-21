from django.db import models


class RMA(models.Model):
    """Return Merchandise Authorization.

    Lifecycle: OPEN (authorized) -> RECEIVED (goods back) -> CREDITED (credit memo issued)
    or CANCELLED.
    """

    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("RECEIVED", "Received"),
        ("CREDITED", "Credited"),
        ("CANCELLED", "Cancelled"),
    ]

    REASON_CHOICES = [
        ("DEFECTIVE", "Defective"),
        ("WRONG_ITEM", "Wrong Item Shipped"),
        ("CUSTOMER_ERROR", "Customer Error"),
        ("DAMAGE_TRANSIT", "Damaged in Transit"),
        ("OTHER", "Other"),
    ]

    rma_number = models.CharField(max_length=20, unique=True)
    invoice = models.ForeignKey(
        "invoicing.Invoice",
        on_delete=models.PROTECT,
        related_name="rmas",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="rmas",
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default="OTHER")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="OPEN")
    issued_date = models.DateField()
    received_date = models.DateField(null=True, blank=True)
    credited_date = models.DateField(null=True, blank=True)
    restock_to_warehouse = models.CharField(max_length=10, blank=True, default="")
    credit_memo_number = models.CharField(max_length=20, blank=True, default="")
    credit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True, default="")
    created_by = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "RMA"
        verbose_name_plural = "RMAs"

    def __str__(self):
        return f"{self.rma_number} ({self.customer.customer_number}) [{self.status}]"


class RMALine(models.Model):
    rma = models.ForeignKey(RMA, on_delete=models.CASCADE, related_name="lines")
    line_number = models.PositiveIntegerField()
    invoice_line = models.ForeignKey(
        "invoicing.InvoiceLine",
        on_delete=models.PROTECT,
        related_name="rma_lines",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="rma_lines",
    )
    qty_returned = models.IntegerField(default=0)
    qty_received = models.IntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    restock = models.BooleanField(
        default=True,
        help_text="When received, add qty back to warehouse inventory",
    )
    extension = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ["rma", "line_number"]
        ordering = ["line_number"]

    def __str__(self):
        return f"Line {self.line_number}: {self.product.product_number} x{self.qty_returned}"
