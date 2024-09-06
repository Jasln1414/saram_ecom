# Generated by Django 5.0.7 on 2024-08-15 20:25

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('admin_app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('method_name', models.CharField(default='Cash on Delivery', max_length=100)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('pending', models.BooleanField(default=True)),
                ('failed', models.BooleanField(default=False)),
                ('success', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_method', models.CharField(max_length=100)),
                ('status', models.CharField(choices=[('Delivered', 'Delivered'), ('Cancelled', 'Cancelled'), ('On Progress', 'On Progress')], default='Pending', max_length=20)),
                ('tracking_id', models.CharField(max_length=100, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('subtotal', models.PositiveBigIntegerField(blank=True, default=0, null=True)),
                ('shipping_charge', models.PositiveBigIntegerField(blank=True, default=0, null=True)),
                ('total', models.IntegerField(default=0)),
                ('paid', models.BooleanField(default=False)),
                ('address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='accounts.address')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.customer')),
                ('payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='cart_app.payment')),
            ],
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('Order Placed', 'Order Placed'), ('Shipped', 'Shipped'), ('Out for Delivery', 'Out for Delivery'), ('Delivered', 'Delivered'), ('Cancelled', 'Cancelled')], default='Pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('each_price', models.PositiveBigIntegerField(blank=True, default=0, null=True)),
                ('size', models.CharField(default='S', max_length=12)),
                ('qty', models.PositiveIntegerField(default=0)),
                ('request_cancel', models.BooleanField(default=False)),
                ('cancel', models.BooleanField(default=False)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order', to='cart_app.order')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='product_order', to='admin_app.productcolorimage')),
            ],
        ),
        migrations.CreateModel(
            name='Shipping_address',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(default=None, max_length=200)),
                ('last_name', models.CharField(default=None, max_length=200)),
                ('email', models.EmailField(default='user@gmail.com', max_length=254)),
                ('house_name', models.CharField(max_length=200)),
                ('city', models.CharField(max_length=100)),
                ('state', models.CharField(max_length=100)),
                ('postal_code', models.CharField(max_length=20)),
                ('country', models.CharField(max_length=100)),
                ('phone_number', models.CharField(max_length=12)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cart_app.order')),
            ],
        ),
        migrations.CreateModel(
            name='User_Cart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('customer', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='accounts.customer')),
            ],
        ),
        migrations.CreateModel(
            name='CartItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_size', models.CharField(blank=True, max_length=10, null=True)),
                ('quantity', models.PositiveIntegerField(blank=True, default=1, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='product_cart', to='admin_app.productcolorimage')),
                ('user_cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cart_app.user_cart')),
            ],
        ),
    ]
