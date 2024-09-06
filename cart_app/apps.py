from django.apps import AppConfig
from geopy.geocoders import Nominatim  # type: ignore
from geopy import distance   # type: ignore



class CartAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cart_app'

geocoder = Nominatim(user_agent="Sarahm")

location1 = "Florida"
location2 = "Texas"
coordinates1 = geocoder.geocode(location1)
coordinates2 = geocoder.geocode(location2)
print(coordinates1)
print(coordinates2)
lat1,long1 = (coordinates1.latitude),(coordinates1.longitude)
lat2,long2 = (coordinates2.latitude),(coordinates2.longitude)


place1 = (lat1,long1)
place2 = (lat2,long2)
print(distance.distance(place1,place2))


