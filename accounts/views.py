import re
import random
from .models import *
from cart_app.models import *
from admin_app.models import *
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from datetime import datetime, timedelta
from django.contrib import messages
from ecommerse.settings import EMAIL_HOST_USER
from django.db.models import Q 
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.http import  JsonResponse
from django.core.exceptions import ValidationError
from django.views.decorators.cache import never_cache
from django.contrib.auth.hashers import check_password
from django.contrib.auth import authenticate, login as auth_login 
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate, login, logout, get_backends
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import render, get_object_or_404
from admin_app.models import ProductColorImage
from cart_app.models import  User_Cart, CartItem
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F, DecimalField, ExpressionWrapper, Q
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
import pdfkit

# Import your models
from cart_app.models import OrderItem, Customer, ProductColorImage  # Update model imports as needed


PRODUCT_PER_PAGE = 9

def clear_coupon_session(request):
    if request.session.get("coupon_applied", False):
        del request.session["coupon_applied"]
        del request.session["coupon_name"]
        del request.session["coupon_discount_percentage"]
        del request.session["discounted_price"]
        messages.warning(request, "Coupon has been removed due to changes in the cart.")


def validate_register(request):
    field_name = request.POST.get("field_name")
    field_value = request.POST.get("field_value")
    response = {"valid": True, "error": ""}

    try:
        if field_name in ["f_name", "l_name"]:
            if not field_value.isalpha():
                raise ValidationError("Name must contain only letters")
            elif len(field_value) < 2:
                raise ValidationError("Name must be at least 2 characters long")

        if field_name == "username":
            if User.objects.filter(username=field_value).exists():
                raise ValidationError("The username is already taken")
            if not field_value.strip():
                raise ValidationError("The username is not valid")

        elif field_name == "email":
            if User.objects.filter(email=field_value).exists():
                raise ValidationError("This email is already registered")
            if not re.match(r"^[\w\.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", field_value):
                raise ValidationError("Please enter a valid email address")

        elif field_name == "pass1":
            validate_password(field_value, user=User)
            if len(field_value) < 6:
                raise ValidationError("The password should be at least 6 characters")
            if not any(char.isupper() for char in field_value):
                raise ValidationError(
                    "Password must contain at least one uppercase letter"
                )
            if not any(char.islower() for char in field_value):
                raise ValidationError(
                    "Password must contain at least one lowercase letter"
                )
            if not any(char.isdigit() for char in field_value):
                raise ValidationError("Password must contain at least one digit")

    except ValidationError as e:
        response["valid"] = False
        response["error"] = ", ".join(e.messages)

    return JsonResponse(response)


@never_cache
def register(request):
    try:
        if request.user.is_authenticated:
            return redirect("index")

        referral_code = request.GET.get("ref")

        if request.method == "POST":
            first_name = request.POST.get("f_name")
            last_name = request.POST.get("l_name")
            username = request.POST.get("username")
            email = request.POST.get("email")
            password1 = request.POST.get("pass1")
            password2 = request.POST.get("pass2")
            referral_code_manual = request.POST.get("referral_code")

            if referral_code_manual:
                referral_code = referral_code_manual

            if referral_code:
                if not Customer.objects.filter(referral_code=referral_code).exists():
                    return JsonResponse(
                        {"success": False, "message": "Invalid Referral Code"}
                    )
                else:
                    coustomer = Customer.objects.get(referral_code = referral_code)
                    coustomer.referral_count += 1
                    coustomer.save()

                    wallet = coustomer.user.wallet
                    wallet.balance += 100
                    wallet.save()

                    request.session["referral_code"] = referral_code

            if not all([first_name, last_name, username, email, password1, password2]):
                return JsonResponse(
                    {"success": False, "message": "Please fill up all the fields."}
                )

            if User.objects.filter(username=username).exists():
                return JsonResponse(
                    {"success": False, "message": "The username is already taken"}
                )

            if len(password1) < 6:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "The password should be at least 6 characters",
                    }
                )

            if password1 != password2:
                return JsonResponse(
                    {"success": False, "message": "The passwords do not match"}
                )

            if not first_name.isalpha():
                return JsonResponse(
                    {
                        "success": False,
                        "message": "First name must contain only letters",
                    }
                )

            if not last_name.isalpha():
                return JsonResponse(
                    {"success": False, "message": "Last name must contain only letters"}
                )

            try:
                validate_password(password1, user=User)
            except ValidationError as e:
                return JsonResponse({"success": False, "message": str(e)})

            if User.objects.filter(email=email).exists():
                return JsonResponse(
                    {"success": False, "message": "This email is already registered"}
                )

            with transaction.atomic():
                user = User.objects.create_user(
                    first_name=first_name,
                    last_name=last_name,
                    username=username,
                    email=email,
                    password=password1,
                )
                user.save()

                user_profile = User_profile.objects.create(user=user, is_verified=False)
                user_profile.user.is_active = False
                user_profile.save()

                user_id = user_profile.user.pk
                otp, otp_generated_at = generate_otp_and_send_email(email)
                print("This is the call for otp", otp, otp_generated_at)
                print(otp, otp_generated_at)
                store_user_data_in_session(
                    request, user_id, otp, email, otp_generated_at
                )

            return JsonResponse({"success": True, "message": f"Welcome {first_name}"})
        else:
            form_data = request.session.get("form_data", {})
            return render(request, "register.html", {"form_data": form_data})

    except ValidationError as e:
        return JsonResponse({"success": False, "message": str(e)})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})

def generate_otp_and_send_email(email):
    # Generate a random 4-digit OTP.
    otp = random.randint(1000, 9999)
    print(otp)
    # Get the current time in ISO format.
    otp_generated_at = timezone.now().isoformat()

    # Send the OTP to the user's email.
    send_mail(
        subject="Your OTP for verification",
        message=f"Your OTP for verification is: {otp}",
        
        from_email=EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=True,
    )
    return otp, otp_generated_at  # Return the OTP and the time it was generated.


def store_user_data_in_session(request, user_id, otp, email, otp_generated_at):
    # Store the user data and OTP information in the session for later verification.
    request.session["user_data"] = {
        "user_id": user_id,
        "otp": otp,
        "email": email,
        "otp_generated_at": otp_generated_at,
    }


def otp(request):
    try:
        if request.user.is_authenticated:
            return redirect("index")

        email = request.session.get("user_data", {}).get("email", "")
        if request.method == "POST":
            otp_digits = [request.POST.get(f"digit{i}") for i in range(1, 5)]
            if None in otp_digits:
                messages.error(request, "Invalid OTP format, please try again.")
                return redirect("my_otp")

            entered_otp = int("".join(otp_digits))
            user_data = request.session.get("user_data", {})
            stored_otp = user_data.get("otp")
            otp_generated_at = user_data.get("otp_generated_at", "")
            user_id = user_data.get("user_id", "")

            try:
                otp_generated_at_datetime = datetime.fromisoformat(otp_generated_at)
            except ValueError:
                otp_generated_at_datetime = None

            if (
                otp_generated_at_datetime
                and otp_generated_at_datetime + timedelta(minutes=5) < timezone.now()
            ):
                messages.error(request, "OTP has expired. Please try again.")
                return redirect("register")

            if str(entered_otp) == str(stored_otp):
                user = User.objects.get(id=user_id)
                user_profile = User_profile.objects.get(user=user)
                user_profile.is_verified = True
                user_profile.user.is_active = True
                user_profile.save()

                del request.session["user_data"]

                backend = get_backends()[0]
                user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
                messages.success(request, f"{user.username} created successfully.")
                login(request, user)
                return redirect("index")
            else:
                messages.error(request, "Invalid OTP, try again.")
                return redirect("my_otp")

        return render(request, "otp.html", {"email": email})

    except Exception as e:
        messages.error(request, str(e))
        return redirect("register")



@never_cache
def resend_otp(request):
    try:
        user_data = request.session.get("user_data", {})
        email = user_data.get("email", "")
        user_id = user_data.get("user_id", "")

        if not user_id or not isinstance(user_id, int):
            messages.error(request, "Invalid session data. Please register again.")
            return redirect("register")

        new_otp, otp_generated_now = generate_otp_and_send_email(email)
        user_data["otp"] = new_otp
        user_data["otp_generated_at"] = otp_generated_now
        request.session["user_data"] = user_data

        messages.success(request, "New OTP sent successfully")
        return redirect("my_otp")

    except Exception as e:
        messages.error(request, str(e))
        return redirect("my_otp")

@ csrf_exempt
@never_cache
def log_in(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if request.user.is_superuser:
            messages.error(request, "invalid.")
            return redirect("login")

        elif user is not None:
            auth_login(request, user)
            return redirect("index")
        
        else:
            messages.error(request, "The username or password is incorrect.")
            return redirect("login")

    return render(request, "log.html")


@never_cache
def verify_email(request):
    try:
        if request.user.is_authenticated:
            return redirect("index")

        if request.method == "POST":
            email = request.POST.get("email")

            if User.objects.filter(email=email).exists():
                otp, otp_generated_at = generate_otp_and_send_email(email)
                request.session["verifyotp"] = {
                    "otp": otp,
                    "email": email,
                    "otp_generated_at": otp_generated_at,
                }
                return redirect("verify_otp")
            else:
                messages.error(request, "This email does not exists in our database.")
                return redirect("verify_email")

    except Exception as e:
        messages.error(request, str(e))
    return render(request, "pass_reset/verify_email.html")


@never_cache
def verify_otp(request):
    try:
        email = request.session.get("verifyotp", {}).get("email", "")

        if request.method == "POST":
            otp_digits = [request.POST.get(f"otp{i}") for i in range(1, 5)]

            if None in otp_digits:
                messages.error(request, "Invalid OTP format, please try again.")
                return redirect("verify_email")

            entered_otp = int("".join(otp_digits))
            storedotp = request.session.get("verifyotp", {}).get("otp")
            otp_generated_at_str = request.session.get("verifyotp", {}).get(
                "otp_generated_at", ""
            )

            try:
                otp_generated_at_datetime = datetime.fromisoformat(otp_generated_at_str)
            except ValueError:
                otp_generated_at_datetime = None

            if (
                otp_generated_at_datetime
                and otp_generated_at_datetime + timedelta(minutes=2) < timezone.now()
            ):
                messages.error(request, "OTP has expired. Please try again.")
                return redirect("verify_email")

            if str(entered_otp) == str(storedotp):
                return redirect("reset_pass")

            else:
                messages.error(request, "Incorrect OTP, please try again.")
                return redirect("verify_otp")

        return render(request, "pass_reset/verify_otp.html", {"email": email})

    except Exception as e:
        messages.error(request, str(e))
        return redirect("verify_otp")


@never_cache
def reset_pass(request):
    email = request.session.get("verifyotp", {}).get("email", "")

    if request.method == "POST":
        new_password = request.POST.get("newpassword")
        confirm_password = request.POST.get("confirmpassword")

        if new_password != confirm_password:
            messages.error(request, "The passwords do not match")
            return redirect("reset_pass")

        try:
            validate_password(new_password)
        except ValidationError as e:
            messages.error(request, ", ".join(e))
            return redirect("reset_pass")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "User does not exist")
            return redirect("reset_pass")

        user = User.objects.get(email=email)
        user.set_password(confirm_password)
        user.save()

        del request.session["verifyotp"]

        messages.success(request, "Password reset successfully")
        return redirect("login")

    return render(request, "pass_reset/reset_pass.html")


@never_cache
def log_out(request):
    logout(request)
    return redirect("index")

#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx LOG IN SECTION END XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!USER INTERFACE PRODUCT SIDE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1111111


@never_cache
def index(request):
   
    products_color = ProductColorImage.objects.filter(product__is_deleted=False)
    products = Product.objects.filter(is_listed=True)
    cart_count = 0
    if request.user.is_authenticated:
        try:
            products_color = ProductColorImage.objects.filter(product__is_deleted=False)
            products = Product.objects.filter(is_listed=True)
            user_cart = User_Cart.objects.get(customer__user=request.user)
            cart_count = CartItem.objects.filter(user_cart=user_cart).count()

        except User_Cart.DoesNotExist:
            pass
        context = {
            "products_color": products_color,
            "products": products,
            "cart_count":cart_count,
           
        }
        
        return render(request, "index.html", context)
    return render(request, "index.html")




@never_cache
def product_detail(request, product_id):
    # Fetch the product color variant based on the product_id
    products_color = get_object_or_404(ProductColorImage, id=product_id)
    # Fetch all color variants for the product
    product_colors = products_color.product.color_image.all()
    
    # Fetch the category of the current product
    product_category = products_color.product.category
    print(product_category)
    # Fetch related products within the same category, excluding the current one
    related_product = ProductColorImage.objects.filter(
        Q(product__category=product_category) & Q(is_listed=True)
    ).exclude(id=product_id)
    # Fetch product sizes related to the current product color image
    product_sizes = products_color.size.all()  # Access sizes related to the product color image
    # Initialize cart count
    cart_count = 0
    if request.user.is_authenticated:
        try:
            user_cart = User_Cart.objects.get(customer__user=request.user)
            cart_count = CartItem.objects.filter(user_cart=user_cart).count()
        except User_Cart.DoesNotExist:
            pass
    # Calculate the offer percentage based on the `percentage` field
    products_with_percentage = Product.objects.annotate(
        offer_percentage=ExpressionWrapper(
            (F('price') - (F('price') * (F('percentage') / 100))),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    )
# Define color mapping
    color_map = {
        'Red': '#FF0000',
        'Green': '#00FF00',
        'Blue': '#0000FF',
        'Yellow': '#FFFF00',
        'Cyan': '#00FFFF',
        'Magenta': '#FF00FF',
        'Black': '#000000',
        'White': '#FFFFFF',
        'Gray': '#808080',
        'Purple': '#800080',
        'Orange': '#FFA500',
        'Pink': '#FFC0CB',
        # Add more colors as needed
    }
    
    for color in product_colors:
        color.color_code = color_map.get(color.color, '#ffffff')  # Default to white if not found

    # Prepare context for rendering the template
    context = {
        "products_color": products_color,
        "product_colors": product_colors,
        "product_sizes": product_sizes,
        "related_product": related_product,
        'cart_count': cart_count,
        'products_with_percentage': products_with_percentage,
        'products': Product.objects.filter(is_listed=True).distinct()
    }
    
    return render(request, "product_detail.html", context)
from django.db.models import Q



def autocomplete_suggestions(request):
    query = request.GET.get('query', '').strip()
    suggestions = {
        'products': [],
        'brands': [],
        'categories': []
    }
    
    if query:
        # Get product suggestions
        products = Product.objects.filter(name__icontains=query)[:3]
        suggestions['products'] = [{'id': product.id, 'name': product.name} for product in products]
        
        # Get brand suggestions
        brands = Brand.objects.filter(name__icontains=query)[:3]
        suggestions['brands'] = [{'id': brand.id, 'name': brand.name} for brand in brands]
        
        # Get category suggestions
        categories = Category.objects.filter(name__icontains=query)[:3]
        suggestions['categories'] = [{'id': category.id, 'name': category.name} for category in categories]
    
    return JsonResponse(suggestions)




@never_cache
def shop_page(request):
    # Get filters and search query from request
    search_query = request.GET.get("search", "")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    ordering = request.GET.get("ordering", "name")
    selected_category_ids = request.GET.getlist("category")
    selected_brand_ids = request.GET.getlist("brand")
    selected_color_ids = request.GET.getlist("color")

    # Base queryset for products, filtering out deleted categories and colors
    products_color = ProductColorImage.objects.filter(
        Q(product__category__is_deleted=False) & Q(is_deleted=False)
    )

    # Apply search query to filter by product name or description
    if search_query:
        products_color = products_color.filter(
            Q(product__name__icontains=search_query) |
            Q(product__description__icontains=search_query)
        )

    # Apply price range filters if provided
    if min_price:
        try:
            min_price = float(min_price)
        except ValueError:
            min_price = None
    if max_price:
        try:
            max_price = float(max_price)
        except ValueError:
            max_price = None

    if min_price is not None and max_price is not None:
        products_color = products_color.annotate(
            calculated_offer_price=ExpressionWrapper(
                F("product__price") - (F("product__price") * F("product__percentage") / 100),
                output_field=DecimalField()
            )
        ).filter(
            calculated_offer_price__gte=min_price,
            calculated_offer_price__lte=max_price
        )

    # Apply category filter
    if selected_category_ids:
        products_color = products_color.filter(product__category__id__in=selected_category_ids)

    # Apply brand filter
    if selected_brand_ids:
        products_color = products_color.filter(product__brand__id__in=selected_brand_ids)

    # Apply color filter
    if selected_color_ids:
        products_color = products_color.filter(color__in=selected_color_ids)

    # Apply ordering
    if ordering == "name":
        products_color = products_color.order_by("product__name")
    elif ordering == "-name":
        products_color = products_color.order_by("-product__name")
    elif ordering == "price":
        products_color = products_color.annotate(
            calculated_offer_price=ExpressionWrapper(
                F("product__price") - (F("product__price") * F("product__percentage") / 100),
                output_field=DecimalField()
            )
        ).order_by("calculated_offer_price")
    elif ordering == "-price":
        products_color = products_color.annotate(
            calculated_offer_price=ExpressionWrapper(
                F("product__price") - (F("product__price") * F("product__percentage") / 100),
                output_field=DecimalField()
            )
        ).order_by("-calculated_offer_price")
    elif ordering == "created_at":
        products_color = products_color.order_by("product__created_at")

    # Pagination
    page = request.GET.get("page", 1)
    product_Paginator = Paginator(products_color, 9)  # 9 products per page
    
    try:
        products = product_Paginator.page(page)
    except PageNotAnInteger:
        products = product_Paginator.page(1)
    except EmptyPage:
        products = product_Paginator.page(product_Paginator.num_pages)

    # Additional context data
    categories = Category.objects.filter(is_listed=True, is_deleted=False)
    colors = ProductColorImage.objects.filter(is_listed=True, is_deleted=False).distinct("color")
    brands = Brand.objects.filter(is_listed=True)

    context = {
        "products_color": products,
        "categories": categories,
        "page_obj": products,
        "is_paginated": product_Paginator.num_pages > 1,
        "paginator": product_Paginator,
        "brands": brands,
        "colors": colors,
        "search_query": search_query,
        "selected_category": selected_category_ids,
        "selected_brand": selected_brand_ids,
        "selected_color": selected_color_ids,
    }
    
    return render(request, "shop.html", context)

@never_cache  # Decorator to prevent the filtered products page from being cached
def filtered_products_cat(request):
    print("Filtered products by category, brand, and color")  # Debugging statement
    print("Request:", request)  # Debugging statement to show the request
    
    # Retrieve filter parameters from the request
    selected_category_ids = request.GET.getlist("category")
    selected_brand_ids = request.GET.getlist("brand")
    selected_color_ids = request.GET.getlist("color")

    print("Selected category:", selected_category_ids)  # Debugging statement
    print("Selected brand:", selected_brand_ids)  # Debugging statement
    print("Selected color:", selected_color_ids)  # Debugging statement

    # Convert selected IDs to integers and validate them
    selected_category_ids = [int(category_id) for category_id in selected_category_ids if category_id.isdigit()]
    selected_brand_ids = [int(brand_id) for brand_id in selected_brand_ids if brand_id.isdigit()]
    selected_color_ids = [color_id for color_id in selected_color_ids if color_id]

    # Fetch categories, brands, and colors that are listed and not deleted
    categories = Category.objects.filter(is_listed=True)
    brands = Brand.objects.filter(is_listed=True)
    colors = ProductColorImage.objects.filter(is_deleted=False, is_listed=True).distinct('color')

    products = ProductColorImage.objects.all()  # Initialize the products query

    # Apply filters based on the selected categories, brands, and colors
    if selected_category_ids:
        products = products.filter(product__category__in=selected_category_ids)
    if selected_brand_ids:
        products = products.filter(product__brand__in=selected_brand_ids)
    if selected_color_ids:
        products = products.filter(color__in=selected_color_ids)

    # Apply combined filters if multiple filters are selected
    if selected_category_ids and selected_color_ids:
        products = products.filter(
            Q(product__category__in=selected_category_ids)
            & Q(color__in=selected_color_ids)
        ).distinct()
    if selected_category_ids and selected_brand_ids:
        products = products.filter(
            Q(product__category__in=selected_category_ids)
            & Q(product__brand__in=selected_brand_ids)
        ).distinct()
    if selected_brand_ids and selected_color_ids and selected_category_ids:
        products = products.filter(
            Q(product__category__in=selected_category_ids)
            & Q(product__brand__in=selected_brand_ids)
            & Q(color__in=selected_color_ids)
        ).distinct()

    print("Products:", products)  # Debugging statement to show the filtered products

    # Prepare the context dictionary to pass to the template
    context = {
        "categories": categories,
        "brands": brands,
        "colors": colors,
        "products_color": products,
        "selected_category": selected_category_ids,
        "selected_brand": selected_brand_ids,
        "selected_color": selected_color_ids,
    }
    
    return render(request, "shop.html", context)  # Render the shop page template with the filtered products

def product_filter_view(request):
    brands = Brand.objects.all()  # Get all brands
    selected_brands = request.GET.getlist('brand')  # Get the selected brands from the request

    products = Product.objects.all()  # Initialize the products query
    if selected_brands:  # If any brands are selected
        products = products.filter(brand__id__in=selected_brands)  # Filter the products by the selected brands

    # Prepare the context dictionary to pass to the template
    context = {
        'brands': brands,
        'selected_brand': selected_brands,
        'products': products,
    }
    
    return render(request, 'your_template.html', context)  # Render the template with the filtered products












######################################################################### PROFILE SECTION #######################################################################################

def profile(request):
    if request.user.is_authenticated:
        user = request.user
    cart_count = 0  # Initialize cart count to 0
    if request.user.is_authenticated:  # Check if the user is authenticated
        try:
            user_cart = User_Cart.objects.get(customer__user=request.user)  # Try to get the user's cart
            cart_count = CartItem.objects.filter(user_cart=user_cart).count()  # Count the number of items in the cart
        except User_Cart.DoesNotExist:  # If the cart does not exist, pass
            pass
        customer = Customer.objects.get(user=user.id)
        context = {"user": user, "customer": customer,'cart_count':cart_count}
        return render(request, "personal_info.html", context)

    else:
        return redirect("login")
        


def edit_profile(request, info_id):
    if request.user.is_authenticated:
        user = request.user
        try:
            customer = Customer.objects.get(id=info_id)
        except Customer.DoesNotExist:
            messages.error(request, "Customer not found.")
            return redirect("profile")

        if request.method == "POST":
            try:
                first_name = request.POST.get("first_name")
                last_name = request.POST.get("last_name")
                email = request.POST.get("email")
                gender = request.POST.get("gender")
                phone_number = request.POST.get("phone_number")

                if User.objects.filter(email=email).exclude(id=user.id).exists():
                    messages.error(request, "Email already in use.")
                    return redirect("edit_profile", info_id=customer.id)

                if not phone_number or len(phone_number) < 10:
                    messages.error(request, "Invalid mobile number.")
                    return redirect("edit_profile", info_id=customer.id)

                customer.user.first_name = first_name
                customer.user.last_name = last_name
                customer.user.email = email
                customer.gender = gender
                customer.phone_number = phone_number
                customer.user.save()
                customer.save()

                messages.success(request, "Profile updated successfully.")
                return redirect(profile)
            except Exception as e:
                messages.error(
                    request, "An error occurred while updating your profile."
                )
                return redirect("edit_profile", info_id=customer.id)

        context = {"user": user, "customer": customer}
        return render(request, "edit_personalinfo.html", context)
















def change_password(request, pass_id):
    if request.user.is_authenticated:
        user = User.objects.get(id=pass_id)
        if request.method == "POST":
            current_password = request.POST.get("current_password")
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            if not check_password(current_password, user.password):
                messages.error(request, "Current password is incorrect.")
                return redirect("change_password", pass_id=user.id)

            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return redirect("change_password", pass_id=user.id)
            if len(new_password) < 8:
                messages.error(
                    request, "New password must be at least 8 characters long."
                )
                return redirect("change_password", pass_id=user.id)

            user.set_password(new_password)
            user.save()
            messages.success(request, "Your password was successfully updated!")
            return redirect("profile")
        context = {"user": user, "customer": Customer.objects.get(user=user)}
    return render(request, "personal_info.html", context)

def address(request):
    try:
        if request.user.is_authenticated:
            address_list = Address.objects.filter(user=request.user.pk, is_deleted=False)
            next_page = request.GET.get("next", "")
            context = {"address": address_list, "next_page": next_page}
            return render(request, "address.html", context)
        else:
            return redirect("login")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return render(request, "address.html")



def add_address(request):
    # Check if the user is authenticated
    if request.user.is_authenticated:
        # Handle form submission
        if request.method == "POST":
            user = request.user
            
            # Extract form data from the POST request
            form_data = {
                "first_name": request.POST.get("first_name"),
                "last_name": request.POST.get("last_name"),
                "email": request.POST.get("email"),
                "city": request.POST.get("city"),
                "state": request.POST.get("state"),
                "country": request.POST.get("country"),
                "postal_code": request.POST.get("postal_code"),
                "house_name": request.POST.get("house_name"),
                "mobile_number": request.POST.get("mobile_number"),
            }

            # Check if all fields are filled
            if not all(form_data.values()):
                messages.error(request, "Please fill up all the fields.")
                return redirect("add_address")

            # Regular expressions for validating form fields
            name_pattern = r"^[a-zA-Z]+(?:\s[a-zA-Z]+)*$"  # Allows letters and single spaces
            location_pattern = r"^[a-zA-Z\s]+$"  # Allows letters and spaces
            house_name_pattern = r"^[a-zA-Z0-9\s\-\/]+$"  # Allows letters, numbers, spaces, hyphens, and slashes

            # Validate first name
            if not re.match(name_pattern, form_data["first_name"]):
                messages.error(request, "First name must contain only letters and single spaces.")
                return redirect("add_address")

            # Validate last name
            if not re.match(name_pattern, form_data["last_name"]):
                messages.error(request, "Last name must contain only letters and single spaces.")
                return redirect("add_address")

            # Validate mobile number
            if len(form_data["mobile_number"]) < 10 or len(form_data["mobile_number"]) > 12:
                messages.error(request, "Mobile number is not valid.")
                return redirect("add_address")

            # Validate city
            if not re.match(location_pattern, form_data["city"]):
                messages.error(request, "City name must contain only letters and spaces.")
                return redirect("add_address")

            # Validate state
            if not re.match(location_pattern, form_data["state"]):
                messages.error(request, "State name must contain only letters and spaces.")
                return redirect("add_address")

            # Validate country
            if not re.match(location_pattern, form_data["country"]):
                messages.error(request, "Country name must contain only letters and spaces.")
                return redirect("add_address")

            # Validate house name
            if not re.match(house_name_pattern, form_data["house_name"]):
                messages.error(request, "House name must contain only letters, numbers, spaces, hyphens, or slashes.")
                return redirect("add_address")

            # Validate postal code
            if not form_data["postal_code"].isdigit():
                messages.error(request, "Postal code must contain only digits.")
                return redirect("add_address")

            # Create a new Address object and save it to the database
            Address.objects.create(
                user=user,
                first_name=form_data["first_name"],
                last_name=form_data["last_name"],
                email=form_data["email"],
                city=form_data["city"],
                state=form_data["state"],
                country=form_data["country"],
                postal_code=form_data["postal_code"],
                house_name=form_data["house_name"],
                phone_number=form_data["mobile_number"],
            )
            messages.success(request, "User address created successfully.")
            return redirect("checkout")
    
    # Render the address form template if not POST request
    return render(request, "add_address.html")


def edit_address(request, address_id):
    if request.user.is_authenticated:
        try:
            address = Address.objects.get(id=address_id)
            if request.method == "POST":
                form_data = {
                    "first_name": request.POST.get("first_name"),
                    "last_name": request.POST.get("last_name"),
                    "email": request.POST.get("email"),
                    "city": request.POST.get("city"),
                    "state": request.POST.get("state"),
                    "country": request.POST.get("country"),
                    "postal_code": request.POST.get("postal_code"),
                    "house_name": request.POST.get("house_name"),
                    "mobile_number": request.POST.get("mobile_number"),
                }

                if not all(form_data.values()):
                    messages.error(request, "Please fill up all the fields.")
                    return redirect("edit_address", address_id=address_id)

                if len(form_data["mobile_number"]) < 10 or len(form_data["mobile_number"]) > 12:
                    messages.error(request, "Mobile number is not valid.")
                    return redirect("edit_address", address_id=address_id)
                # Update the address object with new data from the form submission

                address.first_name = form_data["first_name"]
                address.last_name = form_data["last_name"]
                address.email = form_data["email"]
                address.city = form_data["city"]
                address.state = form_data["state"]
                address.country = form_data["country"]
                address.postal_code = form_data["postal_code"]
                address.house_name = form_data["house_name"]
                address.phone_number = form_data["mobile_number"]
                address.save()

                messages.success(request, "Address updated successfully.")
                return redirect("address")
            
            context = {"address": address}
            return render(request, "edit_address.html", context)

        except Address.DoesNotExist:
            messages.error(request, "Address not found.")
            return redirect("address")

    return redirect("login")

def delete_address(request, address_id):
    try:
        if request.user.is_authenticated:
            address = Address.objects.get(id=address_id)
            address.is_deleted = True
            address.save()
            messages.success(request, "Address deleted successfully.")
            return redirect("address")
        else:
            return redirect("login")
    except Address.DoesNotExist:
        messages.error(request, "Address not found.")
        return redirect("address")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect("address")

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!END PROFILE SECTION !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1
def wallet_view(request):
    # Check if the user is authenticated
    if request.user.is_authenticated:
        # Get or create a Wallet object for the current user
        # If the wallet exists, it is retrieved; if not, a new one is created
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        
        # Retrieve all wallet transactions associated with the user's wallet
        # Transactions are ordered by transaction time in descending order
        wallet_transactions = Wallet_transaction.objects.filter(wallet=wallet).order_by(
            "-transaction_time"
        )
        
        # Prepare the context dictionary to pass to the template
        context = {
            "wallet": wallet,                      # The user's wallet object
            "wallet_transactions": wallet_transactions  # The user's wallet transactions
        }
        
        # Render the 'wallet.html' template with the provided context
        return render(request, "wallet.html", context)
    else:
        # If the user is not authenticated, redirect them to the login page
        return redirect("login")

    
def referral(request):
    if request.user.is_authenticated:
        user = request.user
        customer = Customer.objects.get(user=user)
        referral_code = customer.referral_code
        amount = customer.referral_count * 100
        sign_up_url = reverse("register")

        referral_link = request.build_absolute_uri(
            sign_up_url + f"?ref={referral_code}"
        )
        return render(
            request,
            "refferral.html",
            {"customer": customer, "amount": amount, "referral_link": referral_link},
        )
    else:
        return redirect("login")





def invoice(request, product_id):
    if request.user.is_authenticated:
        try:
            # Fetch the current customer and their related order items
            user = get_object_or_404(Customer, user=request.user)
            order_items = get_object_or_404(OrderItem, id=product_id, order__customer=user)

            # Calculate the subtotal of the order
            sub_total = order_items.product.product.offer_price * order_items.qty

            # Initialize discount and shipping fee
            discount_amount = 0
            shipping_fee = 0

            # Fetch the order to check if any coupon was applied
            order = order_items.order
            if order.coupon_name:
                try:
                    coupon = Coupon.objects.get(coupon_name=order.coupon_name, is_active=True)
                    discount_amount = (sub_total * coupon.discount_percentage) / 100
                except Coupon.DoesNotExist:
                    discount_amount = 0

            # Apply shipping fee logic
            cart_qty = order_items.qty
            shipping_fee = 0 if cart_qty > 5 else 99

            # Calculate final total
            total = sub_total - discount_amount + shipping_fee

            # Fetch the address associated with the user
            address = get_object_or_404(Address, user=request.user, is_deleted=False)

            # Define the seller's name
            seller_name = "SARAM"

            # Create the context for rendering the template
            context = {
                "order_items": order_items,
                "sub_total": sub_total,
                "discount_amount": discount_amount,
                "shipping_fee": shipping_fee,
                "total": total,
                "customer_details": {
                    "first_name": address.first_name,
                    "last_name": address.last_name,
                    "email": address.email,
                    "house_name": address.house_name,
                    "street_name": address.street_name,
                    "city": address.city,
                    "state": address.state,
                    "postal_code": address.postal_code,
                    "country": address.country,
                    "phone_number": address.phone_number,
                },
                "seller_name": seller_name,
            }

            # Render the invoice HTML with the context data
            html_string = render_to_string("invoices.html", context)

            # Define the correct path for wkhtmltopdf based on your environment
            path_to_wkhtmltopdf = '/usr/bin/wkhtmltopdf'  # For the server (Linux)

            # Configure pdfkit with the correct path to wkhtmltopdf
            config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
            
            # Generate the PDF from the rendered HTML string
            pdf = pdfkit.from_string(html_string, False, configuration=config)

            # Create the HTTP response to serve the PDF file
            response = HttpResponse(pdf, content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="invoice.pdf"'

            return response

        except (OrderItem.DoesNotExist, Address.DoesNotExist) as e:
            # Log the exception or handle it as needed
            return HttpResponse("Error generating invoice. Please ensure all data is correct.")
    else:
        return redirect("login")




"""import pdfkit

def invoice(request, product_id):
    if request.user.is_authenticated:
        # Fetch the current customer and their related order items
        user = Customer.objects.get(user=request.user)
        order_items = OrderItem.objects.get(id=product_id, order__customer=user)

        # Calculate the subtotal of the order
        sub_total = order_items.product.product.offer_price * order_items.qty
        
        # Initialize discount and shipping fee
        discount_amount = 0
        shipping_fee = 0

        # Fetch the order to check if any coupon was applied
        order = order_items.order
        if order.coupon_name:
            try:
                coupon = Coupon.objects.get(coupon_name=order.coupon_name, is_active=True)
                if coupon:
                    discount_amount = (sub_total * coupon.discount_percentage) / 100
            except Coupon.DoesNotExist:
                discount_amount = 0

        # Apply shipping fee logic (this is an example; adjust as needed)
        cart_qty = order_items.qty
        shipping_fee = 0 if cart_qty > 5 else 99  # Free shipping if cart_qty > 5

        # Calculate final total
        total = sub_total - discount_amount + shipping_fee

        # Fetch the address associated with the user (assuming one address per user)
        try:
            address = Address.objects.get(user=request.user, is_deleted=False)
            address_details = {
                "first_name": address.first_name,
                "last_name": address.last_name,
                "email": address.email,
                "house_name": address.house_name,
                "street_name": address.street_name,
                "city": address.city,
                "state": address.state,
                "postal_code": address.postal_code,
                "country": address.country,
                "phone_number": address.phone_number,
            }
        except Address.DoesNotExist:
            address_details = {}

        # Define the seller's name
        seller_name = "SARAM"

        # Create the context for rendering the template
        context = {
            "order_items": order_items,
            "sub_total": sub_total,
            "discount_amount": discount_amount,
            "shipping_fee": shipping_fee,
            "total": total,
            "customer_details": address_details,
            "seller_name": seller_name,
        }

        # Render the invoice HTML with the context data
        html_string = render_to_string("invoices.html", context)

        # Define the configuration for pdfkit to generate a PDF
        config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")

        # Generate the PDF from the rendered HTML string
        pdf = pdfkit.from_string(html_string, False, configuration=config)

        # Create the HTTP response to serve the PDF file
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = 'filename="invoice.pdf"'

        return response
    else:
        return redirect("login")
import pdfkit

# Define the path to wkhtmltopdf
path_to_wkhtmltopdf = '/usr/bin/wkhtmltopdf'
config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)

# Generate PDF with the correct configuration
pdfkit.from_url('http://example.com', 'output.pdf', configuration=config)"""
