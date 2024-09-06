import re
import json
import random
import pdfkit
from .models import *
from cart_app.models import *
from admin_app.models import *
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.dispatch import receiver
from django.core.mail import send_mail
from datetime import datetime, timedelta
from django.contrib import messages, auth
from ecommerse.settings import EMAIL_HOST_USER
from django.db.models import Q, FloatField
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.db.models.signals import post_save
from django.core.validators import validate_email
from validate_email_address import validate_email
from django.http import HttpResponse, JsonResponse
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.db.models import F, ExpressionWrapper, DecimalField
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate, login, logout, get_backends
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


PRODUCT_PER_PAGE = 9


@csrf_exempt
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




@never_cache  # This decorator prevents the response from being cached.
def register(request):
    try:
        # If the user is already authenticated, redirect them to the home page.
        if request.user.is_authenticated:
            return redirect("index")

        if request.method == "POST":
            # Retrieve form data from the POST request.
            first_name = request.POST.get("f_name")
            last_name = request.POST.get("l_name")
            username = request.POST.get("username")
            email = request.POST.get("email")
            password1 = request.POST.get("pass1")
            password2 = request.POST.get("pass2")

            # Ensure all required fields are filled out.
            if not all([first_name, last_name, username, email, password1, password2]):
                return JsonResponse(
                    {"success": False, "message": "Please fill up all the fields."}
                )

            # Check if the username is already taken.
            if User.objects.filter(username=username).exists():
                return JsonResponse(
                    {"success": False, "message": "The username is already taken"}
                )

            # Check if the password is at least 6 characters long.
            if len(password1) < 6:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "The password should be at least 6 characters",
                    }
                )

            # Ensure that both password fields match.
            if password1 != password2:
                return JsonResponse(
                    {"success": False, "message": "The passwords do not match"}
                )

            # Ensure that the first name contains only letters.
            if not first_name.isalpha():
                return JsonResponse(
                    {
                        "success": False,
                        "message": "First name must contain only letters",
                    }
                )

            # Ensure that the last name contains only letters.
            if not last_name.isalpha():
                return JsonResponse(
                    {"success": False, "message": "Last name must contain only letters"}
                )

            # Validate the password using Django's built-in validators.
            try:
                validate_password(password1, user=User)
            except ValidationError as e:
                return JsonResponse({"success": False, "message": str(e)})

            # Check if the email is already registered.
            if User.objects.filter(email=email).exists():
                return JsonResponse(
                    {"success": False, "message": "This email is already registered"}
                )

            # Create the user and their profile in an atomic transaction.
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

                store_user_data_in_session(
                    request, user_id, otp, email, otp_generated_at
                )

            return JsonResponse({"success": True, "message": f"Welcome {first_name}"})

        else:
            # If the request method is GET, render the registration form, prefilled with any saved form data.
            form_data = request.session.get("form_data", {})
            return render(request, "register.html", {"form_data": form_data})

    except ValidationError as e:
        # Handle any validation errors that occur and return them as JSON responses.
        return JsonResponse({"success": False, "message": str(e)})
    except Exception as e:
        # Handle any other exceptions and return them as JSON responses.
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


@never_cache
def log_in(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
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
            user_data = request.session.get("user_data", {})
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
    products_color = ProductColorImage.objects.get(id=product_id)
    product_category = products_color.product.category
    related_product = ProductColorImage.objects.filter(
        Q(product__category=product_category) & Q(is_listed=True)
    ).exclude(id=product_id)
    cart_count = 0
    if request.user.is_authenticated:
        try:
            user_cart = User_Cart.objects.get(customer__user=request.user)
            cart_count = CartItem.objects.filter(user_cart=user_cart).count()
        except User_Cart.DoesNotExist:
            pass

    context = {"products_color": products_color, "related_product": related_product,'cart_count': cart_count,}
    return render(request, "product_detail.html", context)




@never_cache
def shop_page(request):
    ordering = request.GET.get("ordering", "name")
    products_color = ProductColorImage.objects.filter(
        Q(product__category__is_deleted=False) & Q(is_deleted=False)
    )
    cart_count = 0
    if request.user.is_authenticated:
        try:
            user_cart = User_Cart.objects.get(customer__user=request.user)
            cart_count = CartItem.objects.filter(user_cart=user_cart).count()
        except User_Cart.DoesNotExist:
            pass


    colors = ProductColorImage.objects.filter(
        is_listed=True, is_deleted=False
    ).distinct("color")
    brands = Brand.objects.filter(is_listed=True)
    categories_filter = request.GET.getlist("category")
    if categories_filter:
        category_filters = Q()
        for category in categories_filter:
            category_filters |= Q(product__category__name=category)
        products_color = products_color.filter(category_filters)

    if ordering == "name":
        products_color = products_color.order_by("product__name")
    elif ordering == "-name":
        products_color = products_color.order_by("-product__name")
   
    elif ordering == "-price":
        products_color = sorted(
            products_color, key=lambda x: x.product.price, reverse=True
        )
    elif ordering == "created_at":
        products_color = products_color.order_by("product__created_at")

    page = request.GET.get("page", 1)
    product_Paginator = Paginator(products_color, PRODUCT_PER_PAGE)

    try:
        products = product_Paginator.page(page)
    except PageNotAnInteger:
        products = product_Paginator.page(1)
    except EmptyPage:
        products = product_Paginator.page(product_Paginator.num_pages)

    categories = Category.objects.filter(is_listed=True, is_deleted=False)

    context = {
        "products_color": products,
        "categories": categories,
        "page_obj": products,
        "is_paginated": product_Paginator.num_pages > 1,
        "paginator": product_Paginator,
        "brands": brands,
        "colors": colors,
        'cart_count': cart_count,
    }
    return render(request, "shop.html", context)


# ___________________________________________________________________________________________________________________________________________________






@never_cache
def filtered_products_cat(request):
    print("Filtered products by category, brand, and color")
    print("Request:", request)
    selected_category_ids = request.GET.getlist("category")
    selected_brand_ids = request.GET.getlist("brand")
    selected_color_ids = request.GET.getlist("color")

    print("Selected category:", selected_category_ids)
    print("Selected brand:", selected_brand_ids)
    print("Selected color:", selected_color_ids)

    categories = Category.objects.filter(is_listed=True)
    brands = Brand.objects.filter(is_listed=True)
    colors = ProductColorImage.objects.filter(
        is_deleted=False, is_listed=True
    ).distinct("color")

    products = ProductColorImage.objects.filter(
        Q(product__category__in=selected_category_ids)
        | Q(product__brand__in=selected_brand_ids)
        | Q(color__in=selected_color_ids)
    ).distinct()

    if selected_category_ids and selected_color_ids:
        products = ProductColorImage.objects.filter(
            Q(product__category__in=selected_category_ids)
            & Q(color__in=selected_color_ids)
        ).distinct()
    if selected_category_ids and selected_brand_ids:
        products = ProductColorImage.objects.filter(
            Q(product__category__in=selected_category_ids)
            & Q(product__brand__in=selected_brand_ids)
        ).distinct()
    if selected_brand_ids and selected_color_ids and selected_category_ids:
        products = ProductColorImage.objects.filter(
            Q(product__category__in=selected_category_ids)
            & Q(product__brand__in=selected_brand_ids)
            & Q(color__in=selected_color_ids)
        ).distinct()

    selected_category_ids = [int(category_id) for category_id in selected_category_ids]
    selected_brand_ids = [int(brand_id) for brand_id in selected_brand_ids]
    selected_color_ids = [color for color in selected_color_ids]

    print("Products:", products)

    context = {
        "categories": categories,
        "brands": brands,
        "colors": colors,
        "products_color": products,
        "selected_category": selected_category_ids,
        "selected_brand": selected_brand_ids,
        "selected_color": selected_color_ids,
    }
    return render(request, "shop.html", context)

def products_by_color(request, color):
    # Filter products by the selected color
    products = ProductColorImage.objects.filter(color=color, is_listed=True)
    context = {
        'products': products,
        'selected_color': color
    }
    return render(request, '', context)


@never_cache
def filter_products_by_price(request):
    try:
        if request.method == "GET":
            min_price = request.GET.get("min", 500)[1:]
            max_price = request.GET.get("max", 50000)[1:]

            print("Minimum price:", min_price)
            print("Maximum price:", max_price)

            product_color_images = ProductColorImage.objects.filter(
                product__is_listed=True, product__is_deleted=False
            )
            categories = Category.objects.filter(is_listed=True)
            brands = Brand.objects.filter(is_listed=True)
            colors = ProductColorImage.objects.filter(
                is_deleted=False, is_listed=True
            ).distinct("color")

            # Annotate the queryset with the offer price
            product_color_images = product_color_images.annotate(
                calculated_offer_price=ExpressionWrapper(
                    F("product__price")
                    - (F("product__percentage") * F("product__price") / 100),
                    output_field=FloatField(),
                )
            )

            # Filter product color images based on the offer price
            if min_price is not None:
                product_color_images = product_color_images.filter(
                    calculated_offer_price__gte=min_price
                )
            if max_price is not None:
                product_color_images = product_color_images.filter(
                    calculated_offer_price__lte=max_price
                )

                print("Filtered products:", product_color_images)
            context = {
                "products_color": product_color_images,
                "categories": categories,
                "brands": brands,
                "colors": colors,
            }
            return render(request, "shop.html", context)
    except Exception as e:
        print("Exception:", e)
        messages.error(request, "Something went wrong please try again.")
        return redirect("index")





#____________________________________________________x_________________________________________________________
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
from django.shortcuts import render
from admin_app.models import ProductColorImage, ProductSize

def products_by_color(request, color):
    # Filter products by the selected color
    products_by_color = ProductColorImage.objects.filter(color__name=color, is_listed=True).select_related('product')

    # Group products by their color for better organization in the template
    product_dict = {}
    for product_color in products_by_color:
        product = product_color.product
        if product not in product_dict:
            product_dict[product] = {
                'color_images': [],
                'sizes': []
            }
        product_dict[product]['color_images'].append(product_color)
        # Collect sizes for this product
        product_sizes = ProductSize.objects.filter(productcolor__product=product)
        for size in product_sizes:
            if size.size not in product_dict[product]['sizes']:
                product_dict[product]['sizes'].append(size.size)

    context = {
        'products_by_color': product_dict,
        'selected_color': color
    }
    return render(request, 'products_by_color.html', context)

def product_images_api(request):
    product_id = request.GET.get('product_id')
    color_code = request.GET.get('color_code')

    if product_id and color_code:
        product_images = ProductColorImage.objects.filter(
            product_id=product_id,
            color__color_code=color_code
        ).values('image1', 'image2', 'image3', 'image4').first()
        
        if product_images:
            return JsonResponse({'image': product_images['image1']})
    
    return JsonResponse({'image': ''}, status=404)















################################################################################################################################################################
# _____________________________________________________________________________________________________________________________________________________________
#------------------------------------------------------------------__________________________________________________________________

def profile(request):
    if request.user.is_authenticated:
        user = request.user
        customer = Customer.objects.get(user=user.id)
        context = {"user": user, "customer": customer}
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
    if request.user.is_authenticated:
        if request.method == "POST":
            user = request.user
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
                return redirect("add_address")

            # Validate each field
            name_pattern = r"^[a-zA-Z]+(?:\s[a-zA-Z]+)*$"
            location_pattern = r"^[a-zA-Z\s]+$"
            house_name_pattern = r"^[a-zA-Z0-9\s\-\/]+$"

            if not re.match(name_pattern, form_data["first_name"]):
                messages.error(request, "First name must contain only letters and single spaces.")
                return redirect("add_address")

            if not re.match(name_pattern, form_data["last_name"]):
                messages.error(request, "Last name must contain only letters and single spaces.")
                return redirect("add_address")

            if len(form_data["mobile_number"]) < 10 or len(form_data["mobile_number"]) > 12:
                messages.error(request, "Mobile number is not valid.")
                return redirect("add_address")

            if not re.match(location_pattern, form_data["city"]):
                messages.error(request, "City name must contain only letters and spaces.")
                return redirect("add_address")

            if not re.match(location_pattern, form_data["state"]):
                messages.error(request, "State name must contain only letters and spaces.")
                return redirect("add_address")

            if not re.match(location_pattern, form_data["country"]):
                messages.error(request, "Country name must contain only letters and spaces.")
                return redirect("add_address")

            if not re.match(house_name_pattern, form_data["house_name"]):
                messages.error(request, "House name must contain only letters, numbers, spaces, hyphens, or slashes.")
                return redirect("add_address")

            if not form_data["postal_code"].isdigit():
                messages.error(request, "Postal code must contain only digits.")
                return redirect("add_address")

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
            return redirect("address")
    
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

# _______________________________________________X_________________________X__________________________


# _____________________________________________________________________________________________________________________


