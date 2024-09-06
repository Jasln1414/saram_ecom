from PIL import Image
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, HttpResponse
from django.core.files.uploadedfile import UploadedFile
from django.contrib.auth.models import User
from django.views.decorators.cache import never_cache
from django.contrib import messages, auth
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import *
from django.urls import reverse
from cart_app.models import *
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum, F
from django.utils.crypto import get_random_string
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from io import BytesIO
import xlsxwriter
from django.utils import timezone
from .forms import CategoryOfferForm

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from cart_app.forms import CategoryOfferForm
from django.db.models import Count
from django.db.models.functions import TruncDate
from datetime import datetime


PRODUCT_PER_PAGE = 9






# Create your views here


@never_cache
def admin_login(request):
    try:
        if request.user.is_superuser:
            return redirect("dashboard")
        if request.method == "POST":
            username = request.POST.get("username")
            password = request.POST.get("password")
            sp_user = authenticate(request, username=username, password=password)
            if sp_user is not None and sp_user.is_superuser:
                login(request, sp_user)
                return redirect("dashboard")
            else:
                messages.error(request, "Sorry, only admins are allowed.")
        return render(request, "login.html")
    except Exception as e:
        messages.error(request, str(e))
        return redirect("admin_login")



@login_required
@never_cache
def dashboard(request):
    if request.user.is_superuser:
        month = request.GET.get("month")
        if month:
            year,month = map(int,month.split("-"))
            ordered_items = OrderItem.objects.filter(
            status = "Delivered", created_at__year=year, created_at__month=month)
        else:
           
            ordered_items = OrderItem.objects.filter(status="Delivered") 
            delivered_orders_per_day =(
                ordered_items.annotate(delivery_date=TruncDate("created_at"))
                .values("delivery_date")
                .annotate(total_orders=Count("id"))
                .order_by("delivery_date")

            )
            delivery_data = list(
               delivered_orders_per_day.values("delivery_date", "total_orders")


            )
            if request.headers.get("x-requested-with") == "XMLHttpRequest":

                    response_data = {
                    "labels": [
                        item["delivery_date"].strftime("%Y-%m-%d") for item in delivery_data
                ],
                    "data": [item["total_orders"] for item in delivery_data],
            } 
                    return JsonResponse(response_data)               
            best_seller = (
                    ProductColorImage.objects.filter(
                        is_deleted=False,
                        product_order__in=ordered_items,
                    )
                    .annotate(order_count=Count("product_order"))
                    .order_by("-order_count")
                )
            top_10_products = best_seller.distinct()[:10]
            start_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
            end_date = datetime.strptime("2024-12-31", "%Y-%m-%d")
            orders_per_year = OrderItem.objects.filter(
                    status="Delivered", created_at__range=(start_date, end_date)
                )
            orders_per_month = OrderItem.objects.filter(
                    status="Delivered", created_at__range=("2024-05-01", "2024-05-31")
                )
            total_sum_per_year = orders_per_year.aggregate(total_price=Sum("order__total"))[
                    "total_price"
                ]
            total_sum_per_month = orders_per_month.aggregate(
                    total_price=Sum("order__total")
                )["total_price"]
            top_3_category = (
                    Product.objects.filter(
                        color_image__in=top_10_products,
                        is_deleted=False,
                        color_image__product_order__in=ordered_items,
                    )
                    .values("category__name", "category__cat_image")
                    .annotate(category_count=Count("category"))
                    .order_by("-category_count")[:3]
                )

            category_count = [item["category_count"] for item in top_3_category]
            category_sum = sum(category_count)
            top_5_brand = (
                    best_seller.values("product__brand__name")
                    .annotate(brand_count=Count("product__brand__id"))
                    .order_by("-brand_count")
                    .distinct()[:5]
                )
            brand_count = top_5_brand.count()
            brand_sum = sum(brand_count for brand in top_5_brand)
            context = {
                    "delivered_orders_per_day": delivery_data,
                    "total_sum_per_month": total_sum_per_month,
                    "top_10_products": top_10_products,
                    "top_3_category": top_3_category,
                    "total_sum": total_sum_per_year,
                    "category_count": category_count,
                    "category_sum": category_sum,
                    "top_5_brand": top_5_brand,
                    "brand_count": brand_count,
                    "brand_sum": brand_sum,
                    }
            return render(request, "dashboard.html", context)
    else:
            messages.error(request, "Only admins are allowed.")
            return redirect("admin_login")





@never_cache
def admin_logout(request):
    try:
        logout(request)
        return redirect("admin_login")
    except Exception as e:
        messages.error(request, str(e))
        return redirect("admin_login")


@never_cache
def customer(request):
    try:
        if request.user.is_superuser:
            users = User.objects.all().order_by("-id")
            return render(request, "customer.html", {"users": users})
    except Exception as e:
        messages.error(request, str(e))
    return redirect("admin_login")


@never_cache
def block_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user.is_active = False
        user.save()
        messages.success(request, f"User {user.username} has been blocked.")

    except Exception as e:
        messages.error(request, str(e))
    return redirect("customer")


@never_cache
def unblock_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.save()
        messages.success(request, f"User {user.username} has been unblocked.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("customer")


@never_cache
def user_search(request):
    try:
        if request.method == "POST":
            get_search = request.POST.get("search")
            return_search = User.objects.filter(
                Q(username__icontains=get_search) | Q(email__icontains=get_search)
            )
            return render(request, "customer.html", {"users": return_search})
    except Exception as e:
        messages.error(request, str(e))
    return redirect("customer")


@never_cache
def category(request):
    try:
        if request.user.is_superuser:
            cat_gory = Category.objects.all().order_by("id")
            return render(request, "category/category.html", {"cat_gory": cat_gory})
    except Exception as e:
        messages.error(request, str(e))
    return redirect("admin_login")


@never_cache
def add_category(request):
    if request.user.is_superuser:
        if request.method == "POST":
            name = request.POST.get("name")
            description = request.POST.get("description")
            image = request.FILES.get("image")

            if not name.strip():
                messages.error(request, "Name cannot be empty.")
                return redirect("add_category")
            elif len(description) < 10:
                messages.error(
                    request, "Description must be at least 10 characters long."
                )
                return redirect("add_category")
            elif not all([name, description, image]):
                messages.error(request, "All fields are required.")
                return redirect("add_category")
            elif Category.objects.filter(name=name).exists():
                messages.error(request, "Category with this name already exists.")
                return redirect("add_category")
            else:
                create_category = Category.objects.create(
                    name=name, description=description, cat_image=image
                )
                create_category.save()
            messages.success(request, "Category added successfully.")
            return redirect("category")
    return render(request, "category/add_category.html")


@never_cache
def edit_category(request, cat_id):
    try:
        if request.user.is_superuser:
            category = Category.objects.get(id=cat_id)

            if request.method == "POST":
                name = request.POST.get("editname")
                description = request.POST.get("description")
                image = request.FILES.get("editimage")
                if not name.strip():
                    messages.error(request, "Name cannot be empty.")
                    return redirect("edit_category", cat_id=cat_id)
                if len(description) < 10:
                    messages.error(
                        request, "Description must be at least 10 characters long."
                    )
                    return redirect("edit_category", cat_id=cat_id)

                elif not all([name, description]):
                    messages.error(request, "Name and description are required.")
                    return redirect("edit_category", cat_id=cat_id)
                elif Category.objects.filter(name=name).exclude(id=cat_id).exists():
                    messages.error(request, "Category with this name already exists.")
                    return redirect("edit_category", cat_id=cat_id)
                elif not name.strip():
                    messages.error(request, "Name cannot be empty.")
                    return redirect("edit_category", cat_id=cat_id)

                if image:
                    category.cat_image = image
                    category.save()

                category.name = name
                category.description = description
                category.cat_image = image
                category.save()
                messages.success(request, "Category updated successfully.")
                return redirect("category")

        return render(request, "category/edit_category.html", {"category": category})
    except Exception as e:
        messages.error(request, str(e))
    return redirect("admin_login")



@never_cache
def islisted(request, cat_id):
    try:
        listed = Category.objects.get(id=cat_id)
        listed.is_listed = True
        listed.save()
        Product.objects.filter(category=listed).update(is_listed=True)

    except Exception as e:
        messages.error(request, str(e))
    return redirect("category")


@never_cache
def isunlisted(request, cat_id):
    try:
        listed = Category.objects.get(id=cat_id)
        listed.is_listed = False
        listed.save()
        Product.objects.filter(category=listed).update(is_listed=False)

    except Exception as e:
        messages.error(request, str(e))
    return redirect("category")


@never_cache
def is_deleted(request, cat_id):
    try:
        deleted = Category.objects.get(id=cat_id)
        deleted.is_deleted = True
        deleted.save()
    except Exception as e:
        messages.error(request, str(e))
    return redirect("recyclebin")


# _____________________________________________________________Product_____________________________________________________________________


@never_cache
def product(request):
    try:
        if request.user.is_superuser:
            #next_url = request.GET.get("next", "/")
            products = ProductColorImage.objects.filter(is_deleted=False).order_by("id")
            page = request.GET.get("page", 1)
            product_Paginator = Paginator(products, PRODUCT_PER_PAGE)

            try:
                products = product_Paginator.page(page)
            except PageNotAnInteger:
                products = product_Paginator.page(1)
            except EmptyPage:
                products = product_Paginator.page(product_Paginator.num_pages)

            context = {
                "products": products,
                "page_obj": products,
                "is_paginated": product_Paginator.num_pages > 1,
                "paginator": product_Paginator,
            }
            return render(request, "product/product.html", context)
        else:
            messages.error(request, "Only admins are allowed.")
            return redirect("admin_login")
    except Exception as e:
        messages.error(request, str(e))
        return redirect("admin_login")


def is_valid_image(file):
    # Check if the file is an image
    if not isinstance(file, UploadedFile):
        return False

    try:

        Image.open(file)
        return True
    except Exception as e:
        return False


@never_cache
def edit_product(request, product_id):
    print(request.POST)
    try:

        # Retrieve the ProductColorImage object based on the provided product_id
        color_image = ProductColorImage.objects.get(id=product_id)
        
        # Get all ProductSize objects related to the ProductColorImage
        sizes = ProductSize.objects.filter(productcolor_id=color_image.pk)
        
        # Retrieve all Brand objects for selection in the form
        brands = Brand.objects.all()
        
        # If the request method is POST, process the form submission
        if request.method == "POST":
            # Extract form data
            name = request.POST.get("name")
            category_id = request.POST.get("category")
            type = request.POST.get("type")
            price = request.POST.get("price")
            brand = request.POST.get("brand")
            percentage = request.POST.get("percentage")

            # Check if all required fields are filled
            if (
                not name.strip()
                or not type.strip()
                or not price.strip()
                or not brand.strip()
            ):
                messages.error(request, "All fields should contain valid data.")
                return redirect("product")  # Redirect back to product page if validation fails

            # Handle expiry date if provided
            exp_date = request.POST.get("exp_date")
            if exp_date:
                try:
                    exp_date = datetime.strptime(exp_date, "%Y-%m-%d").date()
                except ValueError:
                    messages.error(request, "Invalid date format for expiry date.")
                    return redirect("product")  # Redirect back if date format is invalid
            else:
                exp_date = None

            # Check if the expiry date is valid
            today = timezone.now().date()
            if exp_date and (exp_date < today or exp_date == today):
                messages.error(request, "Expiry date cannot be in the past or today.")
                return redirect(edit_product, product_id)  # Redirect back if date is invalid

            # Check if the price is valid
            description = request.POST.get("description")
            if float(price) < 0:
                messages.error(request, "The price cannot be a negative number.")
                return redirect("product")  # Redirect back if price is invalid

            # Validate uploaded images
            image1 = request.FILES.get("image1")
            image2 = request.FILES.get("image2")
            image3 = request.FILES.get("image3")
            image4 = request.FILES.get("image4")

            # Check if each image is valid
            if image1 and not is_valid_image(image1):
                messages.error(request, "This is not a valid image file.")
                return redirect("product")  # Redirect back if image is invalid
            elif image2 and not is_valid_image(image2):
                messages.error(request, "This is not a valid image file.")
                return redirect("product")
            elif image3 and not is_valid_image(image3):
                messages.error(request, "This is not a valid image file.")
                return redirect("product")
            elif image4 and not is_valid_image(image4):
                messages.error(request, "This is not a valid image file.")
                return redirect("product")

            # Retrieve the selected category and brand objects
            category = Category.objects.get(id=category_id)
            if brand:
                brand = Brand.objects.get(id=brand)

            # Update the ProductColorImage and associated Product with new data
            color_image.product.name = name
            color_image.product.per_expiry_date = exp_date
            color_image.product.description = description
            color_image.product.type = type
            color_image.product.price = price
            color_image.product.category = category
            color_image.product.percentage = percentage
            if brand:
                color_image.product.brand = brand
            color_image.product.save()

            # Update images for the ProductColorImage
            if color_image:
                if image1:
                    color_image.image1 = image1
                if image2:
                    color_image.image2 = image2
                if image3:
                    color_image.image3 = image3
                if image4:
                    color_image.image4 = image4
                color_image.save()

            # Update sizes and quantities
            for size in sizes:
                size_quantity = request.POST.get(size.size)
                if size_quantity is not None:
                    size.quantity = size_quantity
                    size.save()

            # Provide a success message and redirect to the product list
            messages.success(request, "Product updated successfully.")
            page = request.GET.get("page", 1)  # Get the page number from the GET parameters
            return HttpResponseRedirect(reverse("product") + "?page=" + str(page))
        
        else:
            # Prepare data for rendering the edit form
            available_sizes = [size.size for size in sizes]
            return render(
                request,
                "product/edit_product.html",
                {
                    "color_image": color_image,
                    "sizes": sizes,
                    "brands": brands,
                    "available_sizes": available_sizes,
                },
            )
    
    except Product.DoesNotExist:
        # Handle case where the ProductColorImage does not exist
        messages.error(request, "Product not found.")
        return redirect("product")



@never_cache
def product_search(request):
    try:
        if request.method == "POST":
            search = request.POST.get("search_product")
            products = ProductColorImage.objects.filter(product__name__icontains=search)
            return render(request, "product/product.html", {"products": products})
        print("successfully send")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("product")


@never_cache
def add_product(request):
    try:
        if request.user.is_superuser:
            categories = Category.objects.all()
            brands = Brand.objects.all()
            
            if request.method == "POST":
                name = request.POST.get("name")
                if not name.strip():
                    messages.error(request, "Name cannot be empty.")
                    return redirect("add_product")
                
                category = request.POST.get("category")
                type = request.POST.get("type")
                if not type.strip():
                    messages.error(request, "Type cannot be empty.")
                    return redirect("add_product")
                
                price = request.POST.get("price")  # Ensure this is defined
                
                exp_date = request.POST.get("exp_date")
                brand = request.POST.get("brand")
                description = request.POST.get("description")
                
                if len(description) < 10:
                    messages.error(request, "Description must be at least 10 characters long.")
                    return redirect("add_product")
                
                if not all([name, type, price, description]):
                    messages.error(request, "All fields are required.")
                    return redirect("add_product")
                
                if brand:
                    if not Brand.objects.filter(id=brand).exists():
                        messages.error(request, "Invalid brand.")
                        return redirect("add_product")
                    else:
                        brand = Brand.objects.filter(id=brand).first()
                
                if Product.objects.filter(name=name).exists():
                    messages.error(request, "Product with this name already exists.")
                    return redirect("add_product")
                
                try:
                    price = float(price)  # Convert price to float
                    if price <= 0:
                        raise ValueError
                except ValueError:
                    messages.error(request, "Please enter a valid positive price.")
                    return redirect("add_product")
                
                add_product = Product.objects.create(
                    name=name,
                    category_id=category,
                    type=type,
                    price=price,  # Ensure price is used here
                    description=description,
                )

                if exp_date:
                    add_product.per_expiry_date = exp_date
                
                if brand:
                    add_product.brand = brand
                
                add_product.save()

                messages.success(request, "Product added successfully.")
                return redirect("product_image")
            
            return render(
                request,
                "product/add_product.html",
                {"categories": categories, "brands": brands},
            )
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect("admin_login")



@never_cache
def product_image(request):
    try:
        if request.user.is_superuser:
            products = Product.objects.all().order_by("id")
            if request.method == "POST":
                product_id = request.POST.get("product")
                color = request.POST.get("color")
                image1 = request.FILES.get("image1")
                image2 = request.FILES.get("image2")
                image3 = request.FILES.get("image3")
                image4 = request.FILES.get("image4")

                if not all([product_id, color, image1, image2, image3, image4]):
                    messages.error(request, "All fields are required.")
                    return redirect("product_image")
                if not color.strip():
                    messages.error(request, "Color cannot be empty.")
                    return redirect("product_image")
                if not color.isalpha():
                    messages.error(request, "Color must contain only letters.")
                    return redirect("product_image")
                if not all(
                    [is_valid_image(img) for img in [image1, image2, image3, image4]]
                ):
                    messages.error(request, "All images must be valid image files.")
                    return redirect("product_image")

                product = get_object_or_404(Product, id=product_id)
                if not all([product_id, color]):
                    messages.error(request, "Product and color are required.")
                    return redirect("product_image")
                create_product = ProductColorImage.objects.create(
                    product=product,
                    color=color,
                    image1=image1,
                    image2=image2,
                    image3=image3,
                    image4=image4,
                )
                create_product.save()
                messages.success(request, "Product image added successfully.")
                return redirect("product_image")
            else:
                return render(
                    request, "product/product_image.html", {"products": products}
                )
        else:
            return redirect("product")
    except Exception as e:
        messages.error(request, str(e))
        return redirect("product")




def product_size(request):
    try:
        if request.user.is_superuser:
            product_colors = ProductColorImage.objects.all()
            
            if request.method == "POST":
                product_color_id = request.POST.get("product_color")
                size = request.POST.get("size")
                quantity = request.POST.get("quantity")

                print(f"Product Color ID: {product_color_id}, Size: {size}, Quantity: {quantity}")
                
                # Fetch the ProductColorImage object or return a 404 error if not found
                product_color = get_object_or_404(ProductColorImage, id=product_color_id)

                # Check if the size already exists for the selected product color
                if ProductSize.objects.filter(productcolor=product_color, size=size).exists():
                    messages.error(request, "This size already exists for the selected product color.")
                    return redirect("product_size")

                # Ensure all fields are provided
                if not all([product_color_id, size, quantity]):
                    messages.error(request, "All fields are required.")
                    return redirect("product_size")

                # Validate quantity
                try:
                    quantity = int(quantity)
                    if quantity < 1:
                        raise ValueError
                except ValueError:
                    messages.error(request, "Quantity must be a positive integer.")
                    return redirect("product_size")

                # Validate size
                if size not in ["S", "M", "L", "XL", "XXL"]:
                    messages.error(request, "Size must be S, M, L, XL, or XXL.")
                    return redirect("product_size")

                if not size.strip():
                    messages.error(request, "Size cannot be empty.")
                    return redirect("product_size")

                # Create a new ProductSize object
                new_product_size = ProductSize.objects.create(
                    productcolor=product_color,
                    size=size,
                    quantity=quantity,
                )
                print(f"New Product Size Created: {new_product_size}")

                messages.success(request, "Product size created successfully.")
                return redirect("product")
            
            else:
                # Render the product size form if the request is GET
                return render(request, "product/product_size.html", {"product_colors": product_colors})

        else:
            return redirect("product")

    except Exception as e:
        messages.error(request, str(e))
        return redirect("product")


@never_cache
def view_brand(request):
    if request.user.is_superuser:
        brands = Brand.objects.filter(is_deleted=False, is_listed=True)
        return render(request, "view_brand.html", {"brands": brands})
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")


def add_brand(request):
    if request.user.is_superuser:
        if request.method == "POST":
            name = request.POST.get("brand_name")
            description = request.POST.get("description")

            if not name:
                messages.error(request, "Brand name is required.")
                return redirect(add_brand)
            if not name.strip():
                messages.error(request, "Brand name cannot contain only spaces.")
                return redirect(add_brand)
            if len(description) < 10:
                messages.error(
                    request, "Description must be at least 10 characters long."
                )
                return redirect(add_brand)
            else:
                create_brand = Brand.objects.create(name=name, description=description)
                messages.success(request, "Brand added successfully.")
                return redirect(view_brand)

        return render(request, "add_brand.html")
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")


@never_cache
def edit_brand(request, brand_id):
    if request.user.is_superuser:
        brand = get_object_or_404(Brand, id=brand_id)

        if request.method == "POST":
            name = request.POST.get("name")
            description = request.POST.get("description")

            if name:
                if not name.strip():
                    messages.error(request, "Name cannot be empty.")
                    return redirect("edit_brand", brand_id=brand_id)
                brand.name = name
            if description:
                if len(description) < 10:
                    messages.error(
                        request, "Description must be at least 10 characters long."
                    )
                    return redirect("edit_brand", brand_id=brand_id)
                elif not description.strip():
                    messages.error(request, "Description cannot be empty.")
                    return redirect("edit_brand", brand_id=brand_id)
                brand.description = description
            brand.save()
            messages.success(request, "Brand updated successfully.")
            return redirect("view_brand")



        return render(request, "edit_brand.html", {"brand": brand})



@never_cache
def delete_brand(request, brand_id):
    if request.user.is_superuser:
        brand = get_object_or_404(Brand, id=brand_id)
        brand.is_deleted = True
        brand.save()
        messages.success(request, "Brand deleted successfully.")
        return redirect("view_brand")
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")


# ____________________________________________________________________________________________________________________________________________________

@never_cache
def product_is_deleted(request, product_id):
    try:
        products = ProductColorImage.objects.get(id=product_id)
        products.is_deleted = True
        products.save()
        page = request.GET.get("page", 1)
        return HttpResponseRedirect(reverse("product") + "?page=" + str(page))
    except Exception as e:
        messages.error(request, str(e))
        return redirect("product")




# ____________________________________________________________________________________________________________________________________________________
@never_cache
def product_is_listed(request, product_id):
    product_color = ProductColorImage.objects.get(id=product_id)
    product_color.is_listed = True
    product_color.save()
    page = request.GET.get("page", 1)
    return HttpResponseRedirect(reverse("product") + "?page=" + str(page))


@never_cache
def product_is_unlisted(request, product_id):
    product_color = ProductColorImage.objects.get(id=product_id)
    product_color.is_listed = False
    product_color.save()
    page = request.GET.get("page", 1)
    return HttpResponseRedirect(reverse("product") + "?page=" + str(page))


# ____________________________________________________________________________________________________________________________________________________





def order(request):
    # Retrieve query parameters from the GET request
    from_date = request.GET.get("from")
    to_date = request.GET.get("to")
    search = request.GET.get("search")
    sort_by = request.GET.get("sort_by")

    print(f"{from_date} and {to_date}")

    # Check if the user is a superuser
    if request.user.is_superuser:
        # Set default sorting order if sort_by is not provided
        if not sort_by:
            sort_by = "-created_at"
        
        # Process from_date if provided
        if from_date:
            # Convert from_date from string to a datetime object
            from_date = datetime.strptime(from_date, "%Y-%m-%d")
            # Make the datetime object timezone-aware, set to start of the day
            from_date = timezone.make_aware(
                from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            )
        
        # Process to_date if provided
        if to_date:
            # Convert to_date from string to a datetime object
            to_date = datetime.strptime(to_date, "%Y-%m-%d")
            # Make the datetime object timezone-aware, set to end of the day
            to_date = timezone.make_aware(
                to_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            )

        # Fetch all orders and apply sorting based on the sort_by parameter
        order_details = Order.objects.all().order_by(sort_by)

        # Filter orders based on date range if both from_date and to_date are provided
        if from_date and to_date:
            order_details = Order.objects.filter(
                created_at__range=[from_date, to_date]
            ).order_by(sort_by)
        # Filter orders based on from_date if only from_date is provided
        elif from_date:
            order_details = Order.objects.filter(created_at__gte=from_date).order_by(
                sort_by
            )
        # Filter orders based on to_date if only to_date is provided
        elif to_date:
            order_details = Order.objects.filter(created_at__lte=to_date).order_by(
                sort_by
            )
        # Filter orders based on search term if search is provided
        elif search:
            order_details = Order.objects.filter(
                Q(tracking_id__icontains=search) | Q(payment_method__icontains=search)
            ).order_by(sort_by)

        # Prepare context for rendering the order list page
        context = {
            "order_details": order_details,
        }
        # Render the order list page with the context
        return render(request, "order/order.html", context)
    else:
        # If the user is not a superuser, print a message and redirect to admin login
        print("Redirecting to admin login")
        return redirect("admin_login")
    
def admin_order(request, order_id):
    # Check if the user is a superuser
    if request.user.is_superuser:
        # Retrieve the Order object based on the provided order_id
        order = Order.objects.get(id=order_id)
        # Fetch all OrderItem objects related to the retrieved order
        item = OrderItem.objects.filter(order=order).order_by("id")
        # Print the order items for debugging purposes
        print(item)
        # Get the status choices for OrderItem as a dictionary
        status_choices = dict(OrderItem.STATUS_CHOICES)
        # Retrieve the ShippingAddress object related to the order
        order_address = Shipping_address.objects.get(order=order)

        # Prepare context for rendering the order detail page
        context = {
            "item": item,
            "order": order,
            "status_choices": status_choices,
            "address": order_address,
        }
        # Render the order detail page with the context
        return render(request, "order/order_detail.html", context)
    else:
        # If the user is not a superuser, redirect to admin login
        return redirect("admin_login")


def update_status(request):
    # Check if the user is a superuser and the request method is POST
    if request.user.is_superuser and request.method == "POST":
        # Retrieve order_item_id and new_status from POST data
        order_item_id = request.POST.get("order_item_id")
        new_status = request.POST.get("new_status")
        try:
            # Fetch the OrderItem object based on the provided order_item_id
            order_item = OrderItem.objects.get(id=order_item_id)
            # Save the previous status before updating
            previous_status = order_item.status
            # Update the status of the OrderItem
            order_item.status = new_status
            order_item.save()

            # If the new status is "Cancelled", update the product size quantity
            if new_status == "Cancelled":
                # Check if the status has actually changed
                if previous_status != new_status:
                    # Fetch the ProductSize object related to the order item
                    product_size = ProductSize.objects.get(
                        productcolor=order_item.product, size=order_item.size
                    )
                    # Increase the quantity by the order item quantity
                    product_size.quantity = F("quantity") + order_item.qty
                    product_size.save()

            # Return a JSON response indicating success
            return JsonResponse({"status": "success"})
        except ObjectDoesNotExist:
            # Return an error response if the order item is not found
            return JsonResponse({"status": "error", "message": "Order item not found."})
        except ProductSize.DoesNotExist:
            # Return an error response if the product size is not found
            return JsonResponse(
                {"status": "error", "message": "Product size not found."}
            )

    # Return an error response if the request is not authorized or invalid
    return JsonResponse(
        {"status": "error", "message": "Unauthorized or invalid request."}
    )

def category_offer(request):
    if request.user.is_superuser:
        category_off = CategoryOffer.objects.filter(
            category__is_listed=True, category__is_deleted=False
        )
        return render(
            request, "category/cat_offer.html", {"category_off": category_off}
        )




def add_category_offer(request):
    # Check if the user is a superuser (admin)
    if request.user.is_superuser:
        # Initialize the form for adding a category offer
        form = CategoryOfferForm()

        # Check if the request is a POST request (i.e., form submission)
        if request.method == "POST":
            # Populate the form with the submitted data
            form = CategoryOfferForm(request.POST)
            if form.is_valid():
                # Extract form data
                category = form.cleaned_data.get("category")
                name = form.cleaned_data.get("offer_name")
                
                # Check if the offer name is not just whitespace
                if not name.strip():
                    messages.error(request, "Offer name cannot be empty.")
                    return redirect("add_category_offer")
                
                # Extract other form data
                discount_percentage = form.cleaned_data.get("discount_percentage")
                is_active = form.cleaned_data.get("is_active")
                end_date = form.cleaned_data.get("end_date")
                
                # Print the data for debugging purposes
                print(category, name, discount_percentage, is_active, end_date)
                
                # Get the current date
                today = timezone.now().date()
                
                # Check if all fields are filled
                if not all([category, name, discount_percentage, is_active, end_date]):
                    messages.error(request, "All fields are required.")
                
                # Validate the discount percentage
                elif discount_percentage < 5 or discount_percentage > 90:
                    messages.error(
                        request, "Discount percentage must be between 5 and 90."
                    )
                
                # Check if the selected category exists
                elif not Category.objects.filter(name=category).exists():
                    messages.error(request, "Category does not exist.")
                
                # Ensure the end date is in the future
                elif str(end_date) < str(today):
                    messages.error(
                        request, "End date must be greater than today's date."
                    )
                
                # Ensure the end date is not today's date
                elif str(end_date) and str(end_date) == str(today):
                    messages.error(
                        request, "End date must be greater than today's date."
                    )
                
                # Check if a category offer already exists for the selected category
                elif CategoryOffer.objects.filter(category__name=category).exists():
                    messages.error(
                        request, "Category offer already exists for this category."
                    )
                
                # If all validations pass, create the new category offer
                else:
                    CategoryOffer.objects.create(
                        category=category,
                        offer_name=name,
                        discount_percentage=discount_percentage,
                        is_active=is_active,
                        end_date=end_date,
                    )
                    messages.success(request, "Category offer added successfully.")
                    return redirect("category_offer")

        # Render the form for adding a category offer
        return render(request, "category/add_cat_offer.html", {"form": form})

#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx CANCEL RETURN XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX




@transaction.atomic
def cancel_order(request, order_id):
    if request.user.is_superuser:
        try:
            # Fetch the OrderItem object
            cancel = OrderItem.objects.get(id=order_id)
            main_order_id = cancel.order.id

            # Debug statements
            print(f"Order Item Status: {cancel.status}")
            print(f"Order Payment Method: {cancel.order.payment_method}")

            # Check if the order is already shipped
            if cancel.status == "Shipped":
                messages.error(request, "Cannot cancel an order that has already been shipped.")
                return redirect("admin_order", main_order_id)

            # Handle non-COD paid orders
            if cancel.order.payment_method != "COD" and cancel.order.paid:
                total_discount = cancel.order.discounted_price
                total_quantity = OrderItem.objects.filter(order=cancel.order).aggregate(
                    total_quantity=Sum("qty")
                )["total_quantity"]
                discount_per_item = float(total_discount) / float(total_quantity)
                original_price = cancel.product.product.offer_price
                cancelled_amount = (float(original_price) - float(discount_per_item)) * int(cancel.qty)

                user = cancel.order.customer.user
                wallet, created = Wallet.objects.get_or_create(user=user)
                wallet.balance += float(cancelled_amount)
                wallet.save()

                tranc_id = "CANCEL_" + get_random_string(3, "ABCDEFGHIJKLMOZ0123456789")
                while Wallet_transaction.objects.filter(transaction_id=tranc_id).exists():
                    tranc_id += get_random_string(3, "ABCDEFGHIJKLMOZ0123456789")

                Wallet_transaction.objects.create(
                    wallet=wallet,
                    order_item=cancel,
                    money_deposit=abs(cancelled_amount),
                    transaction_id=tranc_id,
                )
                if not cancel.cancel:
                    cancel.request_cancel = True
                    cancel.status = "Cancelled"
                    cancel.save()
                    messages.success(request, f"Amount of ₹{cancelled_amount} added to {user.username}'s Wallet.")
                    product_size = ProductSize.objects.get(productcolor=cancel.product, size=cancel.size)
                    product_size.quantity += cancel.qty
                    product_size.save()

            # Handle COD orders
            elif cancel.order.payment_method == "COD":
                if cancel.status in ["Order Placed", "Processing"]:
                    if not cancel.cancel:
                        cancel.request_cancel = True
                        cancel.status = "Cancelled"
                        cancel.save()
                        product_size = ProductSize.objects.get(productcolor=cancel.product, size=cancel.size)
                        product_size.quantity += cancel.qty
                        product_size.save()
                        messages.success(request, "COD order has been successfully cancelled.")
                else:
                    messages.error(request, "Cannot cancel COD order after it has been shipped.")
                return redirect("admin_order", main_order_id)

            # Handle unpaid orders or invalid states
            else:
                messages.info(request, "Order item does not exist or has already been cancelled.")

            return redirect("admin_order", main_order_id)

        except OrderItem.DoesNotExist:
            messages.info(request, "Order item does not exist.")
            return redirect("order")

    else:
        return redirect("admin_login")

@transaction.atomic
def return_order(request, return_id):
    if request.user.is_superuser:
        try:
            print("Starting return_order function",return_id)
            return_order = OrderItem.objects.get(id=return_id)
            ord_id = return_order.order.id
            print("Return order details:", return_order)
            print("Status:", return_order.status)
            print("Request return:", return_order.request_return)

            # Ensure the item hasn't already been returned and is eligible for return
            if return_order.status == "Returned":
                messages.info(request, f"Item '{return_order.product.product.name}' has already been returned.")
                return redirect("admin_order", order_id=ord_id)

            if return_order.request_return and return_order.status == "Delivered":
                total_discount = return_order.order.discounted_price
                total_quantity = OrderItem.objects.filter(order=return_order.order).aggregate(
                    total_quantity=Sum("qty")
                )["total_quantity"]
                print("Total quantity:", total_quantity)
                
                # Calculate discount per item
                if total_quantity > 0:
                    discount_per_item = float(total_discount) / float(total_quantity)
                else:
                    discount_per_item = 0
                
                original_price = return_order.product.product.offer_price
                refund_amount = (float(original_price) - float(discount_per_item)) * int(return_order.qty)
                print("Refund amount:", refund_amount)

                user = return_order.order.customer.user
                wallet, created = Wallet.objects.get_or_create(user=user)
                wallet.balance += float(refund_amount)
                wallet.save()

                tranc_id = "REFUND_" + get_random_string(6, "ABCLMOZ456789")
                while Wallet_transaction.objects.filter(transaction_id=tranc_id).exists():
                    tranc_id = "REFUND_" + get_random_string(6, "ABCLMOZ456789")

                print("Transaction ID:", tranc_id)

                Wallet_transaction.objects.create(
                    wallet=wallet,
                    order_item=return_order,
                    money_deposit=abs(refund_amount),
                    transaction_id=tranc_id,
                )

                # Mark the item as returned and update the status
                return_order.return_product = True
                return_order.status = "Returned"
                return_order.request_return = False
                return_order.save()

                # Update product stock
                product_size = ProductSize.objects.get(
                    productcolor=return_order.product, size=return_order.size
                )
                product_size.quantity += return_order.qty
                product_size.save()

                messages.success(
                    request,
                    f"Amount of ₹{refund_amount} added to {return_order.order.customer.user.username}'s Wallet for '{return_order.product.product.name}'.",
                )
                print("Order returned successfully for item:", return_order.product.product.name)

            else:
                messages.info(request, "item returned and refunded")

            return redirect("admin_order", order_id=ord_id)
        
        except OrderItem.DoesNotExist:
            print("Order item does not exist.")
            messages.error(request, "Order item does not exist.")
            return redirect("admin_order")
    else:
        print("User is not superuser")
        return redirect("admin_login")





#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!COUPON!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!



def admin_coupon(request):
    if request.user.is_superuser:
        coupons = Coupon.objects.filter(is_active=True).order_by("id")
        context = {"coupons": coupons}
        return render(request, "coupon/admin_coupon.html", context)
    else:
        return redirect("admin_login")


@never_cache
def add_coupon(request):
    try:
        if request.user.is_superuser:
            today = timezone.now().date()
            if request.method == "POST":
                code = request.POST.get("coupon_code", "").strip()
                name = request.POST.get("name", "").strip()
                dis = request.POST.get("discount_percentage", "").strip()
                minimum_amount = request.POST.get("minimum_amount", "").strip()
                maximum_amount = request.POST.get("maximum_amount", "").strip()
                end_date = request.POST.get("end_date", "").strip()
                usage_limit = request.POST.get("usage_limit", "").strip()

                # Validate that all fields are provided
                if not all(
                    [
                        code,
                        name,
                        dis,
                        minimum_amount,
                        maximum_amount,
                        end_date,
                        usage_limit,
                    ]
                ):
                    messages.error(
                        request, "All fields are required for adding the coupon."
                    )
                    return redirect("add_coupon")

                # Validate the coupon code
                if not code:
                    messages.error(request, "Coupon code cannot be empty.")
                    return redirect("add_coupon")
                if Coupon.objects.filter(coupon_code=code).exists():
                    messages.error(
                        request, "This coupon already exists. Please add a new one."
                    )
                    return redirect("add_coupon")

                # Validate the coupon name
                if not name:
                    messages.error(request, "Coupon name cannot be empty.")
                    return redirect("add_coupon")

                # Validate the discount percentage
                try:
                    dis = float(dis)
                    if dis < 5 or dis > 100:
                        messages.error(
                            request,
                            "Please provide a valid discount between 5 and 100.",
                        )
                        return redirect("add_coupon")
                except ValueError:
                    messages.error(request, "Please enter a valid discount percentage.")
                    return redirect("add_coupon")

                # Validate the minimum and maximum amounts
                try:
                    minimum_amount = float(minimum_amount)
                    maximum_amount = float(maximum_amount)
                    if minimum_amount < 100 or maximum_amount < 100:
                        messages.error(
                            request, "Price must be a positive value and at least 100."
                        )
                        return redirect("add_coupon")
                    if minimum_amount > maximum_amount:
                        messages.error(
                            request,
                            "Minimum amount cannot be greater than maximum amount.",
                        )
                        return redirect("add_coupon")
                except ValueError:
                    messages.error(
                        request,
                        "Please enter valid amounts for minimum and maximum values.",
                    )
                    return redirect("add_coupon")

                # Validate the end date
                try:
                    end_date = timezone.datetime.strptime(end_date, "%Y-%m-%d").date()
                    if str(end_date) < str(today):
                        messages.error(request, "End date cannot be in the past.")
                        return redirect("add_coupon")
                    elif str(end_date) and str(end_date) == str(today):
                        messages.error(request, "End date cannot be today.")
                        return redirect("add_coupon")
                except ValueError:
                    messages.error(
                        request, "Please enter a valid date in YYYY-MM-DD format."
                    )
                    return redirect("add_coupon")

                # Validate the usage limit
                try:
                    usage_limit = int(usage_limit)
                    if usage_limit < 1:
                        messages.error(request, "Usage limit cannot be less than 1.")
                        return redirect("add_coupon")
                except ValueError:
                    messages.error(request, "Please enter a valid usage limit.")
                    return redirect("add_coupon")

                # Create the coupon
                coupon = Coupon.objects.create(
                    coupon_code=code,
                    coupon_name=name,
                    discount_percentage=dis,
                    minimum_amount=minimum_amount,
                    maximum_amount=maximum_amount,
                    expiry_date=end_date,
                    usage_limit=usage_limit,
                )
                messages.success(request, "Coupon added successfully.")
                return redirect("admin_coupon")

            return render(request, "coupon/add_coupon.html")
        else:
            messages.error(request, "You do not have permission to access this page.")
            return redirect("admin_login")
    except Exception as e:
        messages.error(request, str(e))
        return render(request, "coupon/add_coupon.html")


def edit_coupon(request, coupon_id):
    if request.user.is_superuser:
        today = timezone.now()
        coupon = get_object_or_404(Coupon, id=coupon_id)
        if request.method == "POST":
            code = request.POST.get("coupon_code")
            name = request.POST.get("name")
            dis = request.POST.get("discount_percentage")
            min_amount = request.POST.get("minimum_amount")
            max_amount = request.POST.get("maximum_amount")
            end_date = request.POST.get("end_date")
            usage_limit = request.POST.get("usage_limit")

            if name:
                if not name.strip():
                    messages.error(request, "Name cannot be empty.")
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.coupon_name = name
            if dis:
                if float(dis) < 5 or float(dis) > 100:
                    messages.error(
                        request,
                        "Please provide a valid discount percentage between 5 and 100.",
                    )
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.discount_percentage = dis

            if min_amount:
                if float(min_amount) < 100:
                    messages.error(request, "Minimum amount must be a valid value.")
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.minimum_amount = min_amount
            if max_amount:
                if float(max_amount) < 1000:
                    messages.error(
                        request, "Maximum amount must be a greater than 1000."
                    )
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.maximum_amount = max_amount

            if code:
                if not code.strip():
                    messages.error(request, "Coupon code cannot be empty.")
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.coupon_code = code
            if end_date:
                if str(end_date) < str(today):
                    messages.error(request, "End date cannot be in the past.")
                    return redirect("edit_coupon", coupon_id=coupon_id)
                elif str(end_date) and str(end_date) == str(today):
                    messages.error(request, "End date cannot be today.")
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.expiry_date = end_date
            if usage_limit:
                if int(usage_limit) < 1:
                    messages.error(request, "Usage limit cannot be less than 1.")
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.usage_limit = usage_limit

            coupon.save()
            messages.success(request, "Coupon edited successfully.")
            return redirect("admin_coupon")

        return render(request, "coupon/edit_coupon.html", {"coupon": coupon})
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")


def del_coupon(request, coupon_id):
    if request.user.is_superuser:
        coupon = Coupon.objects.get(id=coupon_id)
        coupon.delete()
        messages.success(request, "The coupon has been deleted Successfully.")
        return redirect("admin_coupon")
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! SALES REPORT !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!





from django.utils.timezone import make_aware


import pytz # type: ignore

# Define the Florida timezone
FLORIDA_TZ = pytz.timezone('America/New_York')

def sales_report(request):
    # Check if the user is a superuser
    if request.user.is_superuser:
        if request.method == "GET":
            # Retrieve query parameters
            from_date_str = request.GET.get("from")
            to_date_str = request.GET.get("to")
            month = request.GET.get("month")
            year = request.GET.get("year")

            # Convert query parameters to timezone-aware datetimes
            from_date = to_date = None
            if from_date_str:
                try:
                    from_date = make_aware(datetime.strptime(from_date_str, "%Y-%m-%d"), timezone=FLORIDA_TZ)
                except ValueError:
                    messages.error(request, "Invalid 'from' date format. Use YYYY-MM-DD.")
                    return redirect("sales_report")
            if to_date_str:
                try:
                    to_date = make_aware(datetime.strptime(to_date_str, "%Y-%m-%d"), timezone=FLORIDA_TZ)
                except ValueError:
                    messages.error(request, "Invalid 'to' date format. Use YYYY-MM-DD.")
                    return redirect("sales_report")

            # Start with a base queryset
            order = OrderItem.objects.filter(
                cancel=False,
                return_product=False,
                status="Delivered",
            ).order_by("-created_at")  # Order from newest to oldest

            # Prepare filters dictionary
            filters = {}
            if from_date:
                filters["from_date"] = from_date_str
                order = order.filter(created_at__gte=from_date)
            if to_date:
                filters["to_date"] = to_date_str
                order = order.filter(created_at__lte=to_date)
            if month:
                filters["month"] = month
                year, month = map(int, month.split("-"))
                order = order.filter(created_at__year=year, created_at__month=month)
            if year:
                filters["year"] = year
                order = order.filter(created_at__year=year)

            # Store filters in session for later use
            request.session["filters"] = filters

            # Calculate totals and aggregate data
            count = order.count()
            total = order.aggregate(total=Sum("order__total"))["total"]
            total_discount = order.aggregate(
                total_discount=Sum("order__discounted_price")
            )["total_discount"]

            # Prepare context for rendering
            context = {
                "order": order,
                "count": count,
                "total": total,
                "total_discount": total_discount,
            }
            # Store overall sales data in session
            request.session["overall_sales_count"] = count
            request.session["overall_order_amount"] = total
            request.session["overall_discount"] = total_discount

            # Render the sales report template
            return render(request, "sales_report.html", context)
        else:
            messages.error(request, "You do not have permission to access this page.")
            return redirect("admin_login")
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")


def download_sales_report(request):
    if request.user.is_superuser:
        if request.method == "GET":
            filters = request.session.get("filters", {})
            sales_data = OrderItem.objects.filter(
                Q(cancel=False) & Q(return_product=False) & Q(status="Delivered")
            ).order_by("-created_at")  # Ensure the data is sorted from newest to oldest

            if "from_date" in filters:
                sales_data = sales_data.filter(created_at__gte=filters["from_date"])
            if "to_date" in filters:
                sales_data = sales_data.filter(created_at__lte=filters["to_date"])
            if "month" in filters:
                year, month = map(int, filters["month"].split("-"))
                sales_data = sales_data.filter(
                    created_at__year=year, created_at__month=month
                )
            if "year" in filters:
                sales_data = sales_data.filter(created_at__year=filters["year"])

            overall_sales_count = request.session.get("overall_sales_count")
            overall_order_amount = request.session.get("overall_order_amount")
            overall_discount = request.session.get("overall_discount")

            # Get the current time with timezone
            current_time = timezone.now().astimezone(FLORIDA_TZ)
            today_date = current_time.strftime("%Y-%m-%d")

            if "format" in request.GET and request.GET["format"] == "pdf":
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter)

                styles = getSampleStyleSheet()
                centered_style = ParagraphStyle(
                    name="Centered", parent=styles["Heading1"], alignment=1
                )

                content = []

                company_details = f"<b>Sara</b><br/>Email: sarahm@gmail.com<br/>Date: {today_date}"
                content.append(Paragraph(company_details, styles["Normal"]))
                content.append(Spacer(1, 0.5 * inch))

                content.append(Paragraph("<b>SALES REPORT</b><hr>", centered_style))
                content.append(Spacer(1, 0.5 * inch))

                data = [["Order ID", "Product", "Quantity", "Total Price", "Date"]]
                for sale in sales_data:
                    formatted_date = sale.order.created_at.astimezone(FLORIDA_TZ).strftime("%a, %d %b %Y")
                    data.append(
                        [
                            sale.order.tracking_id,
                            sale.product.product.name,
                            sale.qty,
                            sale.product.product.offer_price,
                            formatted_date,
                        ]
                    )

                table = Table(data, repeatRows=1)
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("TOPPADDING", (0, 0), (-1, 0), 12),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ]
                    )
                )

                content.append(table)
                content.append(Spacer(1, 0.5 * inch))

                overall_sales_count_text = (
                    f"<b>Overall Sales Count:</b> {overall_sales_count}"
                )
                overall_order_amount_text = (
                    f"<b>Overall Order Amount:</b> {overall_order_amount}"
                )
                overall_discount_amount_text = (
                    f"<b>Overall Discount:</b> {overall_discount}"
                )

                content.append(Paragraph(overall_sales_count_text, styles["Normal"]))
                content.append(Paragraph(overall_order_amount_text, styles["Normal"]))
                content.append(
                    Paragraph(overall_discount_amount_text, styles["Normal"])
                )

                doc.build(content)

                current_time = timezone.now().strftime("%Y-%m-%d %H-%M-%S")
                file_name = f"Sales_Report_{current_time}.pdf"

                response = HttpResponse(
                    buffer.getvalue(), content_type="application/pdf"
                )
                response["Content-Disposition"] = f'attachment; filename="{file_name}"'

                return response

            elif "format" in request.GET and request.GET["format"] == "excel":
                output = BytesIO()
                workbook = xlsxwriter.Workbook(output, {"in_memory": True})
                worksheet = workbook.add_worksheet("Sales Report")

                headings = ["Product", "Quantity", "Total Price", "Date"]
                header_format = workbook.add_format({"bold": True})
                for col, heading in enumerate(headings):
                    worksheet.write(0, col, heading, header_format)

                for row, sale in enumerate(sales_data, start=1):
                    formatted_date = sale.order.created_at.astimezone(FLORIDA_TZ).strftime("%a, %d %b %Y")
                    worksheet.write(row, 0, sale.product.product.name)
                    worksheet.write(row, 1, sale.qty)
                    worksheet.write(row, 2, sale.product.product.offer_price)
                    worksheet.write(row, 3, formatted_date)

                overall_data = [
                    ["Overall Sales Count", overall_sales_count],
                    ["Overall Order Amount", overall_order_amount],
                    ["Overall Discount", overall_discount],
                ]

                row = len(sales_data) + 2
                for label, value in overall_data:
                    worksheet.write(row, 0, label, header_format)
                    worksheet.write(row, 1, value)
                    row += 1

                workbook.close()
                output.seek(0)
                response = HttpResponse(output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                response["Content-Disposition"] = "attachment; filename=Sales_Report.xlsx"
                return response

            else:
                messages.error(request, "Invalid report format.")
                return redirect("sales_report")
        else:
            messages.error(request, "You do not have permission to access this page.")
            return redirect("admin_login")
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")




#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! PRODUCT RESTORE SECTION !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

#recycle_bin focuses on displaying and managing the list of deleted items.
#restore focuses on performing the action of restoring an individual item from the list.
@never_cache
def recycle_bin(request):
    try:
        if request.user.is_superuser:
            category = Category.objects.all().order_by("id")

            return render(request, "restore.html", {"category": category})
    except Exception as e:
        messages.error(request, str(e))
    return redirect("admin_login")


@never_cache
def restore(request, cat_id):
    try:
        restore = Category.objects.get(id=cat_id)
        restore.is_deleted = False
        restore.save()
    except Exception as e:
        messages.error(request, str(e))
    return redirect("category")


@never_cache
def product_restore(request, product_id):
    try:
        restore_product = ProductColorImage.objects.get(id=product_id)
        restore_product.is_deleted = False
        restore_product.save()
        return redirect("product")

    except Exception as e:
        messages.error(request, str(e))
        return redirect("product")

@never_cache
def product_recycle_bin(request):
    try:
        if request.user.is_superuser:
            products = ProductColorImage.objects.filter(is_deleted=True).order_by("id")

            return render(request, "product_restore.html", {"products": products})
    except Exception as e:
        messages.error(request, str(e))
    return redirect("admin_login")





























"""def sales_report(request):
    # Check if the current user is a superuser
    if request.user.is_superuser:
        # Check if the request method is GET
        if request.method == "GET":
            # Retrieve filter values from the GET parameters
            from_date = request.GET.get("from")
            to_date = request.GET.get("to")
            month = request.GET.get("month")
            year = request.GET.get("year")

            # Initialize the base QuerySet to filter OrderItems that are not canceled,
            # not returned, and have a status of 'Delivered', ordered by creation date
            order = OrderItem.objects.filter(
                cancel=False,
                return_product=False,
                status="Delivered",
            ).order_by("created_at")

            # Initialize an empty dictionary to store filters
            filters = {}

            # Apply the 'from_date' filter if provided
            if from_date:
                filters["from_date"] = from_date
                order = order.filter(created_at__gte=from_date)

            # Apply the 'to_date' filter if provided
            if to_date:
                filters["to_date"] = to_date
                order = order.filter(created_at__lte=to_date)

            # Apply the 'month' filter if provided
            if month:
                filters["month"] = month
                year, month = map(int, month.split("-"))
                order = order.filter(created_at__year=year, created_at__month=month)

            # Apply the 'year' filter if provided
            if year:
                filters["year"] = year
                order = order.filter(created_at__year=year)

            # Store the applied filters in the session
            request.session["filters"] = filters

            # Count the number of filtered order items
            count = order.count()

            # Aggregate the total order amount from the filtered results
            total = order.aggregate(total=Sum("order__total"))["total"]

            # Aggregate the total discount from the filtered results
            total_discount = order.aggregate(
                total_discount=Sum("order__discounted_price")
            )["total_discount"]

            # Prepare the context data for rendering the template
            context = {
                "order": order,
                "count": count,
                "total": total,
                "total_discount": total_discount,
            }

            # Store overall sales data in the session for later use
            request.session["overall_sales_count"] = count
            request.session["overall_order_amount"] = total
            request.session["overall_discount"] = total_discount

            # Render the sales report template with the context data
            return render(request, "sales_report.html", context)
        else:
            # If the request method is not GET, display an error message
            messages.error(request, "You do not have permission to access this page.")
            return redirect("admin_login")
    else:
        # If the user is not a superuser, display an error message
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")
def download_sales_report(request):
    # Check if the current user is a superuser
    if request.user.is_superuser:
        # Check if the request method is GET
        if request.method == "GET":
            # Retrieve filters from the session
            filters = request.session.get("filters", {})

            # Initialize the base QuerySet to filter OrderItems that are not canceled,
            # not returned, and have a status of 'Delivered'
            sales_data = OrderItem.objects.filter(
                Q(cancel=False) & Q(return_product=False) & Q(status="Delivered")
            )

            # Apply the 'from_date' filter from the session if it exists
            if "from_date" in filters:
                sales_data = sales_data.filter(created_at__gte=filters["from_date"])

            # Apply the 'to_date' filter from the session if it exists
            if "to_date" in filters:
                sales_data = sales_data.filter(created_at__lte=filters["to_date"])

            # Apply the 'month' filter from the session if it exists
            if "month" in filters:
                year, month = map(int, filters["month"].split("-"))
                sales_data = sales_data.filter(
                    created_at__year=year, created_at__month=month
                )

            # Apply the 'year' filter from the session if it exists
            if "year" in filters:
                sales_data = sales_data.filter(created_at__year=filters["year"])

            # Apply the 'from' and 'to_date' range filter if both exist in the session
            if "from" in filters and "to_date" in filters:
                sales_data = sales_data.filter(
                    created_at__range=[filters["from"], filters["to"]]
                )

            # Retrieve overall sales data from the session
            overall_sales_count = request.session.get("overall_sales_count")
            overall_order_amount = request.session.get("overall_order_amount")
            overall_discount = request.session.get("overall_discount")

            # Check if the requested format is PDF
            if "format" in request.GET and request.GET["format"] == "pdf":
                buffer = BytesIO()

                # Create a PDF document template
                doc = SimpleDocTemplate(buffer, pagesize=letter)

                # Define styles for the PDF content
                styles = getSampleStyleSheet()
                centered_style = ParagraphStyle(
                    name="Centered", parent=styles["Heading1"], alignment=1
                )

                # Get the current date
                today_date = datetime.now().strftime("%Y-%m-%d")

                # Initialize the PDF content list
                content = []

                # Add company details to the PDF
                company_details = f"<b>Sara</b><br/>Email: sarahm@gmail.com<br/>Date: {today_date}"
                content.append(Paragraph(company_details, styles["Normal"]))
                content.append(Spacer(1, 0.5 * inch))

                # Add the sales report title
                content.append(Paragraph("<b>SALES REPORT</b><hr>", centered_style))
                content.append(Spacer(1, 0.5 * inch))

                # Create the table data for the sales report
                data = [["Order ID", "Product", "Quantity", "Total Price", "Date"]]
                for sale in sales_data:
                    formatted_date = sale.order.created_at.strftime("%a, %d %b %Y")
                    data.append(
                        [
                            sale.order.tracking_id,
                            sale.product.product.name,
                            sale.qty,
                            sale.product.product.offer_price,
                            formatted_date,
                        ]
                    )

                # Create a table from the data
                table = Table(data, repeatRows=1)
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("TOPPADDING", (0, 0), (-1, 0), 12),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ]
                    )
                )

                # Add the table to the content
                content.append(table)

                # Add some spacing after the table
                content.append(Spacer(1, 0.5 * inch))

                # Add overall sales data to the PDF
                overall_sales_count_text = (
                    f"<b>Overall Sales Count:</b> {overall_sales_count}"
                )
                overall_order_amount_text = (
                    f"<b>Overall Order Amount:</b> {overall_order_amount}"
                )
                overall_discount_amount_text = (
                    f"<b>Overall Discount:</b> {overall_discount}"
                )

                content.append(Paragraph(overall_sales_count_text, styles["Normal"]))
                content.append(Paragraph(overall_order_amount_text, styles["Normal"]))
                content.append(
                    Paragraph(overall_discount_amount_text, styles["Normal"])
                )

                # Build the PDF document with the content
                doc.build(content)

                # Generate the PDF filename with a timestamp
                current_time = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
                file_name = f"Sales_Report_{current_time}.pdf"

                # Prepare the HTTP response with the PDF content
                response = HttpResponse(
                    buffer.getvalue(), content_type="application/pdf"
                )
                response["Content-Disposition"] = f'attachment; filename="{file_name}"'

                return response

            # Check if the requested format is Excel
            elif "format" in request.GET and request.GET["format"] == "excel":
                output = BytesIO()
                
                # Create an in-memory Excel workbook
                workbook = xlsxwriter.Workbook(output, {"in_memory": True})
                worksheet = workbook.add_worksheet("Sales Report")

                # Define column headings
                headings = ["Product", "Quantity", "Total Price", "Date"]
                header_format = workbook.add_format({"bold": True})
                for col, heading in enumerate(headings):
                    worksheet.write(0, col, heading, header_format)

                # Populate the worksheet with sales data
                for row, sale in enumerate(sales_data, start=1):
                    formatted_date = sale.order.created_at.strftime("%a, %d %b %Y")
                    worksheet.write(row, 0, sale.product.product.name)
                    worksheet.write(row, 1, sale.qty)
                    worksheet.write(row, 2, sale.product.product.offer_price)
                    worksheet.write(row, 3, formatted_date)

                # Close the workbook
                workbook.close()

                # Generate the Excel filename with a timestamp
                current_time = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
                file_name = f"Sales_Report_{current_time}.xlsx"

                # Prepare the HTTP response with the Excel content
                response = HttpResponse(
                    output.getvalue(),
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                response["Content-Disposition"] = f'attachment; filename="{file_name}"'

                return response
            else:
                # If the format is not recognized, redirect to the sales report page
                return redirect("sales_report")
        else:
            # If the request method is not GET, display an error message
            messages.error(request, "You do not have permission to access this page.")
            return redirect("admin_login")
    else:
        # If the user is not a superuser, display an error message
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")"""
