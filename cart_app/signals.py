# signals.py
from django.db.models.signals import pre_save
from django.dispatch import receiver
from geopy.geocoders import Nominatim  # type: ignore
from geopy.exc import GeocoderTimedOut, GeocoderServiceError # type: ignore
from .models import Address

@receiver(pre_save, sender=Address)
def geocode_address(sender, instance, **kwargs):
    if instance.city and instance.state and instance.country and not (instance.latitude and instance.longitude):
        geolocator = Nominatim(user_agent="geoapiExercises")
        try:
            address_string = f"{instance.house_name}, {instance.city}, {instance.state}, {instance.country}"
            location = geolocator.geocode(address_string)
            if location:
                instance.latitude = location.latitude
                instance.longitude = location.longitude
            else:
                print("Location not found.")
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"Error geocoding address: {e}")
