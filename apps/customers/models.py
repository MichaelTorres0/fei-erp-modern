from django.db import models


class Customer(models.Model):
    customer_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    attention = models.CharField(max_length=200, blank=True, default="")
    address_line_1 = models.CharField(max_length=200, blank=True, default="")
    address_line_2 = models.CharField(max_length=200, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=50, blank=True, default="")
    zip_code = models.CharField(max_length=20, blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    fax = models.CharField(max_length=50, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    terms_code = models.CharField(max_length=20, blank=True, default="")
    freight_terms = models.CharField(max_length=20, blank=True, default="")
    resale_number = models.CharField(max_length=50, blank=True, default="")
    affiliation = models.CharField(max_length=50, blank=True, default="")
    salesman = models.CharField(max_length=50, blank=True, default="")
    ar_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    open_order_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit_code = models.CharField(max_length=5, blank=True, default="")
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    over_90_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ytd_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_payment_date = models.DateField(null=True, blank=True)
    last_payment_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    territory_1 = models.CharField(max_length=20, blank=True, default="")
    territory_2 = models.CharField(max_length=20, blank=True, default="")
    territory_3 = models.CharField(max_length=20, blank=True, default="")
    backorder_flag = models.BooleanField(default=False)
    default_ship_via = models.CharField(max_length=50, blank=True, default="")
    special_discounts = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["customer_number"]
        verbose_name_plural = "customers"

    def __str__(self):
        return f"{self.customer_number} - {self.name}"

    @property
    def credit_exposure(self):
        return self.ar_balance + self.open_order_amount

    @property
    def available_credit(self):
        return self.credit_limit - self.credit_exposure


class CustomerAnnex(models.Model):
    customer = models.OneToOneField(
        Customer, on_delete=models.CASCADE, related_name="annex"
    )
    predictive_picking = models.BooleanField(default=False)
    split_processing = models.BooleanField(default=False)
    upc_exception = models.BooleanField(default=False)
    route_to_ptq = models.BooleanField(default=False)
    international_flag = models.BooleanField(default=False)
    web_email = models.EmailField(blank=True, default="")
    inventory_adjustment_pct = models.IntegerField(null=True, blank=True)
    auto_label = models.BooleanField(default=False)
    deferred_po = models.BooleanField(default=False)

    class Meta:
        verbose_name = "customer annex"
        verbose_name_plural = "customer annexes"

    def __str__(self):
        return f"Annex for {self.customer.customer_number}"
