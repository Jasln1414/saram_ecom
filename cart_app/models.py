from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from admin_app.models import *
from accounts.models import *


# Create your models here.


class User_Cart(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Cart for {self.customer.user.username}"


@receiver(post_save, sender=Customer)
def create_customer_cart(sender, instance, created, **kwargs):
    if created:
        User_Cart.objects.create(customer=instance)
        print("cart customer created successfully!!")


class CartItem(models.Model):
    user_cart = models.ForeignKey(User_Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(
        ProductColorImage,
        on_delete=models.CASCADE,
        related_name="product_cart",
        null=True,
        blank=True,
    )
    product_size = models.CharField(max_length=10, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1, null=True, blank=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.product.name} - {self.product_size} - (Quantity: {self.quantity})"

    @property
    def total_price(self):
        offer_price = self.product.product.offer_price
        return int(round(self.quantity * offer_price))


class Payment(models.Model):
    method_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    paid_at = models.DateTimeField(null=True)
    pending = models.BooleanField(default=True)
    failed = models.BooleanField(default=False)
    success = models.BooleanField(default=False)

    def __str__(self) -> str:
        status = ""
        if self.pending:
            status += "Pending "
        if self.failed:
            status += "Failed "
        if self.success:
            status += "Success "

        return f"{self.method_name} - {status} Payment"


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    address = models.ForeignKey(
        Address, on_delete=models.DO_NOTHING, null=True, blank=True
    )
    payment_method = models.CharField(max_length=100, null=False)
    payment_transaction_id = models.CharField(max_length=100, null=True, blank=True)
    payment = models.ForeignKey(
        Payment, on_delete=models.PROTECT, null=True, blank=True
    )
    STATUS_CHOICES = (
        ("Order Placed", "Order Placed"),
        ("Pending", "Pending"),
        ("Shipped", "Shipped"),
        ("Out for Delivery", "Out for Delivery"),
        ("Delivered", "Delivered"),
        ("Returned", "Returned"),
        ("Refunded", "Refunded"),
        ("Cancelled", "Cancelled"),
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")

    tracking_id = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    subtotal = models.PositiveBigIntegerField(default=0, blank=True, null=True)
    shipping_charge = models.PositiveBigIntegerField(default=0, blank=True, null=True)
    total = models.IntegerField(default=0)
    paid = models.BooleanField(default=False)
    coupon_applied = models.BooleanField(default=False)
    coupon_name = models.CharField(blank=True, null=True)
    coupon_discount_percentage = models.PositiveBigIntegerField(blank=True, null=True)
    discounted_price = models.PositiveBigIntegerField(blank=True, default=0, null=True)

    def __str__(self) -> str:
        return f"Order ID: {self.id}, Tracking ID: {self.tracking_id}, Customer: {self.customer}"


class Shipping_address(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=200, default=None)
    last_name = models.CharField(max_length=200, default=None)
    email = models.EmailField(default="user@gmail.com")
    house_name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=12)

    def __str__(self):
        return f"{self.order.tracking_id}-{self.first_name}-{self.last_name}-{self.phone_number}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="order", on_delete=models.CASCADE)
    STATUS_CHOICES = (
        ("Order Placed", "Order Placed"),
        ("Shipped", "Shipped"),
        ("Out for Delivery", "Out for Delivery"),
        ("Delivered", "Delivered"),
        
        
        
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    product = models.ForeignKey(
        ProductColorImage,
        related_name="product_order",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    each_price = models.PositiveBigIntegerField(default=0, blank=True, null=True)
    size = models.CharField(max_length=12, default="S")
    qty = models.PositiveIntegerField(default=0)
    request_cancel = models.BooleanField(default=False)
    cancel = models.BooleanField(default=False)
    return_product = models.BooleanField(default=False)
    request_return = models.BooleanField(default=False)
    return_reason = models.TextField(blank=True, null=True)
    is_refunded = models.BooleanField(default=False)  # New field for refunded status
    def __str__(self):
        return f"{self.product.product.name} - {self.size} - (Quantity: {self.qty}, Status: {self.status})"

    def total_price(self):
        return self.cart_item.total_price()


@receiver(post_save, sender=OrderItem)
def change_order_status(sender, instance, **kwargs):
    order = instance.order
    order_items = OrderItem.objects.filter(order=order)
    if all(item.status == "Delivered" for item in order_items):
        order.status = "Delivered"
    elif all(item.status == "Cancelled" for item in order_items):
        order.status = "Cancelled"
    elif all(item.status == "Returned" for item in order_items):
        order.status = "Returned"
   
    else:
        return  # No status change

    order.save()
    print("Order status changed successfully!")

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.PositiveBigIntegerField(blank=True, default=0)
    referral_deposit = models.PositiveBigIntegerField(blank=True, default=0)

    def __str__(self):
        name = f"{self.user.first_name} {self.user.last_name} "
        email = self.user.email
        balance = self.balance
        return f"{name} {email} | Balance : {balance}"


@receiver(post_save, sender=User)
def Create_User_Wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)
        print("wallet created successfully!!")


class Wallet_transaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    order_item = models.ForeignKey(
        OrderItem, on_delete=models.CASCADE, null=True, blank=True
    )
    transaction_id = models.CharField(
        max_length=50,
        unique=True,
    )
    money_deposit = models.PositiveBigIntegerField(blank=True, default=0)
    money_withdrawn = models.PositiveBigIntegerField(blank=True, default=0)
    transaction_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.money_deposit:
            money = "+{}".format(self.money_deposit)
        elif self.money_withdrawn:
            money = "-{}".format(self.money_withdrawn)
        id = self.transaction_id
        item = self.order_item
        name = f"{self.wallet.user.first_name} {self.wallet.user.last_name}"
        time = self.transaction_time
        return f"{id} | {item} - {name} : {time} | {money}"


class WishList(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(ProductColorImage, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    qty = models.IntegerField(default=1, null=True, blank=True)
    size = models.CharField(default="S", null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.customer.user.username} :- {self.product.product.name} : {self.added_at}"