import razorpay
from django.conf import settings

def get_razorpay_client():
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    return client
