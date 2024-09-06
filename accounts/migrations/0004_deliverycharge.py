# Generated by Django 5.0.7 on 2024-09-01 16:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_address_latitude_address_longitude'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeliveryCharge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('city', models.CharField(max_length=100, unique=True)),
                ('charge', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
        ),
    ]
