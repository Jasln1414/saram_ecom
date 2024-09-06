from django import template

register = template.Library()

# Define a mapping of color names to hex values
COLOR_HEX_MAP = {
    'red': '#FF0000',
    'green': '#00FF00',
    'blue': '#0000FF',
    'yellow': '#FFFF00',
    'cyan': '#00FFFF',
    'magenta': '#FF00FF',
    'black': '#000000',
    'white': '#FFFFFF',
    'gray': '#808080',
    'purple': '#800080',
    'orange': '#FFA500',
    'pink': '#FFC0CB',
    # Add more colors as needed
}

@register.filter(name='color_hex')
def color_hex(value):
    """
    Convert color name to its hex value.
    """
    # Convert the color name to lowercase to handle case insensitivity
    color_name = value.strip().lower()
    # Return the corresponding hex value or a default color if not found
    return COLOR_HEX_MAP.get(color_name, '#000000')  # Default to black if color not found
