# Generated by Django 5.0.7 on 2024-08-20 11:40

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0007_coupon_remove_product_colors_product_per_expiry_date_and_more'),
        ('cart_app', '0006_payment_order_coupon_applied_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartitem',
            name='coupon',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='admin_app.coupon'),
        ),
    ]
