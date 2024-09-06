# forms.py
from django import forms
from admin_app.models import Brand,Category,ProductColorImage

class ProductSearchForm(forms.Form):
    query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search products...', 'class': 'form-control'})
    )
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.filter(is_listed=True),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    brands = forms.ModelMultipleChoiceField(
        queryset=Brand.objects.filter(is_listed=True),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    colors = forms.ModelMultipleChoiceField(
        queryset=ProductColorImage.objects.filter(is_deleted=False, is_listed=True).distinct('color'),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
