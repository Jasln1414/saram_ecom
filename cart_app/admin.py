from django.contrib import admin
from .models import *

# Register your models here.

admin.site.register(User_Cart)
admin.site.register(CartItem)
admin.site.register(OrderItem)
admin.site.register(Order)
admin.site.register(CategoryOffer)
admin.site.register(Coupon)
admin.site.register(WishList)
admin.site.register(Payment)
admin.site.register(Wallet)
admin.site.register(Wallet_transaction)