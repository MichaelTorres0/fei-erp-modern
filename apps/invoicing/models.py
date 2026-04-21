from django.db import models


class Invoice(models.Model):
    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("PAID", "Paid"),
        ("VOID", "Void"),
    ]

    invoice_number = models.CharField(max_length=20, unique=True)
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="invoice",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="OPEN")
    terms = models.CharField(max_length=20, blank=True, default="")
    po_number = models.CharField(max_length=100, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-invoice_date", "-invoice_number"]

    def __str__(self):
        return f"{self.invoice_number} ({self.customer.customer_number}) [{self.status}]"

    @property
    def amount_due(self):
        return self.total - self.amount_paid


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    line_number = models.PositiveIntegerField()
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="invoice_lines",
    )
    description = models.CharField(max_length=255, blank=True, default="")
    qty_shipped = models.IntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    net_price = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    extension = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ["invoice", "line_number"]
        ordering = ["line_number"]

    def __str__(self):
        return f"Line {self.line_number}: {self.product.product_number} x{self.qty_shipped}"
