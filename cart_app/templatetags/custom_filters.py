# cart_app/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplies the given value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''
