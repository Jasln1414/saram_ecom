from cart_app.models import *


def default(request):
    if request.user.is_authenticated:
        user = request.user
        cart_count = CartItem.objects.filter(user_cart__customer__user=user).count()
        wishlist_count = WishList.objects.filter(customer__user=user).count()
        context = {
            "cart_count": cart_count,
            "wishlist_count": wishlist_count,
        }
        return context
    else:
        # Return an empty dictionary or include a specific variable
        return {"user_is_authenticated": False}