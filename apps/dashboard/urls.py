from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("pipeline/", views.order_pipeline, name="pipeline"),
    path("inventory/", views.inventory_overview, name="inventory"),
    path("ar-aging/", views.ar_aging, name="ar_aging"),
]
