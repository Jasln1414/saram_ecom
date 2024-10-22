# Generated by Django 5.0.7 on 2024-08-30 17:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart_app', '0022_alter_order_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='status',
            field=models.CharField(choices=[('Order Placed', 'Order Placed'), ('Pending', 'Pending'), ('Shipped', 'Shipped'), ('Out for Delivery', 'Out for Delivery'), ('Delivered', 'Delivered'), ('Returned', 'Returned')], default='Pending', max_length=20),
        ),
    ]
