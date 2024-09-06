
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import *
from .models import *


@receiver(post_save, sender=CategoryOffer)
def update_category_offer(sender, instance, created, **kwargs):
    today = timezone.now()
    if str(instance.end_date) and str(instance.end_date) < str(today):
        category_offer = CategoryOffer.objects.get(id=instance.id)
        category_offer.is_active = False
        category_offer.save()