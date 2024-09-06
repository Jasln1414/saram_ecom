from django import forms
from admin_app.models import CategoryOffer


class CategoryOfferForm(forms.ModelForm):
    class Meta:
        model = CategoryOffer
        fields = "__all__"
        widgets = {
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }