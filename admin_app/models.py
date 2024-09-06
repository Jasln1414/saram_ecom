from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import *


# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cat_image = models.ImageField(upload_to="images/category", blank=True)
    is_listed = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    is_listed = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class CategoryOffer(models.Model):
    category = models.OneToOneField(Category, on_delete=models.CASCADE)
    offer_name = models.CharField(max_length=100, null=True, blank=True)
    discount_percentage = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()

    def __str__(self):
        return f"{self.category.name} - {self.discount_percentage}% DISCOUNT FROM {self.start_date} :- {self.end_date}"


class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    percentage = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)], default=0
    )
    category = models.ForeignKey(
        Category, related_name="category", on_delete=models.CASCADE, null=False
    )
    brand = models.ForeignKey(
        Brand, related_name="brand", on_delete=models.CASCADE, null=True, blank=True
    )
    type = models.CharField(max_length=100, default="Clothing")
    created_at = models.DateTimeField(auto_now_add=True)
    per_expiry_date = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_listed = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

   
    @property
    def offer_price(self):
        category_offer = CategoryOffer.objects.filter(
            category=self.category,
            is_active=True,
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date()
        ).first()

        if category_offer and category_offer.discount_percentage > self.percentage:
            offer_percentage = category_offer.discount_percentage
        else:
            offer_percentage = self.percentage

        offer_price = self.price - (offer_percentage * self.price / 100)
        return round(offer_price, 2)


class ProductColorImage(models.Model):
    product = models.ForeignKey(
        Product, related_name="color_image", on_delete=models.CASCADE
    )
    color = models.CharField(max_length=50)
    image1 = models.ImageField(upload_to="images/product")
    image2 = models.ImageField(upload_to="images/product")
    image3 = models.ImageField(upload_to="images/product")
    image4 = models.ImageField(upload_to="images/product")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_listed = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.product.name} {self.color}"


class ProductSize(models.Model):
    productcolor = models.ForeignKey(
        ProductColorImage, related_name="size", on_delete=models.CASCADE
    )
    size = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_listed = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        product_name = self.productcolor.product.name
        return f"{product_name} {self.productcolor.color} - {self.size}"


@receiver(post_save, sender=ProductSize)
def product_stock_management(sender, instance, **kwargs):
    product_color_image = instance.productcolor
    if all(size.quantity == 0 for size in product_color_image.size.all()):
        product_color_image.is_listed = False
        product_color_image.save(update_fields=["is_listed"])




   

class Coupon(models.Model):
    coupon_code = models.CharField(max_length=100, unique=True)
    coupon_name = models.CharField(max_length=50)
    discount_percentage = models.IntegerField(default=0)
    minimum_amount = models.PositiveBigIntegerField(blank=True, default=0)
    maximum_amount = models.PositiveBigIntegerField(blank=True, default=0)
    is_active = models.BooleanField(default=True)
    added_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.coupon_code} till {self.expiry_date} for {self.usage_limit} Customers."


