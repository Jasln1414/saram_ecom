from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.utils.crypto import get_random_string
import re
import logging
from accounts.models import *
from admin_app.models import *
from cart_app.models import *
from django.core.exceptions import ObjectDoesNotExist  # Import for handling specific object not found cases
from django.http import JsonResponse  # Import for returning JSON responses
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.http import JsonResponse
from .models import *
from django.contrib import messages, auth
from admin_app.models import *
from accounts.models import *
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.utils.crypto import get_random_string
import razorpay # type: ignore
from django.conf import settings
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
import re
import logging
from django.db.models import Q
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import Sum ,F
from django.utils import timezone
from django.conf import settings


class MyModel(models.Model):
    my_date = models.DateField()
    
    def get_formatted_date(self):
        return self.my_date.strftime(settings.DATE_FORMAT)




def custom_404(request, exception):
    return render(request, "404.html", status=404)
def clear_coupon_session(request):
    if request.session.get("coupon_applied", False):
        del request.session["coupon_applied"]
        del request.session["coupon_name"]
        del request.session["coupon_discount_percentage"]
        del request.session["discounted_price"]
        messages.warning(request, "Coupon has been removed due to changes in the cart.")


from django.utils import timezone

@never_cache
@login_required(login_url="login")
def shop_cart(request):
    if request.user.is_authenticated:
        user = Customer.objects.get(user=request.user.pk)
        customer = User_Cart.objects.get(customer=user)
        cart_items = CartItem.objects.filter(
            user_cart=customer,
            product__product__is_listed=True,
            product__product__is_deleted=False,
        ).distinct()

        sub_total = 0
        cart_item_offers = []
        for item in cart_items:
            product = item.product.product
            # Fetch active category offer, if any
            category_offer = CategoryOffer.objects.filter(
                category=product.category,
                is_active=True,
                start_date__lte=timezone.now().date(),
                end_date__gte=timezone.now().date()
            ).first()

            # Determine the best discount to apply
            if category_offer and category_offer.discount_percentage > product.percentage:
                offer_percentage = category_offer.discount_percentage
                applied_offer = "Category Offer"
            else:
                offer_percentage = product.percentage
                applied_offer = "Product Offer"

            # Calculate the offer price
            offer_price = product.price - (offer_percentage * product.price / 100)

            # Calculate the total price for this item
            total_price = round(offer_price * item.quantity, 2)
            sub_total += total_price

            # Save the offer information for this item
            cart_item_offers.append({
                "item": item,
                "applied_offer": applied_offer,
                "offer_percentage": offer_percentage,
                "offer_price": offer_price,
                "total_price": total_price,
                "category_offer": category_offer,  # Ensure this is included
            })

        total = sub_total

        total_quantity = sum(i.quantity for i in cart_items)
        if total_quantity >= 5:
            shipping_fee = "Free"
        else:
            shipping_fee = 99

        if shipping_fee == 99:
            total += shipping_fee

        context = {
            "cart_items": cart_items,
            "cart_item_offers": cart_item_offers,
            "sub_total": sub_total,
            "total": total,
            "shipping_fee": shipping_fee,
        }

        return render(request, "shop_cart.html", context)
    else:
        return redirect("login")







"""@never_cache
@login_required(login_url="login")
def shop_cart(request):
    if request.user.is_authenticated:
        user = Customer.objects.get(user=request.user.pk)
        customer = User_Cart.objects.get(customer=user)
        cart_items = CartItem.objects.filter(
            user_cart=customer,
            product__product__is_listed=True,
            product__product__is_deleted=False,
        ).distinct()

        sub_total = sum(item.total_price for item in cart_items)
        total = sub_total

        total_quantity = sum(i.quantity for i in cart_items)
        if total_quantity >= 5:
            shipping_fee = "Free"
        else:
            shipping_fee = 99
        if shipping_fee == 99:
            total += shipping_fee

       

        context = {
            "cart_items": cart_items,
            "sub_total": sub_total,
            "total": total,
            "shipping_fee": shipping_fee,
           
        }

        return render(request, "shop_cart.html", context)
    else:
        return redirect("login")"""


@never_cache
@login_required(login_url="login")
def add_to_cart(request, pro_id):
    if request.method == "POST":
        try:
            # Fetch user
            user = Customer.objects.get(user=request.user)
        except Customer.DoesNotExist:
            messages.error(request, "User information is missing.")
            return redirect("product_detail", pro_id)

        # Get or create a user cart
        user_cart, created = User_Cart.objects.get_or_create(customer=user)
    
        try:
            # Fetch product
            product = ProductColorImage.objects.get(id=pro_id)
        except ProductColorImage.DoesNotExist:
            messages.error(request, "Product does not exist.")
            return redirect("product_detail", pro_id)

        # Validate size and quantity
        selected_size = request.POST.get("size")
        size = ProductSize.objects.filter(
            productcolor=product, size=selected_size
        ).first()

        if not size:
            messages.error(request, "Selected size is not available.")
            return redirect("product_detail", pro_id)

        try:
            quantity = int(request.POST.get("quantity", 0))
            if quantity <= 0:
                raise ValueError("Invalid quantity.")
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("product_detail", pro_id)

        if size.quantity < quantity:
            messages.error(request, "Selected quantity exceeds available stock.")
            return redirect("product_detail", pro_id)

        # Check if the item is already in the cart
        if CartItem.objects.filter(
            user_cart=user_cart, product=product, product_size=selected_size
        ).exists():
            messages.error(request, "Product already in cart.")
            return redirect("product_detail", pro_id)

        # Add item to the cart
        CartItem.objects.create(
            user_cart=user_cart,
            product=product,
            quantity=quantity,
            product_size=selected_size,

        )

        messages.success(request, "Product added to cart.")
        return redirect("shop_cart")

    # Handle GET request
    return redirect("product_detail", pro_id)

@never_cache
@login_required(login_url="login")
def delete_cart_items(request, pro_id):
    try:
        cart_item = CartItem.objects.get(id=pro_id)
        cart_item.delete()
        messages.success(request, "Product removed from cart.")
    except CartItem.DoesNotExist:
        messages.error(request, "Cart item does not exist.")
    return redirect("shop_cart")



logger = logging.getLogger(__name__)  # Set up a logger for error logging

@never_cache
def update_total_price(request):
    if request.method == "POST":
        cart_item_id = request.POST.get("cart_item_id")
        new_quantity = int(request.POST.get("new_quantity"))

        try:
            cart_item = CartItem.objects.get(id=cart_item_id)
            product_size = ProductSize.objects.get(
                productcolor=cart_item.product, size=cart_item.product_size
            )

            if new_quantity > product_size.quantity:
                return JsonResponse(
                    {
                        "error": f"There is only {product_size.quantity} quantity of this product size {cart_item.product_size} available."
                    },
                    status=400,
                )

            cart_item.quantity = new_quantity
            cart_item.save()

            clear_coupon_session(request)

            # Recalculate totals
            user = Customer.objects.get(user=request.user.pk)
            customer_cart = User_Cart.objects.get(customer=user)
            cart_items = CartItem.objects.filter(user_cart=customer_cart).distinct()

            sub_total = sum(item.total_price for item in cart_items)
            total_quantity = sum(item.quantity for item in cart_items)

            if total_quantity >= 5:
                shipping_fee = "Free"
            else:
                shipping_fee = 99

            if shipping_fee == "Free":
                total = sub_total
            else:
                total = sub_total + shipping_fee

            return JsonResponse(
                {
                    "new_total_price": cart_item.total_price,
                    "subtotal": sub_total,
                    "total": total,
                    "shipping_fee": shipping_fee,
                }
            )
        except CartItem.DoesNotExist:
            return JsonResponse({"error": "Cart item does not exist"}, status=404)
        except ProductSize.DoesNotExist:
            return JsonResponse({"error": "Product size does not exist"}, status=404)
        except Exception as e:
            logger.error(f"Error updating total price: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)



def check_stock(request):
    if request.method == "GET":  # Check if the request method is GET
        cart_item_id = request.GET.get("cart_item_id")  # Get cart item ID from the GET data

        # Validate that the cart_item_id is present
        if not cart_item_id:
            return JsonResponse({"error": "Cart item ID is required"}, status=400)  # Return error if cart item ID is missing

        try:
            # Attempt to retrieve the CartItem object based on the cart_item_id
            cart_item = CartItem.objects.get(id=cart_item_id)
        except CartItem.DoesNotExist:
            return JsonResponse({"error": "Cart item does not exist"}, status=404)  # Return error if cart item is not found

        try:
            # Retrieve the ProductSize object that matches the cart item's product and size
            product_size = ProductSize.objects.get(
                productcolor=cart_item.product, size=cart_item.product_size
            )
            return JsonResponse({"available_quantity": product_size.quantity})  # Return the available quantity in JSON format
        except ProductSize.DoesNotExist:
            return JsonResponse({"error": "Product size does not exist"}, status=404)  # Handle case where the product size is missing
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")  # Log the unexpected error
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)  # Return the error message in JSON format

    return JsonResponse({"error": "Invalid request method"}, status=400)  # Handle invalid request methods






#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
@never_cache
def add_address_checkout(request):
    if request.method == "POST":
        user = User.objects.get(pk=request.user.pk)
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        city = request.POST.get("city")
        state = request.POST.get("state")
        country = request.POST.get("country")
        postal_code = request.POST.get("postal_code")
        house_name = request.POST.get("house_name")
        mobile_number = request.POST.get("mobile_number")

        if not all(
            [
                first_name,
                last_name,
                email,
                city,
                state,
                country,
                postal_code,
                house_name,
                mobile_number,
            ]
        ):
            messages.error(request, "Please fill up all the fields.")
            return redirect("checkout")

        # Name validation: only letters and single spaces between words
        name_pattern = r"^[a-zA-Z]+(?:\s[a-zA-Z]+)*$"
       
        if not re.match(name_pattern, first_name):
            messages.error(
                request, "First name must contain only letters and single spaces."
            )
            return redirect("checkout")

        if not re.match(name_pattern, last_name):
            messages.error(
                request, "Last name must contain only letters and single spaces."
            )
            return redirect("checkout")

        # Mobile number length validation
        if len(mobile_number) < 10 or len(mobile_number) > 12:
            messages.error(request, "Mobile number is not valid.")
            return redirect("checkout")

        location_pattern = r"^[a-zA-Z0-9\s\-\/]+$"  # Allows letters, numbers, spaces, hyphens, and slashes
        if not re.match(location_pattern, city):
            messages.error(request, "City name must contain only letters and spaces.")
            return redirect("checkout")

        if not re.match(location_pattern, state):
            messages.error(request, "State name must contain only letters and spaces.")
            return redirect("checkout")

        if not re.match(location_pattern, country):
            messages.error(
                request, "Country name must contain only letters and spaces."
            )
            return redirect("checkout")

        if not re.match(location_pattern, house_name):
            messages.error(request, "House name must contain only letters and spaces.")
            return redirect("checkout")

        # Postal code validation: only digits
        if not postal_code.isdigit():
            messages.error(request, "Postal code must contain only digits.")
            return redirect("checkout")

        address = Address.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            email=email,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            house_name=house_name,
            phone_number=mobile_number,
        )
        messages.success(request, "user address created successfully.")
        return redirect("checkout")

def checkout(request):
    try:
        today = timezone.now()
        if request.user.is_authenticated:
            user = Customer.objects.get(user=request.user.pk)
            cart = CartItem.objects.filter(user_cart__customer=user)

            if not cart.exists():
                messages.error(request, "Your cart is empty.")
                return redirect("shop_cart")

            for item in cart:
                try:
                    product_size = ProductSize.objects.get(
                        productcolor=item.product, size=item.product_size
                    )
                except ProductSize.DoesNotExist:
                    messages.error(
                        request,
                        f"Size {item.product_size} for product {item.product.product.name} not found.",
                    )
                    return redirect("shop_cart")

                if item.quantity > product_size.quantity:
                    messages.error(
                        request,
                        f"Selected quantity for {item.product.product.name} exceeds available stock.",
                    )
                    return redirect("shop_cart")

            sub_total = sum(price.total_price for price in cart)
            total = sub_total
            discount_amount = 0

            cart_qty = sum(item.quantity for item in cart)
            shipping_fee = "Free" if cart_qty > 5 else 99
            total += 0 if cart_qty > 5 else shipping_fee

            coupons = Coupon.objects.filter(
                is_active=True,
                expiry_date__gt=today,
                minimum_amount__lte=total,
                maximum_amount__gte=total,
            )
            
            for i in cart:
                if not i.product.is_listed:
                    messages.error(
                        request,
                        f"Product {i.product.product.name} is not available for checkout.",
                    )
                    return redirect("shop_cart")

            if request.method == "POST":
                get_coupon = request.POST.get("coupon_code")
                action = request.POST.get("action")

                if action == "remove_coupon":
                    if request.session.get("coupon_applied", False):
                        request.session.pop("coupon_applied", None)
                        request.session.pop("coupon_name", None)
                        request.session.pop("coupon_discount_percentage", None)
                        request.session.pop("discounted_price", None)
                        messages.success(request, "Coupon has been removed successfully.")
                    else:
                        messages.error(request, "No coupon has been applied.")
                    return redirect("checkout")

                if get_coupon:
                    if request.session.get("coupon_applied", False):
                        messages.error(request, "You have already applied a Coupon.")
                        return redirect("checkout")

                    cpn = Coupon.objects.filter(
                        coupon_code=get_coupon, is_active=True
                    ).first()

                    if not cpn:
                        messages.error(request, "Invalid coupon code.")
                        return redirect("checkout")

                    if cpn.expiry_date <= today:
                        messages.error(request, "The coupon has expired.")
                        return redirect("checkout")

                    usage_count = Order.objects.filter(
                        customer=user, coupon_name=cpn.coupon_name
                    ).count()

                    if usage_count >= cpn.usage_limit:
                        messages.error(
                            request,
                            "You have already used this coupon the maximum number of times.",
                        )
                        return redirect("checkout")

                    if total >= cpn.minimum_amount and total <= cpn.maximum_amount:
                        discount_amount = (total * cpn.discount_percentage) / 100
                        total -= round(discount_amount)
                        request.session["coupon_applied"] = True
                        request.session["coupon_name"] = cpn.coupon_name
                        request.session["coupon_discount_percentage"] = cpn.discount_percentage
                        request.session["discounted_price"] = round(discount_amount)
                        messages.success(request, "Coupon has been applied successfully.")
                    else:
                        messages.error(
                            request,
                            f"Your total must be between ₹ {cpn.minimum_amount} and ₹ {cpn.maximum_amount} to apply this coupon.",
                        )
                        return redirect("checkout")

            custom = Customer.objects.get(user=request.user.pk)
            user_cart = User_Cart.objects.get(customer=custom)
            cart_items = CartItem.objects.filter(user_cart=user_cart)
            addresses = Address.objects.filter(user=request.user, is_deleted=False)

            context = {
                "cartitems": cart_items,
                "addresses": addresses,
                "total": total,
                "sub_total": sub_total,
                "shipping_fee": shipping_fee,
                "coupons": coupons,
                "discount_amount": round(discount_amount),
                "coupon_applied": request.session.get("coupon_applied", False),
            }

            return render(request, "checkout.html", context)
        else:
            return redirect("login")
    except Exception as e:
        messages.error(request, f"Something went wrong. Please try again. Error: {str(e)}")
        return redirect("checkout")



razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


from django.utils.crypto import get_random_string

def generate_unique_transaction_id():
    while True:
        transaction_id = "WALLET_TRANSFER_" + get_random_string(6, "ABCLMOZ456789")
        if not Wallet_transaction.objects.filter(transaction_id=transaction_id).exists():
            return transaction_id
def generate_tracking_id():
    tk_id = get_random_string(10, "ABCDEFGHIJKLMOZ0123456789")
    while Order.objects.filter(tracking_id=tk_id).exists():
        tk_id = get_random_string(10, "ABCDEFGHIJKLMOZ0123456789")
    return tk_id
def create_order(order_data, cart_items, shipping_address_data):
    order = Order.objects.create(**order_data)
    Shipping_address.objects.create(order=order, **shipping_address_data)
    for cart_item in cart_items:
        order_item = OrderItem.objects.create(
            order=order,
            status="Order Placed",
            product=cart_item.product,
            each_price=cart_item.product.product.offer_price,
            qty=cart_item.quantity,
            size=cart_item.product_size,
        )
        product_size = ProductSize.objects.get(
            productcolor=cart_item.product, size=cart_item.product_size
        )
        product_size.quantity -= cart_item.quantity
        product_size.save()
    return order
def handle_cart_and_coupon(request, coupon_applied, coupon_name, discounted_price):
    if coupon_applied:
        used_coupon = Coupon.objects.filter(coupon_name=coupon_name).first()
        if used_coupon:
            used_coupon.used_count += 1
            used_coupon.save()
    keys_to_delete = [
        "coupon_applied",
        "coupon_name",
        "coupon_discount_percentage",
        "discounted_price",
    ]
    for key in keys_to_delete:
        if key in request.session:
            del request.session[key]
    CartItem.objects.filter(user_cart__customer=Customer.objects.get(user=request.user.pk)).delete()
# Initialize Razorpay client with authentication credentials
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

def initiate_payment(items):
    """
    Initiates a payment transaction with Razorpay for the given items.

    Parameters:
    items (list): A list of dictionaries containing item details. Each dictionary should include 'amount'.

    Returns:
    str: The unique order ID generated by Razorpay.
    """
    
    # Validate that items list is not empty
    if not items:
        raise ValueError("No items provided for payment initiation.")
    
    # Calculate the total amount from the items
    total_amount = sum(item["amount"] for item in items)

    # Prepare data for Razorpay order creation
    data = {
        "currency": "INR",
        "payment_capture": "1",
        "amount": total_amount,  # Use total amount for the entire order
    }
    

    print(f"Total amount for payment: {data['amount']}")
    
    # Create a Razorpay order with the specified data
    try:
        razorpay_order = razorpay_client.order.create(data=data)
        razorpay_order_id = razorpay_order["id"]
    except Exception as e:
        # Log error and raise an exception if order creation fails
        logging.error(f"Error creating Razorpay order: {e}")
        raise

    # Return the Razorpay order ID
    return razorpay_order_id



@transaction.atomic
def place_order(request):
    if request.method == "POST":
        payment_status = request.POST.get("payment_status", "failed")
        address_id = request.POST.get("select_address")
        payment_method = request.POST.get("payment_method")

        if not address_id:
            messages.error(request, "Please select an address.")
            return redirect("checkout")
        if not payment_method:
            messages.error(request, "Please select a Payment Method.")
            return redirect("checkout")

        address = Address.objects.get(id=address_id)
        customer = Customer.objects.get(user=request.user.pk)
        cart = CartItem.objects.filter(user_cart__customer=customer)
        subtotal = sum(item.total_price for item in cart)
        total_qty = sum(item.quantity for item in cart)
       # shipping_fee = 99 if total_qty <= 5 else 0
       
        if total_qty <= 5:
            shipping_fee = 99  # Fixed shipping fee
        else:
            shipping_fee = 0  # Adjust as needed

        total = subtotal + shipping_fee
        total = subtotal + shipping_fee

        tk_id = generate_tracking_id()

        coupon_applied = request.session.get("coupon_applied", False)
        coupon_name = request.session.get("coupon_name")
        coupon_discount_percentage = request.session.get("coupon_discount_percentage", 0)
        discounted_price = request.session.get("discounted_price", 0)

        if coupon_applied:
            total -= discounted_price

        shipping_address_data = {
            'first_name': address.first_name,
            'last_name': address.last_name,
            'email': address.email,
            'phone_number': address.phone_number,
            'house_name': address.house_name,
            'postal_code': address.postal_code,
            'city': address.city,
            'state': address.state,
            'country': address.country,
        }

        if payment_method == "wallet":
            user_customers = customer.user
            wallet = Wallet.objects.get(user=user_customers)
            if wallet.balance < total:
                messages.error(request, "Insufficient balance in your wallet.")
                return redirect("checkout")

            transaction_id = generate_unique_transaction_id()

            payment = Payment.objects.create(
                method_name=payment_method,
                amount=total,
                transaction_id=transaction_id,
                paid_at=timezone.now(),
                pending=False,
                success=True,
            )

            order_data = {
                'customer': customer,
                'address': address,
                'payment_method': payment_method,
                'subtotal': subtotal,
                'shipping_charge': shipping_fee,
                'total': total,
                'paid': True,
                'tracking_id': tk_id,
                'coupon_applied': coupon_applied,
                'coupon_name': coupon_name,
                'coupon_discount_percentage': coupon_discount_percentage,
                'discounted_price': discounted_price,
                'payment_transaction_id': transaction_id,
                'payment': payment,
                'status': "On Progress",
            }
            order = create_order(order_data, cart, shipping_address_data)

            wallet.balance -= total
            wallet.save()

            handle_cart_and_coupon(request, coupon_applied, coupon_name, discounted_price)
            messages.success(request, "Order placed successfully.")
            return redirect("order_detail")

        elif payment_method == "Razorpay":
            # Implement Razorpay payment processing logic here
            if payment_method == "Razorpay":
                items = [{"amount": total * 100}]
                order_id = initiate_payment(items)

            if payment_status == "failed":
                print("payment failed", "====", payment_status)
                payment = Payment.objects.create(
                    method_name=payment_method,
                    amount=total,
                    transaction_id=tk_id,
                    paid_at=timezone.now(),
                    pending=True,
                    success=False,
                    failed=True,
                )
                print(payment, "this is the mayment object")
                order = Order.objects.create(
                    customer=customer,
                    address=address,
                    payment_method=payment_method,
                    subtotal=subtotal,
                    shipping_charge=shipping_fee,
                    total=total,
                    paid=False,
                    tracking_id=tk_id,
                    coupon_applied=coupon_applied,
                    coupon_name=coupon_name,
                    coupon_discount_percentage=coupon_discount_percentage,
                    discounted_price=discounted_price,
                    payment=payment,
                    status="Payment Failed",
                )

                shipping_address = Shipping_address.objects.create(
                    order=order,
                    first_name=address.first_name,
                    last_name=address.last_name,
                    email=address.email,
                    phone_number=address.phone_number,
                    house_name=address.house_name,
                    postal_code=address.postal_code,
                    city=address.city,
                    state=address.state,
                    country=address.country,
                )
                for cart_item in cart:
                    OrderItem.objects.create(
                        order=order,
                        status="Pending",
                        product=cart_item.product,
                        each_price=cart_item.product.product.offer_price,
                        qty=cart_item.quantity,
                        size=cart_item.product_size,
                    )
                    product_size = ProductSize.objects.get(
                        productcolor=cart_item.product, size=cart_item.product_size
                    )
                    product_size.quantity -= cart_item.quantity
                    product_size.save()

                cart.delete()

                keys_to_delete = [
                    "coupon_applied",
                    "coupon_name",
                    "coupon_discount_percentage",
                    "discounted_price",
                ]
                for key in keys_to_delete:
                    if key in request.session:
                        del request.session[key]

                messages.error(
                    request,
                    "Payment initiation failed. Order has been created with Payment Failed status.",
                )
                created_order = Order.objects.get(id=order.id)
                print(f"Order ID: {created_order.id}, Status: {created_order.status}")
                return redirect("payment_failure")
            else:

                payment = Payment.objects.create(
                    method_name=payment_method,
                    amount=total,
                    transaction_id=order_id,
                    paid_at=timezone.now(),
                    pending=False,
                    success=True,
                )

                order = Order.objects.create(
                    customer=customer,
                    address=address,
                    payment_method=payment_method,
                    subtotal=subtotal,
                    shipping_charge=shipping_fee,
                    total=total,
                    paid=True,
                    tracking_id=tk_id,
                    coupon_applied=coupon_applied,
                    coupon_name=coupon_name,
                    coupon_discount_percentage=coupon_discount_percentage,
                    discounted_price=discounted_price,
                    payment_transaction_id=order_id,
                    payment=payment,
                    status="On Progress",
                )
                Shipping_address.objects.create(
                    order=order,
                    first_name=address.first_name,
                    last_name=address.last_name,
                    email=address.email,
                    phone_number=address.phone_number,
                    house_name=address.house_name,
                    postal_code=address.postal_code,
                    city=address.city,
                    state=address.state,
                    country=address.country,
                )
                for cart_item in cart:
                    OrderItem.objects.create(
                        order=order,
                        status="Order Placed",
                        product=cart_item.product,
                        each_price=cart_item.product.product.offer_price,
                        qty=cart_item.quantity,
                        size=cart_item.product_size,
                    )
                    product_size = ProductSize.objects.get(
                        productcolor=cart_item.product, size=cart_item.product_size
                    )
                    product_size.quantity -= cart_item.quantity
                    product_size.save()

                cart.delete()

                keys_to_delete = [
                    "coupon_applied",
                    "coupon_name",
                    "coupon_discount_percentage",
                    "discounted_price",
                ]
                for key in keys_to_delete:
                    if key in request.session:
                        del request.session[key]

                return redirect("order_detail")
            

        elif payment_method == "COD":
            order_data = {
                'customer': customer,
                'address': address,
                'payment_method': payment_method,
                'subtotal': subtotal,
                'shipping_charge': shipping_fee,
                'total': total,
                'tracking_id': tk_id,
                'coupon_applied': coupon_applied,
                'coupon_name': coupon_name,
                'coupon_discount_percentage': coupon_discount_percentage,
                'discounted_price': discounted_price,
                'status': "On Progress",
            }
            create_order(order_data, cart, shipping_address_data)
            handle_cart_and_coupon(request, coupon_applied, coupon_name, discounted_price)
            messages.success(request, "Order placed successfully.")
            return redirect("order_detail")

    else:
        messages.error(request, "Invalid request method.")
        return redirect("checkout")











def payment_success(request):
    if request.method == "POST":
        order_id = request.POST.get("razorpay_order_id")
        payment_id = request.POST.get("order_id")
        signature = request.POST.get("razorpay_signature")
    else:
        messages.error(
            request, "Something went wrong in the payment section please try again."
        )

        return redirect("checkout")
    params_dict = {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": signature,
    }

    try:
        razorpay_client.utility.verify_payment_signature(params_dict)
        return render(request, "op.html")
    except razorpay.errors.SignatureVerificationError as e:
        return redirect("payment_failure")


# _________________________________________________________________________________________________________________________________________
def order_detail(request):
    if request.user.is_authenticated:
        return render(request, "op.html")
    else:
        messages.error(request, "Please login first.")
        return redirect("login")


def payment_failure(request):
    return render(request, "order_payment_failed.html")


def view_all_order(request):
    if request.user.is_authenticated:
        customer = Customer.objects.get(user=request.user)
        orders = Order.objects.filter(customer=customer).order_by("-created_at")
        shipping_addresses = (
            Shipping_address.objects.filter(order__in=orders)
            .annotate(num_orders=Count("order"))
            .distinct()
        )

        return render(
            request,
            "view_all_order.html",
            {"orders": orders, "order_addresses": shipping_addresses},
        )
    else:
        return redirect("login")


def view_order(request, ord_id):
    if request.user.is_authenticated:
        customer = get_object_or_404(Customer, user=request.user)
        order = get_object_or_404(Order, pk=ord_id)
        
        items = OrderItem.objects.filter(order=order).order_by("-created_at")
        context = {"order": order, "items": items}
        return render(request, "view_order.html", context)
    else:
        return redirect("login")



"""@never_cache
def view_status(request, order_id):
    if request.user.is_authenticated:
        customer = Customer.objects.get(user=request.user.pk)
        try:
            order_items = OrderItem.objects.get(pk=order_id)
        except OrderItem.DoesNotExist:
            return redirect("index")

        # Check if the order belongs to the customer
        if order_items.order.customer == customer:
            # Calculate subtotal
            subtotal = OrderItem.objects.filter(order=order_items.order).aggregate(
                total=Sum(F('each_price') * F('qty'))
            )['total'] or 0

            # Get shipping charge from the order
            shipping_charge = order_items.order.shipping_charge or 0

            # Calculate total price
            total_price = subtotal
            total_final_price = subtotal + shipping_charge

            # Check if a coupon was applied
            coupon_applied = order_items.order.coupon_applied
            discounted_total = order_items.order.discounted_price if coupon_applied else 0
            final_total_price = total_final_price - discounted_total

            # Get the current date
            currentTime = timezone.now().date()

            # Status information
            status_info = {
                "Order Placed": {"color": "#009608", "label": "Order Placed"},
                "Shipped": {"color": "#009608", "label": "Shipped"},
                "Out for Delivery": {"color": "#009608", "label": "Out for Delivery"},
                "Delivered": {"color": "#009608", "label": "Delivered"},
            }
            
            context = {
                "order_items": order_items,
                "status_info": status_info,
                "currentTime": currentTime,
                "subtotal": subtotal,
                "shipping_charge": shipping_charge,
                "total_final_price": final_total_price,
                "discounted_total": discounted_total,
                "coupon_applied": coupon_applied
            }
            return render(request, "view_status.html", context)
        else:
            return redirect("index")
    else:
        return redirect("login")"""

@never_cache
def view_status(request, order_id):
    if request.user.is_authenticated:
        customer = Customer.objects.get(user=request.user.pk)
        order_items = OrderItem.objects.get(pk=order_id)
        
        if order_items.order.customer == customer:
            total_price = order_items.each_price * order_items.qty
            currentTime = timezone.now().date()

            status_info = {
                "Order Placed": {"color": "#009608", "label": "Order Placed"},
                "Shipped": {"color": "#009608", "label": "Shipped"},
                "Out for Delivery": {"color": "#009608", "label": "Out for Delivery"},
                "Delivered": {"color": "#009608", "label": "Delivered"},
            }
              #
            context = {
                "order_items": order_items,
                "status_info": status_info,
                "currentTime": currentTime,
                "total_price": total_price,
            
            }
            return render(request, "view_status.html", context)
        else:
            return redirect("index")
    else:
        return redirect("login")
# views.py
from django.shortcuts import render, get_object_or_404
from .models import Payment

def payment_status(request, payment_id):
    payment = get_object_or_404(Payment, pk=payment_id)
    context = {'payment': payment}
    return render(request, 'view_status.html', context)





def request_cancel_order(request, order_id):
    print(order_id)
    if request.user.is_authenticated:
        order_item = OrderItem.objects.get(pk=order_id)
        total_price = order_item.each_price * order_item.qty

        if order_item.order.customer.user == request.user:
            order_item.request_cancel = True
            order_item.save()
            return render(
                request,
                "view_status.html",
                {"order_items": order_item, "total_price": total_price},
            )
    return redirect("login")



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import OrderItem
from .forms import ReturnOrderForm

def request_return_product(request, orderItem_id):
    if not request.user.is_authenticated:
        return redirect("login")

    seven_days = timezone.now() - timedelta(days=7)
    order_item = get_object_or_404(OrderItem, pk=orderItem_id)
    total_price = order_item.each_price * order_item.qty

    # Check if return is eligible
    if order_item.created_at <= seven_days or order_item.status != "Delivered":
        messages.info(request, "You can only request a return within 7 days of delivery.")
        return redirect("view_status", orderItem_id=orderItem_id)

    if request.method == "POST":
        form = ReturnOrderForm(request.POST)
        if form.is_valid():
            order_item.request_return = True
            order_item.return_reason = form.cleaned_data["reason"]  # Save the return reason
            order_item.save()
            messages.success(request, "Your return request has been submitted.")
            return redirect("view_status", orderItem_id)
    else:
        form = ReturnOrderForm()

    context = {
        "order_items": order_item,
        "total_price": total_price,
        "form": form,
        "currentTime": timezone.now(),  # Pass current time for comparison in the template
    }
    return render(request, "view_status.html", context)

def process_item_return_and_refund(request, order_item_id):
    try:
        order_item = OrderItem.objects.get(id=order_item_id)
        if order_item.status == "Delivered":
            # Update to Returned
            order_item.status = "Returned"
            order_item.is_refunded = True  # Set refunded to True at the same time
            order_item.save()
            messages.success(request, "The item has been marked as returned and refunded.")
        else:
            messages.error(request, "The item is not eligible for return and refund.")
    except OrderItem.DoesNotExist:
        messages.error(request, "Order item not found.")
    return redirect('my_orders')
from django.shortcuts import get_object_or_404, redirect


from django.shortcuts import get_object_or_404, redirect
from .models import OrderItem

def refund_order(request, order_item_id):
    order_item = get_object_or_404(OrderItem, id=order_item_id)
    if not order_item.is_refunded:
        order_item.is_refunded = True
        order_item.save()
        # Optionally, handle wallet transactions or other logic here
    return redirect('admin_order', order_id=order_item.order.id)  # Pass the order_id here




"""from .forms import ReturnOrderForm

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import OrderItem
from .forms import ReturnOrderForm  # Import the form

def request_return_product(request, orderItem_id):
    if not request.user.is_authenticated:
        return redirect("login")

    seven_days = timezone.now() - timedelta(days=7)
    order_item = get_object_or_404(OrderItem, pk=orderItem_id)
    total_price = order_item.each_price * order_item.qty

    # Check if return is eligible
    if order_item.created_at <= seven_days or order_item.status != "Delivered":
        messages.info(request, "You can only request a return within 7 days of delivery.")
        return redirect("view_status", orderItem_id=orderItem_id)

    if request.method == "POST":
        form = ReturnOrderForm(request.POST)
        if form.is_valid():
            order_item.request_return = True
            order_item.return_reason = form.cleaned_data["reason"]  # Save the return reason
            order_item.save()
            messages.success(request, "Your return request has been submitted.")
            return redirect("view_status",orderItem_id)
    else:
        form = ReturnOrderForm()

    context = {
        "order_items": order_item,
        "total_price": total_price,
        "form": form,
        "currentTime": timezone.now(),  # Pass current time for comparison in the template
    }
    return render(request, "view_status.html", context)"""


from django.shortcuts import render


def search_products(request):
    query = request.GET.get('query', '')
    category_id = request.GET.get('category', None)
    brand_id = request.GET.get('brand', None)

    # Start with a base queryset
    products = Product.objects.filter(is_deleted=False, is_listed=True)

    # Filter by query
    if query:
        products = products.filter(name__icontains=query)
    
    # Filter by category
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Filter by brand
    if brand_id:
        products = products.filter(brand_id=brand_id)

    # Prepare context for rendering
    context = {
        'products': products,
        'query': query,
        'categories': Category.objects.all(),
        'brands': Brand.objects.all(),
    }

    return render(request, 'search.html', context)













"""def request_return_product(request, orderItem_id):
    if request.user.is_authenticated:
        print("hellooooooo order id",orderItem_id)
        seven_days = timezone.now() - timedelta(days=7)
        order_item = OrderItem.objects.get(pk=orderItem_id)
        total_price = order_item.each_price * order_item.qty
        print("order item......",order_item)
        if order_item.created_at > seven_days and order_item.status == "Delivered":
            print("reached here")
            order_item.request_return = True
            order_item.save()
            print("item return request generated",order_item.request_return)
            context = {
                "order_items": order_item,
                "total_price": total_price,
            }
            return render(
                request,
                "view_status.html",
                {"order_items": order_item, "total_price": total_price},
            )
        else:
            messages.info(
                request, "You can only request for return product within 7 days."
            )
            return redirect("view_status", orderItem_id)
    return redirect("login")"""







@csrf_exempt
def retry_payment(request):
    if request.method == "POST":
        order_id = request.POST.get("order_id")
        payment_id = request.POST.get("razorpay_payment_id")
        try:
            # Update payment and order details
            order = Order.objects.get(id=order_id)
            payment = order.payment
            payment.transaction_id = payment_id
            payment.paid_at = timezone.now()
            payment.pending = False
            payment.success = True
            payment.failed = False
            payment.save()

            order.status = "On Progress"
            order.payment_transaction_id = payment_id
            order.paid = True
            order.save()
            items = OrderItem.objects.filter(order=order)
            for i in items:
                i.status = "Order Placed"
                i.save()

            return JsonResponse({"status": "success"})
        except Order.DoesNotExist:
            return JsonResponse({"status": "failure", "message": "Order not found"})
        except Exception as e:
            return JsonResponse({"status": "failure", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request "})








#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! WISHLIST !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

def wishlist_view(request):
    if request.user.is_authenticated:
        customer=Customer.objects.get(user=request.user.pk)
        wished_products=WishList.objects.filter(customer=customer)
        
        context ={
            "wished_products":wished_products,
            

        }
        return render(request,"wishlist.html",context)
    else:
        return render("login")



def wishlist_add(request, pro_id):
    if request.user.is_authenticated:
        # Get the logged-in customer. Assuming `Customer` is related to the user.
        customer = get_object_or_404(Customer, user=request.user)

        # Fetch the product using the product ID
        product = get_object_or_404(ProductColorImage, id=pro_id)

        # Check if the wishlist entry already exists
        if WishList.objects.filter(customer=customer, product=product).exists():
            messages.error(request, "Product already in wishlist")
            return redirect("product_detail", product_id=pro_id)

        # Create the wishlist item if it doesn't exist
        wishlist_item, created = WishList.objects.get_or_create(
            customer=customer, product=product, size="S", qty=1
        )

        if created:
            messages.success(request, "Product added to wishlist.")
        else:
            messages.info(request, "Product already in wishlist.")

        return redirect("product_detail", product_id=pro_id)

    else:
        return redirect("login")


def wishlist_del(request, pro_id):
    if request.user.is_authenticated:
        customer = Customer.objects.get(user=request.user.pk)
        WishList.objects.filter(id=pro_id, customer=customer).delete()
        messages.success(request, "Product removed from wishlist.")
        return redirect("wishlist_view")
    else:
        return redirect("login")





















































#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

"""from django.db import transaction
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from .models import Address, Customer, CartItem, Wallet, Payment, Order, Shipping_address, OrderItem, ProductSize

@transaction.atomic
def place_order(request):
    if request.method == "POST":
        payment_status = request.POST.get("payment_status", "failed")
        address_id = request.POST.get("select_address")
        payment_method = request.POST.get("payment_method")

        if not address_id:
            messages.error(request, "Please select an address.")
            return redirect("checkout")
        if not payment_method:
            messages.error(request, "Please select a Payment Method.")
            return redirect("checkout")

        try:
            address = get_object_or_404(Address, id=address_id)
            customer = get_object_or_404(Customer, user=request.user.pk)
            cart = CartItem.objects.filter(user_cart__customer=customer)
            subtotal = sum(item.total_price for item in cart)
            total_qty = sum(item.quantity for item in cart)

            shipping_fee = 99 if total_qty <= 5 else 0
            total = subtotal + shipping_fee

            tk_id = generate_tracking_id()

            coupon_applied = request.session.get("coupon_applied", False)
            coupon_name = request.session.get("coupon_name")
            coupon_discount_percentage = request.session.get("coupon_discount_percentage", 0)
            discounted_price = request.session.get("discounted_price", 0)

            if coupon_applied:
                total -= discounted_price

            shipping_address_data = {
                'first_name': address.first_name,
                'last_name': address.last_name,
                'email': address.email,
                'phone_number': address.phone_number,
                'house_name': address.house_name,
                'postal_code': address.postal_code,
                'city': address.city,
                'state': address.state,
                'country': address.country,
            }

            if payment_method == "wallet":
                return process_wallet_payment(request, customer, total, tk_id, address, cart, shipping_address_data, coupon_applied, coupon_name, coupon_discount_percentage, discounted_price)

            elif payment_method == "Razorpay":
                return process_razorpay_payment(request, payment_status, total, tk_id, address, cart, customer, shipping_address_data, coupon_applied, coupon_name, coupon_discount_percentage, discounted_price)

            elif payment_method == "COD":
                return process_cod_payment(customer, subtotal, shipping_fee, total, tk_id, address, cart, shipping_address_data, coupon_applied, coupon_name, coupon_discount_percentage, discounted_price)

        except Exception as e:
            transaction.set_rollback(True)
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect("checkout")

    else:
        messages.error(request, "Invalid request method.")
        return redirect("checkout")


def process_wallet_payment(request, customer, total, tk_id, address, cart, shipping_address_data, coupon_applied, coupon_name, coupon_discount_percentage, discounted_price):
    user_customers = customer.user
    wallet = Wallet.objects.get(user=user_customers)
    if wallet.balance < total:
        messages.error(request, "Insufficient balance in your wallet.")
        return redirect("checkout")

    transaction_id = generate_unique_transaction_id()

    payment = Payment.objects.create(
        method_name="wallet",
        amount=total,
        transaction_id=transaction_id,
        paid_at=timezone.now(),
        pending=False,
        success=True,
    )

    order_data = {
        'customer': customer,
        'address': address,
        'payment_method': "wallet",
        'subtotal': sum(item.total_price for item in cart),
        'shipping_charge': 99 if sum(item.quantity for item in cart) <= 5 else 0,
        'total': total,
        'paid': True,
        'tracking_id': tk_id,
        'coupon_applied': coupon_applied,
        'coupon_name': coupon_name,
        'coupon_discount_percentage': coupon_discount_percentage,
        'discounted_price': discounted_price,
        'payment_transaction_id': transaction_id,
        'payment': payment,
        'status': "On Progress",
    }
    create_order(order_data, cart, shipping_address_data)

    wallet.balance -= total
    wallet.save()

    handle_cart_and_coupon(request, coupon_applied, coupon_name, discounted_price)
    messages.success(request, "Order placed successfully.")
    return redirect("order_detail")


def process_razorpay_payment(request, payment_status, total, tk_id, address, cart, customer, shipping_address_data, coupon_applied, coupon_name, coupon_discount_percentage, discounted_price):
    order_id = initiate_payment([{"amount": total * 100}])

    if payment_status == "failed":
        return handle_payment_failure(customer, address, total, tk_id, "Razorpay", cart, shipping_address_data, coupon_applied, coupon_name, coupon_discount_percentage, discounted_price)

    else:
        payment = Payment.objects.create(
            method_name="Razorpay",
            amount=total,
            transaction_id=order_id,
            paid_at=timezone.now(),
            pending=False,
            success=True,
        )

        order_data = {
            'customer': customer,
            'address': address,
            'payment_method': "Razorpay",
            'subtotal': sum(item.total_price for item in cart),
            'shipping_charge': 99 if sum(item.quantity for item in cart) <= 5 else 0,
            'total': total,
            'paid': True,
            'tracking_id': tk_id,
            'coupon_applied': coupon_applied,
            'coupon_name': coupon_name,
            'coupon_discount_percentage': coupon_discount_percentage,
            'discounted_price': discounted_price,
            'payment_transaction_id': order_id,
            'payment': payment,
            'status': "On Progress",
        }
        create_order(order_data, cart, shipping_address_data)

        handle_cart_and_coupon(request, coupon_applied, coupon_name, discounted_price)
        return redirect("order_detail")


def process_cod_payment(customer, subtotal, shipping_fee, total, tk_id, address, cart, shipping_address_data, coupon_applied, coupon_name, coupon_discount_percentage, discounted_price):
    order_data = {
        'customer': customer,
        'address': address,
        'payment_method': "COD",
        'subtotal': subtotal,
        'shipping_charge': shipping_fee,
        'total': total,
        'tracking_id': tk_id,
        'coupon_applied': coupon_applied,
        'coupon_name': coupon_name,
        'coupon_discount_percentage': coupon_discount_percentage,
        'discounted_price': discounted_price,
        'status': "On Progress",
    }
    create_order(order_data, cart, shipping_address_data)

    handle_cart_and_coupon(request, coupon_applied, coupon_name, discounted_price)
    messages.success(request, "Order placed successfully.")
    return redirect("order_detail")


def handle_payment_failure(customer, address, total, tk_id, payment_method, cart, shipping_address_data, coupon_applied, coupon_name, coupon_discount_percentage, discounted_price):
    payment = Payment.objects.create(
        method_name=payment_method,
        amount=total,
        transaction_id=tk_id,
        paid_at=timezone.now(),
        pending=True,
        success=False,
        failed=True,
    )

    order = Order.objects.create(
        customer=customer,
        address=address,
        payment_method=payment_method,
        subtotal=sum(item.total_price for item in cart),
        shipping_charge=99 if sum(item.quantity for item in cart) <= 5 else 0,
        total=total,
        paid=False,
        tracking_id=tk_id,
        coupon_applied=coupon_applied,
        coupon_name=coupon_name,
        coupon_discount_percentage=coupon_discount_percentage,
        discounted_price=discounted_price,
        payment=payment,
        status="Payment Failed",
    )

    create_shipping_address(order, shipping_address_data, cart)

    cart.delete()

    delete_coupon_session_data(request)

    messages.error(request, "Payment initiation failed. Order has been created with Payment Failed status.")
    return redirect("payment_failure")


def create_order(order_data, cart, shipping_address_data):
    order = Order.objects.create(**order_data)
    create_shipping_address(order, shipping_address_data, cart)
    return order


def create_shipping_address(order, shipping_address_data, cart):
    Shipping_address.objects.create(
        order=order,
        **shipping_address_data,
    )
    for cart_item in cart:
        OrderItem.objects.create(
            order=order,
            status="Order Placed",
            product=cart_item.product,
            each_price=cart_item.product.product.offer_price,
            total_price=cart_item.total_price,
            quantity=cart_item.quantity,
        )
        update_stock(cart_item)


def update_stock(cart_item):
    product_size = get_object_or_404(ProductSize, product_color=cart_item.product_color, size=cart_item.size)
    product_size.stock -= cart_item.quantity
    product_size.save()


def handle_cart_and_coupon(request, coupon_applied, coupon_name, discounted_price):
    CartItem.objects.filter(user_cart__customer=request.user).delete()
    if coupon_applied:
        Coupon.objects.filter(name=coupon_name).delete()
    delete_coupon_session_data(request)


def delete_coupon_session_data(request):
    request.session.pop("coupon_applied", None)
    request.session.pop("coupon_name", None)
    request.session.pop("coupon_discount_percentage", None)
    request.session.pop("discounted_price", None)

def generate_unique_transaction_id():
    return f"{timezone.now().strftime('%Y%m%d%H%M%S')}{str(request.user.id).zfill(6)}"

def generate_tracking_id():
    return f"TK-{timezone.now().strftime('%Y%m%d%H%M%S')}{str(request.user.id).zfill(6)}"""

