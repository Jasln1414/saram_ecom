# Generated by Django 5.0.7 on 2024-08-20 13:09

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart_app', '0011_transaction_money_withdrawn'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='transaction_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
