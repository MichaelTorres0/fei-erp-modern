from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(url="/dashboard/", permanent=False)),
    path("dashboard/", include("apps.dashboard.urls")),
    path("admin/", admin.site.urls),
    path("api/v1/customers/", include("apps.customers.urls")),
    path("api/v1/products/", include("apps.products.urls")),
    path("api/v1/orders/", include("apps.orders.urls")),
    path("api/v1/pricing/", include("apps.pricing.urls")),
    path("api/v1/invoices/", include("apps.invoicing.urls")),
    path("api/v1/pick-tickets/", include("apps.fulfillment.urls")),
]
