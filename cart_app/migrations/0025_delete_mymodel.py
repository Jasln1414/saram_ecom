# Generated by Django 5.1.1 on 2024-09-12 11:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cart_app', '0024_alter_orderitem_status'),
    ]

    operations = [
        migrations.DeleteModel(
            name='MyModel',
        ),
    ]