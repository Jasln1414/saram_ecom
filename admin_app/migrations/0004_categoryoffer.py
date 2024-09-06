# Generated by Django 5.0.7 on 2024-08-19 17:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0003_remove_productcolorimage_color_code_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoryOffer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('offer_name', models.CharField(blank=True, max_length=100, null=True)),
                ('discount_percentage', models.PositiveIntegerField()),
                ('is_active', models.BooleanField(default=True)),
                ('start_date', models.DateField(auto_now_add=True)),
                ('end_date', models.DateField()),
                ('category', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='admin_app.category')),
            ],
        ),
    ]
