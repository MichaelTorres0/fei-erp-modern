import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0001_initial'),
        ('orders', '0001_initial'),
        ('products', '0001_initial'),
    ]

    operations = [
        # Add new fields to Order
        migrations.AddField(
            model_name='order',
            name='customer',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='orders',
                to='customers.customer',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='is_drop_ship',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='order',
            name='ship_to_line_1',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='order',
            name='ship_to_line_2',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='order',
            name='ship_to_city',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='order',
            name='ship_to_state',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='order',
            name='ship_to_zip',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='ship_to_country',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='order',
            name='entry_date',
            field=models.DateField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='order_date',
            field=models.DateField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='required_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='po_number',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='order',
            name='placed_by',
            field=models.CharField(default='', max_length=50),
        ),
        migrations.AddField(
            model_name='order',
            name='email',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
        migrations.AddField(
            model_name='order',
            name='ship_via',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='order',
            name='freight_terms',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='terms',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='salesman',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='order',
            name='affiliation',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='order',
            name='territory_1',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='territory_2',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='territory_3',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_cost',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='order',
            name='special_instructions',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='order',
            name='special_discounts',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='order',
            name='subtotal',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='order',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='queue_status',
            field=models.CharField(
                choices=[
                    ('OEQ', 'Order Entry'),
                    ('MGQ', 'Management'),
                    ('CHQ', 'Credit Hold'),
                    ('PTQ', 'Pick Ticket'),
                    ('IVQ', 'Invoice'),
                ],
                default='OEQ',
                max_length=10,
            ),
        ),
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ['-created_at']},
        ),

        # Add new fields to OrderLine
        migrations.AddField(
            model_name='orderline',
            name='line_number',
            field=models.PositiveIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='orderline',
            name='unit_price',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='orderline',
            name='discount_1',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name='orderline',
            name='discount_2',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name='orderline',
            name='net_price',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='orderline',
            name='cost',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='orderline',
            name='qty_ordered',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='orderline',
            name='qty_shipped',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='orderline',
            name='backorder_qty',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='orderline',
            name='extension',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AlterUniqueTogether(
            name='orderline',
            unique_together={('order', 'line_number')},
        ),
        migrations.AlterModelOptions(
            name='orderline',
            options={'ordering': ['line_number']},
        ),

        # Add new fields to OrderAudit
        migrations.AddField(
            model_name='orderaudit',
            name='operator',
            field=models.CharField(default='SYSTEM', max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='orderaudit',
            name='notes',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterModelOptions(
            name='orderaudit',
            options={'ordering': ['timestamp']},
        ),
    ]
