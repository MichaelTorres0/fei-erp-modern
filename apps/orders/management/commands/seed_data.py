from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from apps.customers.models import Customer, CustomerAnnex
from apps.products.models import Product, ProductAnnex, KitComponent, WarehouseInventory
from apps.orders.models import Order, OrderLine, OrderAudit
from apps.pricing.models import CustomerSpecialPrice
from apps.orders.services import create_order


class Command(BaseCommand):
    help = "Seed database with representative test data for PoC demo"

    def handle(self, *args, **options):
        self.stdout.write("Seeding test data...")

        # --- Customers ---
        customers_data = [
            {"customer_number": "F10001", "name": "Acme Distribution", "city": "New York", "state": "NY", "zip_code": "10001", "credit_code": "A", "credit_limit": 50000, "ar_balance": 12000, "terms_code": "N30", "affiliation": "DIST", "salesman": "JSmith"},
            {"customer_number": "F10002", "name": "Beta Medical Supply", "city": "Chicago", "state": "IL", "zip_code": "60601", "credit_code": "", "credit_limit": 25000, "ar_balance": 8000, "open_order_amount": 3000, "terms_code": "N30", "affiliation": "MED"},
            {"customer_number": "F10003", "name": "Coastal Healthcare", "city": "Miami", "state": "FL", "zip_code": "33101", "credit_code": "", "credit_limit": 15000, "ar_balance": 14000, "over_90_balance": 2000, "terms_code": "N30"},
            {"customer_number": "F10004", "name": "Direct Supply Inc", "city": "Milwaukee", "state": "WI", "zip_code": "53201", "credit_code": "A", "credit_limit": 100000, "terms_code": "N30", "affiliation": "DIST"},
            {"customer_number": "F10005", "name": "Eagle Products", "city": "Dallas", "state": "TX", "zip_code": "75201", "credit_code": "D", "credit_limit": 5000, "terms_code": "COD"},
            {"customer_number": "F14746", "name": "Direct Supply National", "city": "Milwaukee", "state": "WI", "zip_code": "53202", "credit_code": "A", "credit_limit": 200000, "terms_code": "N30", "affiliation": "DS"},
            {"customer_number": "F31906", "name": "Walmart.com", "city": "Bentonville", "state": "AR", "zip_code": "72712", "credit_code": "A", "credit_limit": 500000, "terms_code": "N30", "affiliation": "WMT"},
        ]
        for data in customers_data:
            cust, created = Customer.objects.get_or_create(
                customer_number=data.pop("customer_number"), defaults=data
            )
            CustomerAnnex.objects.get_or_create(customer=cust)
            if created:
                self.stdout.write(f"  Created customer: {cust}")

        # Walmart annex flags
        wmt = Customer.objects.get(customer_number="F31906")
        wmt_annex = wmt.annex
        wmt_annex.split_processing = True
        wmt_annex.save()

        # --- Products ---
        products_data = [
            {"product_number": "FEI-1001", "sku": "FEI-1001", "description": "Standard Bed Rail - Chrome", "list_price": 89.99, "dealer_price": 64.99, "standard_cost": 32.00, "category": "BED-RAILS"},
            {"product_number": "FEI-1002", "sku": "FEI-1002", "description": "Standard Bed Rail - White", "list_price": 89.99, "dealer_price": 64.99, "standard_cost": 32.00, "category": "BED-RAILS"},
            {"product_number": "FEI-2001", "sku": "FEI-2001", "description": "Wheelchair Cushion - Standard", "list_price": 45.99, "dealer_price": 29.99, "standard_cost": 15.00, "category": "CUSHIONS"},
            {"product_number": "FEI-2002", "sku": "FEI-2002", "description": "Wheelchair Cushion - Gel", "list_price": 79.99, "dealer_price": 54.99, "standard_cost": 28.00, "category": "CUSHIONS"},
            {"product_number": "FEI-3001", "sku": "FEI-3001", "description": "Exercise Band - Light (Yellow)", "list_price": 12.99, "dealer_price": 7.99, "standard_cost": 3.50, "category": "EXERCISE"},
            {"product_number": "FEI-3002", "sku": "FEI-3002", "description": "Exercise Band - Medium (Red)", "list_price": 12.99, "dealer_price": 7.99, "standard_cost": 3.50, "category": "EXERCISE"},
            {"product_number": "FEI-3003", "sku": "FEI-3003", "description": "Exercise Band - Heavy (Blue)", "list_price": 14.99, "dealer_price": 9.99, "standard_cost": 4.00, "category": "EXERCISE"},
            {"product_number": "KIT-3000", "sku": "KIT-3000", "description": "Exercise Band 3-Pack (Light/Med/Heavy)", "list_price": 34.99, "dealer_price": 22.99, "standard_cost": 11.00, "category": "EXERCISE", "is_kit": True},
            {"product_number": "FEI-5001", "sku": "FEI-5001", "description": "Hot/Cold Pack - Standard", "list_price": 8.99, "dealer_price": 5.49, "standard_cost": 2.25, "category": "THERAPY"},
            {"product_number": "FEI-DS01", "sku": "FEI-DS01", "description": "Premium Lift Chair (Drop Ship)", "list_price": 899.99, "dealer_price": 599.99, "standard_cost": 450.00, "category": "SEATING", "is_drop_ship": True},
        ]
        for data in products_data:
            prod, created = Product.objects.get_or_create(
                product_number=data.pop("product_number"), defaults=data
            )
            ProductAnnex.objects.get_or_create(product=prod, defaults={"weight": Decimal("2.5")})
            if created:
                self.stdout.write(f"  Created product: {prod}")

        # Kit components for Exercise Band 3-Pack
        kit = Product.objects.get(product_number="KIT-3000")
        for comp_pn, qty in [("FEI-3001", 1), ("FEI-3002", 1), ("FEI-3003", 1)]:
            comp = Product.objects.get(product_number=comp_pn)
            KitComponent.objects.get_or_create(
                parent_product=kit, component_product=comp,
                defaults={"quantity_per_kit": qty},
            )

        # --- Warehouse Inventory ---
        for prod in Product.objects.filter(is_drop_ship=False):
            WarehouseInventory.objects.get_or_create(
                product=prod, warehouse_code="NY",
                defaults={"on_hand_qty": 150, "standard_cost": prod.standard_cost},
            )
            WarehouseInventory.objects.get_or_create(
                product=prod, warehouse_code="FL",
                defaults={"on_hand_qty": 75, "standard_cost": prod.standard_cost},
            )

        # Drop ship product gets D warehouse
        ds_prod = Product.objects.get(product_number="FEI-DS01")
        WarehouseInventory.objects.get_or_create(
            product=ds_prod, warehouse_code="D",
            defaults={"on_hand_qty": 0, "standard_cost": ds_prod.standard_cost},
        )

        # --- Customer Special Pricing ---
        acme = Customer.objects.get(customer_number="F10001")
        bed_rail = Product.objects.get(product_number="FEI-1001")
        CustomerSpecialPrice.objects.get_or_create(
            customer=acme, product=bed_rail,
            defaults={"gross_price": 72.00, "discount_1": 10, "net_price": 64.80},
        )

        ds_nat = Customer.objects.get(customer_number="F14746")
        for pn in ["FEI-2001", "FEI-2002"]:
            prod = Product.objects.get(product_number=pn)
            CustomerSpecialPrice.objects.get_or_create(
                customer=ds_nat, product=prod,
                defaults={"gross_price": prod.dealer_price, "net_price": prod.dealer_price * Decimal("0.9")},
            )

        # --- Sample Orders ---
        self.stdout.write("  Creating sample orders...")
        acme = Customer.objects.get(customer_number="F10001")
        create_order(
            customer=acme,
            lines=[
                {"product_id": Product.objects.get(product_number="FEI-1001").pk, "qty_ordered": 10, "warehouse_code": "NY"},
                {"product_id": Product.objects.get(product_number="FEI-2001").pk, "qty_ordered": 5, "warehouse_code": "NY"},
            ],
            placed_by="SEED",
            po_number="ACME-PO-2026-001",
        )

        beta = Customer.objects.get(customer_number="F10002")
        create_order(
            customer=beta,
            lines=[
                {"product_id": Product.objects.get(product_number="FEI-3001").pk, "qty_ordered": 100, "warehouse_code": "NY"},
            ],
            placed_by="SEED",
            po_number="BETA-PO-100",
        )

        # Credit hold order
        coastal = Customer.objects.get(customer_number="F10003")
        create_order(
            customer=coastal,
            lines=[
                {"product_id": Product.objects.get(product_number="FEI-5001").pk, "qty_ordered": 50, "warehouse_code": "FL"},
            ],
            placed_by="SEED",
        )

        # Auto-hold order (credit code D)
        eagle = Customer.objects.get(customer_number="F10005")
        create_order(
            customer=eagle,
            lines=[
                {"product_id": Product.objects.get(product_number="FEI-1002").pk, "qty_ordered": 2, "warehouse_code": "NY"},
            ],
            placed_by="SEED",
            po_number="EAG-001",
        )

        self.stdout.write(self.style.SUCCESS("Test data seeded successfully!"))
        self.stdout.write(f"  Customers: {Customer.objects.count()}")
        self.stdout.write(f"  Products: {Product.objects.count()}")
        self.stdout.write(f"  Warehouse records: {WarehouseInventory.objects.count()}")
        self.stdout.write(f"  Orders: {Order.objects.count()}")
        self.stdout.write(f"  Special prices: {CustomerSpecialPrice.objects.count()}")
