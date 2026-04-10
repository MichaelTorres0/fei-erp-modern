from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from apps.customers.models import Customer, CustomerAnnex
from apps.products.models import Product, ProductAnnex, KitComponent, WarehouseInventory
from apps.orders.models import Order, OrderLine, OrderAudit
from apps.pricing.models import CustomerSpecialPrice
from apps.orders.services import create_order, transition_queue


class Command(BaseCommand):
    help = "Seed database with representative test data for PoC demo (~20 customers, ~50 products, ~30 orders)"

    def handle(self, *args, **options):
        self.stdout.write("Seeding test data...")

        # -----------------------------------------------------------------------
        # CUSTOMERS (~20)
        # -----------------------------------------------------------------------
        customers_data = [
            # Original 7 customers
            {
                "customer_number": "F10001", "name": "Acme Distribution",
                "city": "New York", "state": "NY", "zip_code": "10001",
                "credit_code": "A", "credit_limit": 50000, "ar_balance": 12000,
                "terms_code": "N30", "affiliation": "DIST", "salesman": "JSmith",
            },
            {
                "customer_number": "F10002", "name": "Beta Medical Supply",
                "city": "Chicago", "state": "IL", "zip_code": "60601",
                "credit_code": "", "credit_limit": 25000, "ar_balance": 8000,
                "open_order_amount": 3000, "terms_code": "N30", "affiliation": "MED",
            },
            {
                "customer_number": "F10003", "name": "Coastal Healthcare",
                "city": "Miami", "state": "FL", "zip_code": "33101",
                "credit_code": "", "credit_limit": 15000, "ar_balance": 14000,
                "over_90_balance": 2000, "terms_code": "N30",
            },
            {
                "customer_number": "F10004", "name": "Direct Supply Inc",
                "city": "Milwaukee", "state": "WI", "zip_code": "53201",
                "credit_code": "A", "credit_limit": 100000, "terms_code": "N30",
                "affiliation": "DIST",
            },
            {
                "customer_number": "F10005", "name": "Eagle Products",
                "city": "Dallas", "state": "TX", "zip_code": "75201",
                "credit_code": "D", "credit_limit": 5000, "terms_code": "COD",
            },
            {
                "customer_number": "F14746", "name": "Direct Supply National",
                "city": "Milwaukee", "state": "WI", "zip_code": "53202",
                "credit_code": "A", "credit_limit": 200000, "terms_code": "N30",
                "affiliation": "DS",
            },
            {
                "customer_number": "F31906", "name": "Walmart.com",
                "city": "Bentonville", "state": "AR", "zip_code": "72712",
                "credit_code": "A", "credit_limit": 500000, "terms_code": "N30",
                "affiliation": "WMT",
            },
            # New customers (13 more)
            {
                "customer_number": "F10006", "name": "Genesis Home Health",
                "city": "Phoenix", "state": "AZ", "zip_code": "85001",
                "credit_code": "A", "credit_limit": 75000, "ar_balance": 22000,
                "terms_code": "N30", "affiliation": "MED", "salesman": "RJones",
            },
            {
                "customer_number": "F10007", "name": "Heartland Medical LLC",
                "city": "Kansas City", "state": "MO", "zip_code": "64101",
                "credit_code": "", "credit_limit": 30000, "ar_balance": 18000,
                "over_90_balance": 5000, "terms_code": "N30", "affiliation": "MED",
            },
            {
                "customer_number": "F10008", "name": "Northwest Rehab Supply",
                "city": "Seattle", "state": "WA", "zip_code": "98101",
                "credit_code": "A", "credit_limit": 40000, "ar_balance": 9500,
                "terms_code": "N30", "affiliation": "DIST", "salesman": "BDavis",
            },
            {
                "customer_number": "F10009", "name": "Southern Comfort Medical",
                "city": "Atlanta", "state": "GA", "zip_code": "30301",
                "credit_code": "H", "credit_limit": 10000, "ar_balance": 3200,
                "terms_code": "COD",
            },
            {
                "customer_number": "F10010", "name": "Valley View Pharmacy",
                "city": "Sacramento", "state": "CA", "zip_code": "95814",
                "credit_code": "", "credit_limit": 20000, "ar_balance": 5500,
                "open_order_amount": 1200, "terms_code": "N30", "affiliation": "MED",
            },
            {
                "customer_number": "F10011", "name": "Great Lakes Distribution",
                "city": "Cleveland", "state": "OH", "zip_code": "44101",
                "credit_code": "A", "credit_limit": 85000, "ar_balance": 31000,
                "terms_code": "N30", "affiliation": "DIST", "salesman": "JSmith",
            },
            {
                "customer_number": "F10012", "name": "Pinnacle Health Systems",
                "city": "Denver", "state": "CO", "zip_code": "80201",
                "credit_code": "A", "credit_limit": 60000, "ar_balance": 14500,
                "terms_code": "N30", "affiliation": "MED", "salesman": "RJones",
            },
            {
                "customer_number": "F10013", "name": "Sunrise Senior Living",
                "city": "Orlando", "state": "FL", "zip_code": "32801",
                "credit_code": "", "credit_limit": 25000, "ar_balance": 7800,
                "terms_code": "N30",
            },
            {
                "customer_number": "F10014", "name": "Capitol Medical Supply",
                "city": "Washington", "state": "DC", "zip_code": "20001",
                "credit_code": "A", "credit_limit": 90000, "ar_balance": 28000,
                "terms_code": "N30", "affiliation": "GOV", "salesman": "BDavis",
            },
            {
                "customer_number": "F10015", "name": "University Health Services",
                "city": "Ann Arbor", "state": "MI", "zip_code": "48101",
                "credit_code": "A", "credit_limit": 45000, "ar_balance": 11000,
                "terms_code": "N30", "affiliation": "EDU",
            },
            {
                "customer_number": "F10016", "name": "Cascade Care Products",
                "city": "Portland", "state": "OR", "zip_code": "97201",
                "credit_code": "C", "credit_limit": 8000, "ar_balance": 2100,
                "terms_code": "COD",
            },
            {
                "customer_number": "F10017", "name": "Blue Ridge Home Medical",
                "city": "Charlotte", "state": "NC", "zip_code": "28201",
                "credit_code": "", "credit_limit": 18000, "ar_balance": 16500,
                "over_90_balance": 3500, "terms_code": "N30", "affiliation": "MED",
            },
            {
                "customer_number": "F10018", "name": "Metro Therapy Associates",
                "city": "Boston", "state": "MA", "zip_code": "02101",
                "credit_code": "A", "credit_limit": 35000, "ar_balance": 8900,
                "terms_code": "N30", "affiliation": "MED", "salesman": "JSmith",
            },
            {
                "customer_number": "F10019", "name": "Desert Sun Medical",
                "city": "Las Vegas", "state": "NV", "zip_code": "89101",
                "credit_code": "", "credit_limit": 12000, "ar_balance": 4200,
                "terms_code": "N30",
            },
            {
                "customer_number": "F10020", "name": "Rocky Mountain Rehab",
                "city": "Salt Lake City", "state": "UT", "zip_code": "84101",
                "credit_code": "D", "credit_limit": 3000, "ar_balance": 900,
                "terms_code": "COD",
            },
        ]
        for data in customers_data:
            cust, created = Customer.objects.get_or_create(
                customer_number=data.pop("customer_number"), defaults=data
            )
            CustomerAnnex.objects.get_or_create(customer=cust)
            if created:
                self.stdout.write(f"  Created customer: {cust}")

        # Special annex flags
        wmt = Customer.objects.get(customer_number="F31906")
        wmt_annex = wmt.annex
        wmt_annex.split_processing = True
        wmt_annex.save()

        # Direct Supply National routes straight to PTQ
        ds_nat = Customer.objects.get(customer_number="F14746")
        ds_nat_annex = ds_nat.annex
        ds_nat_annex.route_to_ptq = True
        ds_nat_annex.save()

        # -----------------------------------------------------------------------
        # PRODUCTS (~50)
        # -----------------------------------------------------------------------
        products_data = [
            # BED-RAILS (4 products)
            {"product_number": "FEI-1001", "sku": "FEI-1001", "description": "Standard Bed Rail - Chrome", "list_price": 89.99, "dealer_price": 64.99, "standard_cost": 32.00, "category": "BED-RAILS"},
            {"product_number": "FEI-1002", "sku": "FEI-1002", "description": "Standard Bed Rail - White", "list_price": 89.99, "dealer_price": 64.99, "standard_cost": 32.00, "category": "BED-RAILS"},
            {"product_number": "FEI-1003", "sku": "FEI-1003", "description": "Half Bed Rail - Adjustable", "list_price": 64.99, "dealer_price": 44.99, "standard_cost": 22.00, "category": "BED-RAILS"},
            {"product_number": "FEI-1004", "sku": "FEI-1004", "description": "Deluxe Bed Rail - Full Length", "list_price": 119.99, "dealer_price": 84.99, "standard_cost": 48.00, "category": "BED-RAILS"},
            # CUSHIONS (4 products)
            {"product_number": "FEI-2001", "sku": "FEI-2001", "description": "Wheelchair Cushion - Standard", "list_price": 45.99, "dealer_price": 29.99, "standard_cost": 15.00, "category": "CUSHIONS"},
            {"product_number": "FEI-2002", "sku": "FEI-2002", "description": "Wheelchair Cushion - Gel", "list_price": 79.99, "dealer_price": 54.99, "standard_cost": 28.00, "category": "CUSHIONS"},
            {"product_number": "FEI-2003", "sku": "FEI-2003", "description": "Pressure Relief Cushion - Memory Foam", "list_price": 99.99, "dealer_price": 69.99, "standard_cost": 38.00, "category": "CUSHIONS"},
            {"product_number": "FEI-2004", "sku": "FEI-2004", "description": "Coccyx Cushion - Standard", "list_price": 34.99, "dealer_price": 22.99, "standard_cost": 11.00, "category": "CUSHIONS"},
            # EXERCISE (5 standalone + 1 kit + 1 nested kit)
            {"product_number": "FEI-3001", "sku": "FEI-3001", "description": "Exercise Band - Light (Yellow)", "list_price": 12.99, "dealer_price": 7.99, "standard_cost": 3.50, "category": "EXERCISE"},
            {"product_number": "FEI-3002", "sku": "FEI-3002", "description": "Exercise Band - Medium (Red)", "list_price": 12.99, "dealer_price": 7.99, "standard_cost": 3.50, "category": "EXERCISE"},
            {"product_number": "FEI-3003", "sku": "FEI-3003", "description": "Exercise Band - Heavy (Blue)", "list_price": 14.99, "dealer_price": 9.99, "standard_cost": 4.00, "category": "EXERCISE"},
            {"product_number": "FEI-3004", "sku": "FEI-3004", "description": "Hand Exerciser - Soft", "list_price": 9.99, "dealer_price": 6.49, "standard_cost": 2.50, "category": "EXERCISE"},
            {"product_number": "FEI-3005", "sku": "FEI-3005", "description": "Pedal Exerciser - Desktop", "list_price": 49.99, "dealer_price": 34.99, "standard_cost": 18.00, "category": "EXERCISE"},
            {"product_number": "KIT-3000", "sku": "KIT-3000", "description": "Exercise Band 3-Pack (Light/Med/Heavy)", "list_price": 34.99, "dealer_price": 22.99, "standard_cost": 11.00, "category": "EXERCISE", "is_kit": True},
            {"product_number": "KIT-3100", "sku": "KIT-3100", "description": "Exercise Starter Kit (Bands + Exerciser)", "list_price": 69.99, "dealer_price": 49.99, "standard_cost": 25.00, "category": "EXERCISE", "is_kit": True},
            # THERAPY (4 products)
            {"product_number": "FEI-5001", "sku": "FEI-5001", "description": "Hot/Cold Pack - Standard", "list_price": 8.99, "dealer_price": 5.49, "standard_cost": 2.25, "category": "THERAPY"},
            {"product_number": "FEI-5002", "sku": "FEI-5002", "description": "Hot/Cold Pack - Cervical", "list_price": 12.99, "dealer_price": 8.49, "standard_cost": 3.75, "category": "THERAPY"},
            {"product_number": "FEI-5003", "sku": "FEI-5003", "description": "TENS Unit - 2 Channel", "list_price": 59.99, "dealer_price": 39.99, "standard_cost": 22.00, "category": "THERAPY"},
            {"product_number": "FEI-5004", "sku": "FEI-5004", "description": "Ultrasound Gel - 8oz", "list_price": 6.99, "dealer_price": 4.29, "standard_cost": 1.80, "category": "THERAPY"},
            # SEATING (4 products + 1 drop-ship)
            {"product_number": "FEI-4001", "sku": "FEI-4001", "description": "Transport Chair - Standard", "list_price": 149.99, "dealer_price": 104.99, "standard_cost": 62.00, "category": "SEATING"},
            {"product_number": "FEI-4002", "sku": "FEI-4002", "description": "Recliner Chair - Basic", "list_price": 399.99, "dealer_price": 279.99, "standard_cost": 165.00, "category": "SEATING"},
            {"product_number": "FEI-4003", "sku": "FEI-4003", "description": "Geri Chair - Standard", "list_price": 549.99, "dealer_price": 384.99, "standard_cost": 230.00, "category": "SEATING"},
            {"product_number": "FEI-DS01", "sku": "FEI-DS01", "description": "Premium Lift Chair (Drop Ship)", "list_price": 899.99, "dealer_price": 599.99, "standard_cost": 450.00, "category": "SEATING", "is_drop_ship": True},
            # BATH-SAFETY (4 products)
            {"product_number": "FEI-6001", "sku": "FEI-6001", "description": "Grab Bar - 18 inch Chrome", "list_price": 29.99, "dealer_price": 19.99, "standard_cost": 9.50, "category": "BATH-SAFETY"},
            {"product_number": "FEI-6002", "sku": "FEI-6002", "description": "Grab Bar - 24 inch Chrome", "list_price": 34.99, "dealer_price": 23.99, "standard_cost": 11.50, "category": "BATH-SAFETY"},
            {"product_number": "FEI-6003", "sku": "FEI-6003", "description": "Bath Bench - Standard", "list_price": 44.99, "dealer_price": 29.99, "standard_cost": 15.00, "category": "BATH-SAFETY"},
            {"product_number": "FEI-6004", "sku": "FEI-6004", "description": "Tub Transfer Bench", "list_price": 69.99, "dealer_price": 47.99, "standard_cost": 28.00, "category": "BATH-SAFETY"},
            # MOBILITY (5 products + 1 drop-ship)
            {"product_number": "FEI-7001", "sku": "FEI-7001", "description": "Standard Walker - Folding", "list_price": 54.99, "dealer_price": 37.99, "standard_cost": 20.00, "category": "MOBILITY"},
            {"product_number": "FEI-7002", "sku": "FEI-7002", "description": "Rolling Walker (Rollator) - 4-Wheel", "list_price": 129.99, "dealer_price": 89.99, "standard_cost": 52.00, "category": "MOBILITY"},
            {"product_number": "FEI-7003", "sku": "FEI-7003", "description": "Quad Cane - Large Base", "list_price": 34.99, "dealer_price": 22.99, "standard_cost": 11.00, "category": "MOBILITY"},
            {"product_number": "FEI-7004", "sku": "FEI-7004", "description": "Forearm Crutches - Pair", "list_price": 49.99, "dealer_price": 34.99, "standard_cost": 19.00, "category": "MOBILITY"},
            {"product_number": "FEI-DS02", "sku": "FEI-DS02", "description": "Power Wheelchair - Standard (Drop Ship)", "list_price": 2499.99, "dealer_price": 1799.99, "standard_cost": 1250.00, "category": "MOBILITY", "is_drop_ship": True},
            # DIAGNOSTICS (3 products)
            {"product_number": "FEI-8001", "sku": "FEI-8001", "description": "Blood Pressure Monitor - Wrist", "list_price": 39.99, "dealer_price": 26.99, "standard_cost": 14.00, "category": "DIAGNOSTICS"},
            {"product_number": "FEI-8002", "sku": "FEI-8002", "description": "Pulse Oximeter - Fingertip", "list_price": 24.99, "dealer_price": 16.99, "standard_cost": 8.50, "category": "DIAGNOSTICS"},
            {"product_number": "FEI-8003", "sku": "FEI-8003", "description": "Infrared Thermometer - Non-Contact", "list_price": 29.99, "dealer_price": 19.99, "standard_cost": 10.00, "category": "DIAGNOSTICS"},
            # REHAB (3 products)
            {"product_number": "FEI-9001", "sku": "FEI-9001", "description": "Paraffin Bath - Standard", "list_price": 79.99, "dealer_price": 54.99, "standard_cost": 30.00, "category": "REHAB"},
            {"product_number": "FEI-9002", "sku": "FEI-9002", "description": "Balance Board - Standard", "list_price": 44.99, "dealer_price": 29.99, "standard_cost": 16.00, "category": "REHAB"},
            {"product_number": "FEI-9003", "sku": "FEI-9003", "description": "Therapy Putty Set - 4 Resistance", "list_price": 19.99, "dealer_price": 13.49, "standard_cost": 6.50, "category": "REHAB"},
            # POSITIONING (3 products)
            {"product_number": "FEI-P001", "sku": "FEI-P001", "description": "Positioning Wedge - 12 inch", "list_price": 54.99, "dealer_price": 37.99, "standard_cost": 20.00, "category": "POSITIONING"},
            {"product_number": "FEI-P002", "sku": "FEI-P002", "description": "Bolster Pillow - Cylindrical", "list_price": 29.99, "dealer_price": 19.99, "standard_cost": 10.00, "category": "POSITIONING"},
            {"product_number": "FEI-P003", "sku": "FEI-P003", "description": "Body Alignment Pillow", "list_price": 39.99, "dealer_price": 26.99, "standard_cost": 14.00, "category": "POSITIONING"},
            # KIT products (3 more kits)
            {"product_number": "KIT-6000", "sku": "KIT-6000", "description": "Bath Safety Starter Kit (Grab Bars + Bench)", "list_price": 89.99, "dealer_price": 62.99, "standard_cost": 34.00, "category": "BATH-SAFETY", "is_kit": True},
            {"product_number": "KIT-8000", "sku": "KIT-8000", "description": "Home Diagnostics Kit (BP + Oximeter + Thermometer)", "list_price": 79.99, "dealer_price": 54.99, "standard_cost": 30.00, "category": "DIAGNOSTICS", "is_kit": True},
            {"product_number": "KIT-9000", "sku": "KIT-9000", "description": "Rehab Essentials Kit", "list_price": 109.99, "dealer_price": 76.99, "standard_cost": 44.00, "category": "REHAB", "is_kit": True},
            # Drop-ship product 3
            {"product_number": "FEI-DS03", "sku": "FEI-DS03", "description": "Stair Lift - Straight (Drop Ship)", "list_price": 3499.99, "dealer_price": 2499.99, "standard_cost": 1800.00, "category": "MOBILITY", "is_drop_ship": True},
            # Obsolete products (2)
            {"product_number": "FEI-OBS1", "sku": "FEI-OBS1", "description": "Bed Rail - Legacy Model (OBSOLETE)", "list_price": 49.99, "dealer_price": 34.99, "standard_cost": 18.00, "category": "BED-RAILS", "is_obsolete": True, "is_active": False},
            {"product_number": "FEI-OBS2", "sku": "FEI-OBS2", "description": "Manual BP Cuff - Aneroid (OBSOLETE)", "list_price": 19.99, "dealer_price": 12.99, "standard_cost": 6.00, "category": "DIAGNOSTICS", "is_obsolete": True, "is_active": False},
        ]
        for data in products_data:
            prod, created = Product.objects.get_or_create(
                product_number=data.pop("product_number"), defaults=data
            )
            ProductAnnex.objects.get_or_create(product=prod, defaults={"weight": Decimal("2.5")})
            if created:
                self.stdout.write(f"  Created product: {prod}")

        # -----------------------------------------------------------------------
        # KIT COMPONENTS (BOMs)
        # -----------------------------------------------------------------------
        # KIT-3000: Exercise Band 3-Pack (Light + Med + Heavy)
        kit_3pack = Product.objects.get(product_number="KIT-3000")
        for comp_pn, qty in [("FEI-3001", 1), ("FEI-3002", 1), ("FEI-3003", 1)]:
            comp = Product.objects.get(product_number=comp_pn)
            KitComponent.objects.get_or_create(
                parent_product=kit_3pack, component_product=comp,
                defaults={"quantity_per_kit": qty},
            )

        # KIT-3100: Exercise Starter Kit (NESTED - contains KIT-3000 + Hand Exerciser + Pedal Exerciser)
        # This is the nested kit: KIT-3100 contains KIT-3000 (itself a kit) + 2 standalone items
        kit_starter = Product.objects.get(product_number="KIT-3100")
        for comp_pn, qty in [("KIT-3000", 1), ("FEI-3004", 1), ("FEI-3005", 1)]:
            comp = Product.objects.get(product_number=comp_pn)
            KitComponent.objects.get_or_create(
                parent_product=kit_starter, component_product=comp,
                defaults={"quantity_per_kit": qty},
            )

        # KIT-6000: Bath Safety Starter Kit (2x 18" grab bar + 1x bath bench)
        kit_bath = Product.objects.get(product_number="KIT-6000")
        for comp_pn, qty in [("FEI-6001", 2), ("FEI-6003", 1)]:
            comp = Product.objects.get(product_number=comp_pn)
            KitComponent.objects.get_or_create(
                parent_product=kit_bath, component_product=comp,
                defaults={"quantity_per_kit": qty},
            )

        # KIT-8000: Home Diagnostics Kit (BP monitor + Oximeter + Thermometer)
        kit_diag = Product.objects.get(product_number="KIT-8000")
        for comp_pn, qty in [("FEI-8001", 1), ("FEI-8002", 1), ("FEI-8003", 1)]:
            comp = Product.objects.get(product_number=comp_pn)
            KitComponent.objects.get_or_create(
                parent_product=kit_diag, component_product=comp,
                defaults={"quantity_per_kit": qty},
            )

        # KIT-9000: Rehab Essentials Kit (Paraffin Bath + Balance Board + Therapy Putty)
        kit_rehab = Product.objects.get(product_number="KIT-9000")
        for comp_pn, qty in [("FEI-9001", 1), ("FEI-9002", 1), ("FEI-9003", 1)]:
            comp = Product.objects.get(product_number=comp_pn)
            KitComponent.objects.get_or_create(
                parent_product=kit_rehab, component_product=comp,
                defaults={"quantity_per_kit": qty},
            )

        # -----------------------------------------------------------------------
        # WAREHOUSE INVENTORY (varied quantities - active non-drop-ship products only)
        # -----------------------------------------------------------------------
        # Define per-product inventory overrides (NY qty, FL qty)
        inventory_overrides = {
            # Low stock items
            "FEI-4002": (8, 3),
            "FEI-4003": (5, 2),
            "FEI-DS01": None,   # drop-ship, skip
            "FEI-DS02": None,
            "FEI-DS03": None,
            "FEI-OBS1": None,   # obsolete/inactive, skip
            "FEI-OBS2": None,
            "FEI-9001": (12, 6),
            "KIT-3100": (20, 10),
            # High stock items
            "FEI-3001": (500, 250),
            "FEI-3002": (500, 250),
            "FEI-3003": (400, 200),
            "FEI-5001": (600, 300),
            "FEI-8002": (350, 150),
        }

        for prod in Product.objects.filter(is_drop_ship=False, is_active=True):
            override = inventory_overrides.get(prod.product_number)
            if override is None:
                continue  # explicitly excluded above
            ny_qty, fl_qty = override if override else (150, 75)
            WarehouseInventory.objects.get_or_create(
                product=prod, warehouse_code="NY",
                defaults={"on_hand_qty": ny_qty, "standard_cost": prod.standard_cost},
            )
            WarehouseInventory.objects.get_or_create(
                product=prod, warehouse_code="FL",
                defaults={"on_hand_qty": fl_qty, "standard_cost": prod.standard_cost},
            )

        # Products not in override dict get default quantities
        for prod in Product.objects.filter(is_drop_ship=False, is_active=True):
            if prod.product_number not in inventory_overrides:
                WarehouseInventory.objects.get_or_create(
                    product=prod, warehouse_code="NY",
                    defaults={"on_hand_qty": 150, "standard_cost": prod.standard_cost},
                )
                WarehouseInventory.objects.get_or_create(
                    product=prod, warehouse_code="FL",
                    defaults={"on_hand_qty": 75, "standard_cost": prod.standard_cost},
                )

        # Drop-ship products get D warehouse with 0 on-hand
        for prod in Product.objects.filter(is_drop_ship=True):
            WarehouseInventory.objects.get_or_create(
                product=prod, warehouse_code="D",
                defaults={"on_hand_qty": 0, "standard_cost": prod.standard_cost},
            )

        # -----------------------------------------------------------------------
        # CUSTOMER SPECIAL PRICING (~10-15 combos)
        # -----------------------------------------------------------------------
        def make_special_price(cust_num, prod_num, gross, disc1=0, net=None):
            cust = Customer.objects.get(customer_number=cust_num)
            prod = Product.objects.get(product_number=prod_num)
            if net is None:
                net = gross * (1 - Decimal(str(disc1)) / 100)
            CustomerSpecialPrice.objects.get_or_create(
                customer=cust, product=prod,
                defaults={"gross_price": gross, "discount_1": disc1, "net_price": net},
            )

        # Acme Distribution - special on bed rails
        make_special_price("F10001", "FEI-1001", Decimal("72.00"), 10, Decimal("64.80"))
        make_special_price("F10001", "FEI-1002", Decimal("72.00"), 10, Decimal("64.80"))

        # Direct Supply National - special on cushions
        for pn in ["FEI-2001", "FEI-2002", "FEI-2003"]:
            prod = Product.objects.get(product_number=pn)
            make_special_price("F14746", pn, prod.dealer_price, 0, prod.dealer_price * Decimal("0.90"))

        # Walmart.com - special on exercise + kit
        make_special_price("F31906", "KIT-3000", Decimal("28.99"), 0, Decimal("28.99"))
        make_special_price("F31906", "FEI-3001", Decimal("6.49"), 0, Decimal("6.49"))
        make_special_price("F31906", "FEI-3002", Decimal("6.49"), 0, Decimal("6.49"))

        # Great Lakes Distribution - bath safety discount
        make_special_price("F10011", "FEI-6001", Decimal("17.99"), 0, Decimal("17.99"))
        make_special_price("F10011", "FEI-6002", Decimal("20.99"), 0, Decimal("20.99"))
        make_special_price("F10011", "KIT-6000", Decimal("55.99"), 0, Decimal("55.99"))

        # Capitol Medical - GOV pricing on mobility
        make_special_price("F10014", "FEI-7001", Decimal("32.99"), 0, Decimal("32.99"))
        make_special_price("F10014", "FEI-7002", Decimal("79.99"), 0, Decimal("79.99"))

        # University Health - EDU pricing on diagnostics kit
        make_special_price("F10015", "KIT-8000", Decimal("48.99"), 0, Decimal("48.99"))

        # Metro Therapy - therapy discount
        make_special_price("F10018", "FEI-9001", Decimal("45.99"), 0, Decimal("45.99"))
        make_special_price("F10018", "KIT-9000", Decimal("68.99"), 0, Decimal("68.99"))

        # --- Affiliation Pricing ---
        from apps.pricing.models import AffiliationPrice
        self.stdout.write("  Creating affiliation prices...")
        aff_prices = [
            {"affiliation_code": "DIST", "product_number": "FEI-1001", "discount_pct": 15},
            {"affiliation_code": "DIST", "product_number": "FEI-1002", "discount_pct": 15},
            {"affiliation_code": "MED", "product_number": "FEI-2001", "discount_pct": 10},
            {"affiliation_code": "MED", "product_number": "FEI-2002", "discount_pct": 10},
            {"affiliation_code": "GOV", "product_number": "FEI-3001", "discount_pct": 20},
            {"affiliation_code": "GOV", "product_number": "FEI-3002", "discount_pct": 20},
            {"affiliation_code": "GOV", "product_number": "FEI-3003", "discount_pct": 20},
        ]
        for ap_data in aff_prices:
            prod = Product.objects.get(product_number=ap_data["product_number"])
            disc = Decimal(str(ap_data["discount_pct"]))
            gross = prod.list_price
            net = (gross * (Decimal("1") - disc / Decimal("100"))).quantize(Decimal("0.0001"))
            AffiliationPrice.objects.get_or_create(
                affiliation_code=ap_data["affiliation_code"],
                product=prod,
                defaults={"gross_price": gross, "discount_1": disc, "net_price": net},
            )

        # Set company codes on some customers
        for cn, cc in [("F10002", "B"), ("F10004", "C")]:
            try:
                c_obj = Customer.objects.get(customer_number=cn)
                c_obj.company_code = cc
                c_obj.save(update_fields=["company_code"])
            except Customer.DoesNotExist:
                pass

        # -----------------------------------------------------------------------
        # ORDERS (~30 total in various queue states)
        # -----------------------------------------------------------------------
        self.stdout.write("  Creating sample orders...")

        def p(product_number):
            return Product.objects.get(product_number=product_number).pk

        def c(customer_number):
            return Customer.objects.get(customer_number=customer_number)

        # Helper: create order only if no orders exist for customer with that PO
        def make_order(cust_num, lines, placed_by="SEED", po_number="", target_queue=None):
            cust = c(cust_num)
            # Check for existing order with same PO to stay idempotent
            if po_number and Order.objects.filter(customer=cust, po_number=po_number).exists():
                return Order.objects.filter(customer=cust, po_number=po_number).first()
            order = create_order(
                customer=cust,
                lines=lines,
                placed_by=placed_by,
                po_number=po_number,
            )
            # Advance queue state if requested
            if target_queue and target_queue != order.queue_status:
                self._advance_to(order, target_queue, placed_by)
            return order

        # Helper: create order directly in OEQ (order entry in progress, credit check not yet run)
        import datetime
        from apps.pricing.services import calculate_price

        def make_oeq_order(cust_num, lines_data, placed_by="WEB", po_number=""):
            """Create an order directly at OEQ status without running credit check."""
            cust = c(cust_num)
            if po_number and Order.objects.filter(customer=cust, po_number=po_number).exists():
                return
            from apps.orders.services import _next_order_number, sync_customer_open_orders
            order = Order.objects.create(
                order_number=_next_order_number(),
                customer=cust,
                placed_by=placed_by,
                order_date=datetime.date.today(),
                terms=cust.terms_code,
                salesman=cust.salesman,
                affiliation=cust.affiliation,
                po_number=po_number,
                queue_status="OEQ",
            )
            subtotal = Decimal("0")
            for idx, ld in enumerate(lines_data, start=1):
                prod = Product.objects.get(pk=ld["product_id"])
                price_result = calculate_price(cust, prod)
                qty = ld["qty_ordered"]
                extension = price_result.net * qty
                OrderLine.objects.create(
                    order=order, line_number=idx, product=prod,
                    unit_price=price_result.gross, discount_1=price_result.discount_1,
                    discount_2=price_result.discount_2, net_price=price_result.net,
                    cost=prod.standard_cost, qty_ordered=qty, qty_open=qty,
                    warehouse_code=ld.get("warehouse_code", "NY"), extension=extension,
                )
                subtotal += extension
            order.subtotal = subtotal
            order.save(update_fields=["subtotal"])
            OrderAudit.objects.create(order=order, operator=placed_by, event_code="OEQ", notes="Order entry in progress")
            sync_customer_open_orders(cust)

        # --- OEQ orders (~4 orders sitting in Order Entry, credit check not yet submitted) ---
        make_oeq_order("F10019", [{"product_id": p("FEI-8001"), "qty_ordered": 5, "warehouse_code": "NY"}], placed_by="PHONE", po_number="DSM-001")
        make_oeq_order("F10013", [{"product_id": p("FEI-6003"), "qty_ordered": 8, "warehouse_code": "FL"}, {"product_id": p("FEI-6004"), "qty_ordered": 4, "warehouse_code": "FL"}], placed_by="WEB", po_number="SSL-WEB-101")
        make_oeq_order("F10010", [{"product_id": p("FEI-5001"), "qty_ordered": 20, "warehouse_code": "NY"}, {"product_id": p("FEI-5002"), "qty_ordered": 10, "warehouse_code": "NY"}], placed_by="EDI", po_number="VVP-EDI-0055")
        make_oeq_order("F10015", [{"product_id": p("KIT-8000"), "qty_ordered": 3, "warehouse_code": "NY"}], placed_by="WEB", po_number="UHS-WEB-22")

        # --- CHQ orders (~6 orders in credit hold) ---
        # code D auto-hold
        make_order("F10005", [{"product_id": p("FEI-1002"), "qty_ordered": 2, "warehouse_code": "NY"}], placed_by="SEED", po_number="EAG-001")
        make_order("F10005", [{"product_id": p("FEI-7001"), "qty_ordered": 3, "warehouse_code": "NY"}, {"product_id": p("FEI-7003"), "qty_ordered": 2, "warehouse_code": "NY"}], placed_by="PHONE", po_number="EAG-002")

        # over_90_balance triggers hold
        make_order("F10003", [{"product_id": p("FEI-5001"), "qty_ordered": 50, "warehouse_code": "FL"}], placed_by="SEED")
        make_order("F10007", [{"product_id": p("FEI-2001"), "qty_ordered": 10, "warehouse_code": "NY"}, {"product_id": p("FEI-2003"), "qty_ordered": 5, "warehouse_code": "NY"}], placed_by="EDI", po_number="HML-EDI-300")
        make_order("F10017", [{"product_id": p("FEI-1001"), "qty_ordered": 6, "warehouse_code": "NY"}], placed_by="WEB", po_number="BRH-WEB-55")

        # code H auto-hold
        make_order("F10009", [{"product_id": p("FEI-P001"), "qty_ordered": 4, "warehouse_code": "FL"}], placed_by="PHONE", po_number="SCM-001")

        # code C auto-hold
        make_order("F10016", [{"product_id": p("FEI-6001"), "qty_ordered": 12, "warehouse_code": "NY"}], placed_by="WEB", po_number="CCP-WEB-7")

        # --- MGQ orders (~8 orders - approved, waiting management release) ---
        make_order("F10001", [{"product_id": p("FEI-1001"), "qty_ordered": 10, "warehouse_code": "NY"}, {"product_id": p("FEI-2001"), "qty_ordered": 5, "warehouse_code": "NY"}], placed_by="SEED", po_number="ACME-PO-2026-001")
        make_order("F10002", [{"product_id": p("FEI-3001"), "qty_ordered": 100, "warehouse_code": "NY"}], placed_by="SEED", po_number="BETA-PO-100")
        make_order("F10004", [{"product_id": p("FEI-1003"), "qty_ordered": 25, "warehouse_code": "NY"}, {"product_id": p("FEI-1004"), "qty_ordered": 10, "warehouse_code": "NY"}, {"product_id": p("FEI-2004"), "qty_ordered": 15, "warehouse_code": "NY"}], placed_by="EDI", po_number="DSI-EDI-2026-88")
        make_order("F10006", [{"product_id": p("FEI-7002"), "qty_ordered": 8, "warehouse_code": "FL"}], placed_by="PHONE", po_number="GHH-001")
        make_order("F10008", [{"product_id": p("KIT-3000"), "qty_ordered": 20, "warehouse_code": "NY"}, {"product_id": p("KIT-3100"), "qty_ordered": 5, "warehouse_code": "NY"}], placed_by="EDI", po_number="NRS-EDI-441")
        make_order("F10011", [{"product_id": p("FEI-6001"), "qty_ordered": 50, "warehouse_code": "NY"}, {"product_id": p("FEI-6002"), "qty_ordered": 50, "warehouse_code": "NY"}, {"product_id": p("KIT-6000"), "qty_ordered": 10, "warehouse_code": "NY"}], placed_by="EDI", po_number="GLD-EDI-2026-19")
        make_order("F10012", [{"product_id": p("FEI-9001"), "qty_ordered": 6, "warehouse_code": "NY"}, {"product_id": p("FEI-9002"), "qty_ordered": 6, "warehouse_code": "NY"}], placed_by="WEB", po_number="PHS-WEB-303")
        make_order("F10018", [{"product_id": p("KIT-9000"), "qty_ordered": 4, "warehouse_code": "NY"}, {"product_id": p("FEI-5003"), "qty_ordered": 8, "warehouse_code": "NY"}], placed_by="PHONE", po_number="MTA-001")

        # --- PTQ orders (~5 orders - pick ticket printed) ---
        # Direct Supply National routes to PTQ automatically via annex flag
        make_order("F14746", [{"product_id": p("FEI-2001"), "qty_ordered": 30, "warehouse_code": "NY"}, {"product_id": p("FEI-2002"), "qty_ordered": 20, "warehouse_code": "NY"}], placed_by="EDI", po_number="DSN-EDI-5001")
        make_order("F14746", [{"product_id": p("FEI-2003"), "qty_ordered": 15, "warehouse_code": "FL"}], placed_by="EDI", po_number="DSN-EDI-5002")

        # Manually advance some MGQ orders to PTQ
        mgq_to_ptq_specs = [
            ("F10001", "ACME-PO-2026-PTQ", [{"product_id": p("FEI-1001"), "qty_ordered": 5, "warehouse_code": "NY"}], "ADMIN"),
            ("F10004", "DSI-PTQ-001", [{"product_id": p("FEI-7004"), "qty_ordered": 12, "warehouse_code": "NY"}, {"product_id": p("FEI-7003"), "qty_ordered": 6, "warehouse_code": "NY"}], "ADMIN"),
            ("F10006", "GHH-PTQ-01", [{"product_id": p("FEI-8002"), "qty_ordered": 25, "warehouse_code": "FL"}, {"product_id": p("FEI-8003"), "qty_ordered": 10, "warehouse_code": "FL"}], "ADMIN"),
        ]
        for cust_num, po, lines, operator in mgq_to_ptq_specs:
            cust = c(cust_num)
            if not Order.objects.filter(customer=cust, po_number=po).exists():
                order = create_order(customer=cust, lines=lines, placed_by=operator, po_number=po)
                self._advance_to(order, "PTQ", operator)

        # --- IVQ orders (~4 orders - invoiced) ---
        ivq_specs = [
            ("F10031", "F10001", "ACME-PO-2026-IVQ", [{"product_id": p("FEI-1002"), "qty_ordered": 8, "warehouse_code": "NY"}], "ADMIN"),
            ("F10032", "F10002", "BETA-IVQ-55", [{"product_id": p("FEI-3002"), "qty_ordered": 50, "warehouse_code": "NY"}, {"product_id": p("FEI-3003"), "qty_ordered": 30, "warehouse_code": "NY"}], "ADMIN"),
            ("F10033", "F10011", "GLD-IVQ-2026-01", [{"product_id": p("FEI-6003"), "qty_ordered": 20, "warehouse_code": "NY"}], "ADMIN"),
            ("F10034", "F10014", "CAP-IVQ-101", [{"product_id": p("FEI-7001"), "qty_ordered": 15, "warehouse_code": "NY"}, {"product_id": p("FEI-P001"), "qty_ordered": 5, "warehouse_code": "NY"}], "ADMIN"),
        ]
        for _ref, cust_num, po, lines, operator in ivq_specs:
            cust = c(cust_num)
            if not Order.objects.filter(customer=cust, po_number=po).exists():
                order = create_order(customer=cust, lines=lines, placed_by=operator, po_number=po)
                self._advance_to(order, "IVQ", operator)

        # --- Drop-ship order ---
        ds_cust = c("F10012")
        if not Order.objects.filter(customer=ds_cust, po_number="PHS-DS-001").exists():
            create_order(
                customer=ds_cust,
                lines=[{"product_id": p("FEI-DS01"), "qty_ordered": 1, "warehouse_code": "D"}],
                placed_by="PHONE",
                po_number="PHS-DS-001",
            )

        # --- Walmart multi-line order ---
        wmt_cust = c("F31906")
        if not Order.objects.filter(customer=wmt_cust, po_number="WMT-EDI-2026-001").exists():
            create_order(
                customer=wmt_cust,
                lines=[
                    {"product_id": p("KIT-3000"), "qty_ordered": 200, "warehouse_code": "NY"},
                    {"product_id": p("FEI-3001"), "qty_ordered": 500, "warehouse_code": "NY"},
                    {"product_id": p("FEI-3002"), "qty_ordered": 500, "warehouse_code": "NY"},
                    {"product_id": p("FEI-3003"), "qty_ordered": 300, "warehouse_code": "NY"},
                    {"product_id": p("FEI-5001"), "qty_ordered": 150, "warehouse_code": "NY"},
                ],
                placed_by="EDI",
                po_number="WMT-EDI-2026-001",
            )

        # --- Backorder scenario orders ---
        self.stdout.write("  Creating backorder scenario orders...")

        # Set some products to low stock for backorder demo
        for pn, ny_qty, fl_qty in [("FEI-5001", 8, 3), ("FEI-2002", 5, 2)]:
            try:
                prod = Product.objects.get(product_number=pn)
                WarehouseInventory.objects.filter(product=prod, warehouse_code="NY").update(on_hand_qty=ny_qty)
                WarehouseInventory.objects.filter(product=prod, warehouse_code="FL").update(on_hand_qty=fl_qty)
            except Product.DoesNotExist:
                pass

        # Order that triggers partial backorder (customer allows backorders)
        try:
            ds_inc = Customer.objects.get(customer_number="F10004")
            ds_inc.backorder_flag = True
            ds_inc.save(update_fields=["backorder_flag"])
            hot_cold = Product.objects.get(product_number="FEI-5001")
            if not Order.objects.filter(po_number="BO-DEMO-001").exists():
                create_order(
                    customer=ds_inc,
                    lines=[{"product_id": hot_cold.pk, "qty_ordered": 25, "warehouse_code": "NY"}],
                    placed_by="SEED",
                    po_number="BO-DEMO-001",
                )
        except (Customer.DoesNotExist, Product.DoesNotExist):
            pass

        # -----------------------------------------------------------------------
        # SUMMARY
        # -----------------------------------------------------------------------
        from apps.orders.models import Order as O
        queue_counts = {}
        for choice_code, _ in O.QUEUE_CHOICES:
            queue_counts[choice_code] = O.objects.filter(queue_status=choice_code).count()

        self.stdout.write(self.style.SUCCESS("\nTest data seeded successfully!"))
        self.stdout.write(f"  Customers:          {Customer.objects.count()}")
        self.stdout.write(f"  Products:           {Product.objects.count()}")
        self.stdout.write(f"    Active:           {Product.objects.filter(is_active=True).count()}")
        self.stdout.write(f"    Kits:             {Product.objects.filter(is_kit=True).count()}")
        self.stdout.write(f"    Drop-ship:        {Product.objects.filter(is_drop_ship=True).count()}")
        self.stdout.write(f"    Obsolete:         {Product.objects.filter(is_obsolete=True).count()}")
        self.stdout.write(f"  Kit components:     {KitComponent.objects.count()}")
        self.stdout.write(f"  Warehouse records:  {WarehouseInventory.objects.count()}")
        self.stdout.write(f"  Special prices:     {CustomerSpecialPrice.objects.count()}")
        self.stdout.write(f"  Affiliation prices: {AffiliationPrice.objects.count()}")
        self.stdout.write(f"  Orders (total):     {Order.objects.count()}")
        for code, count in queue_counts.items():
            self.stdout.write(f"    {code}:             {count}")
        from apps.products.models import InventoryCommitment
        self.stdout.write(f"  Inventory commitments: {InventoryCommitment.objects.count()}")

    def _advance_to(self, order, target_queue, operator):
        """Advance an order through the queue pipeline to the target state."""
        pipeline = ["OEQ", "MGQ", "CHQ", "PTQ", "IVQ"]
        # Handle CHQ -> MGQ -> PTQ path
        chq_to_ptq = ["CHQ", "MGQ", "PTQ"]

        current = order.queue_status
        if current == target_queue:
            return order

        # If currently in CHQ, must go CHQ->MGQ->PTQ->IVQ
        if current == "CHQ":
            path = chq_to_ptq
            start_idx = 0
        else:
            try:
                start_idx = pipeline.index(current) + 1
            except ValueError:
                return order
            path = pipeline[start_idx:]

        for next_status in path:
            from apps.orders.services import VALID_TRANSITIONS
            if next_status in VALID_TRANSITIONS.get(order.queue_status, []):
                order = order.__class__.objects.get(pk=order.pk)  # refresh
                from apps.orders.services import transition_queue as tq
                order = tq(order, next_status, operator)
            if order.queue_status == target_queue:
                break

        return order
