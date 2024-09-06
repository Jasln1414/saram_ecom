# Generated by Django 5.0.7 on 2024-08-29 20:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart_app', '0019_alter_orderitem_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='is_refunded',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='status',
            field=models.CharField(choices=[('Order Placed', 'Order Placed'), ('Pending', 'Pending'), ('Shipped', 'Shipped'), ('Out for Delivery', 'Out for Delivery'), ('Delivered', 'Delivered'), ('Returned', 'Returned')], default='Pending', max_length=20),
        ),
    ]
