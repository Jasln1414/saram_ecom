# Generated by Django 5.0.7 on 2024-08-16 05:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='colors',
            field=models.ManyToManyField(related_name='products', to='admin_app.color'),
        ),
        migrations.AlterField(
            model_name='productcolor',
            name='color',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_colors', to='admin_app.color'),
        ),
        migrations.AlterField(
            model_name='productcolor',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='color_variants', to='admin_app.product'),
        ),
    ]
