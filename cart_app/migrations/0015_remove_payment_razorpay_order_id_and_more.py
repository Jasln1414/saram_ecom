# Generated by Django 5.0.7 on 2024-08-22 02:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cart_app', '0014_remove_order_amount_remove_order_order_id_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='payment',
            name='razorpay_order_id',
        ),
        migrations.RemoveField(
            model_name='payment',
            name='razorpay_payment_id',
        ),
        migrations.RemoveField(
            model_name='payment',
            name='razorpay_signature',
        ),
        migrations.DeleteModel(
            name='Transaction',
        ),
    ]
