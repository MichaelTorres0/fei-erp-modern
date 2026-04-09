# Minimal stub - full implementation in Task 10
from django.db import models


class Order(models.Model):
    order_number = models.CharField(max_length=20, unique=True)
    queue_status = models.CharField(max_length=10, default="OEQ")

    class Meta:
        ordering = ["-id"]


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="order_lines")
    warehouse_code = models.CharField(max_length=10, default="NY")
    qty_open = models.IntegerField(default=0)

    class Meta:
        ordering = ["id"]


class OrderAudit(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="audit_trail")
    timestamp = models.DateTimeField(auto_now_add=True)
    event_code = models.CharField(max_length=20)
