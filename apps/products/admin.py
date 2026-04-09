from django.contrib import admin
from .models import Product, ProductAnnex, KitComponent, WarehouseInventory


class ProductAnnexInline(admin.StackedInline):
    model = ProductAnnex
    can_delete = False
    verbose_name = "Dimensions & Shipping"


class KitComponentInline(admin.TabularInline):
    model = KitComponent
    fk_name = "parent_product"
    extra = 0
    autocomplete_fields = ["component_product"]
    verbose_name = "Kit Component"
    verbose_name_plural = "Kit Components (BOM)"


class WarehouseInventoryInline(admin.TabularInline):
    model = WarehouseInventory
    extra = 0
    verbose_name = "Warehouse Stock"
    verbose_name_plural = "Warehouse Stock Levels"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "product_number",
        "sku",
        "short_description",
        "list_price",
        "dealer_price",
        "category",
        "is_kit",
        "is_drop_ship",
        "is_obsolete",
    ]
    list_filter = ["category", "is_drop_ship", "is_kit", "is_obsolete", "is_active"]
    search_fields = ["product_number", "sku", "description"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ProductAnnexInline, KitComponentInline, WarehouseInventoryInline]

    fieldsets = (
        ("Identity", {
            "fields": ("product_number", "sku", "description", "category")
        }),
        ("Pricing", {
            "fields": ("list_price", "dealer_price", "price_a", "price_b", "standard_cost", "map_price")
        }),
        ("Classification", {
            "fields": ("is_drop_ship", "is_kit", "is_obsolete", "is_active")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Description")
    def short_description(self, obj):
        if len(obj.description) > 60:
            return obj.description[:60] + "..."
        return obj.description


@admin.register(WarehouseInventory)
class WarehouseInventoryAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "warehouse_code",
        "on_hand_qty",
        "mtd_units",
        "ytd_units",
        "last_activity_date",
    ]
    list_filter = ["warehouse_code"]
    search_fields = ["product__product_number", "product__description"]
