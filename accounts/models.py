from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string
from geopy.geocoders import Nominatim  # type: ignore
# Create your models here.
geocoder = Nominatim(user_agent="Sarahm")


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=200, default=None)
    last_name = models.CharField(max_length=200, default=None)
    email = models.EmailField(default="user@gmail.com")
    house_name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    street_name = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=12)
    is_deleted = models.BooleanField(default=False, blank=True, null=True)
    #latitude = models.FloatField(null=True, blank=True)
    #longitude = models.FloatField(null=True, blank=True)

   

    def __str__(self):
        return f" {self.city}, {self.state}, {self.country}"
    def __str__(self):
        return f"{self.user.username}:{self.house_name}"


class DeliveryCharge(models.Model):
    city = models.CharField(max_length=100, unique=True)
    charge = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.city}: {self.charge}"


class Customer(models.Model):
    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    dob = models.DateField(null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    phone_number = models.CharField(max_length=15)
    referral_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    referral_count = models.IntegerField(default=0)
    referred_person = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.user.username


class User_profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.user.id} - {self.user.username}"


@receiver(post_save, sender=User)
def Create_User_Customer(sender, instance, created, **kwargs):
    if created:
        Customer.objects.create(user=instance)
        print("customer created successfully!!")


@receiver(post_save, sender=Customer)
def generate_referral_code(sender, instance, created, **kwargs):
    if created:
        if not instance.referral_code:
            referral_code = "REF"
            referral_code += get_random_string(5, "IJKLMOZ0123456789")
            while Customer.objects.filter(referral_code=referral_code).exists():
                referral_code += get_random_string(5, "IJKLMOZ0123456789")
            instance.referral_code = referral_code
            instance.save()
