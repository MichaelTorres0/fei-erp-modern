from django.db import models


class CustomerSpecialPrice(models.Model):
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="special_prices"
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="special_prices"
    )
    gross_price = models.DecimalField(max_digits=10, decimal_places=4)
    discount_1 = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    discount_2 = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    net_price = models.DecimalField(max_digits=10, decimal_places=4)

    class Meta:
        unique_together = ["customer", "product"]
        verbose_name = "customer special price"

    def __str__(self):
        return f"{self.customer.customer_number} / {self.product.product_number}: ${self.net_price}"


class CustomerPriceHistory(models.Model):
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="price_history"
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="price_history"
    )
    last_gross_price = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    last_discount = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    last_net_price = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    last_order_date = models.DateField(null=True, blank=True)
    quote_gross_price = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    quote_net_price = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    quote_date = models.DateField(null=True, blank=True)
    quote_comment = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ["customer", "product"]
        verbose_name = "customer price history"
        verbose_name_plural = "customer price histories"

    def __str__(self):
        return f"Price history: {self.customer.customer_number} / {self.product.product_number}"
