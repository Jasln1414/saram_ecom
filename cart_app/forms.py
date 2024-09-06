from django import forms
from admin_app.models import CategoryOffer
from django import forms
from .models import Order
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from django import forms
from .models import Order
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field, Fieldset


class CategoryOfferForm(forms.ModelForm):
    class Meta:
        model = CategoryOffer
        fields = "__all__"
        widgets = {
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

# forms.py
from django import forms

class ReturnOrderForm(forms.Form):
    reason = forms.CharField(
        label="Reason for Return",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        required=True,
    )
