from django import template
import re

register = template.Library()

@register.filter
def clean_text(value):
    """Clean up escaped characters and normalize whitespace."""
    if not value:
        return value
    
    # Replace escaped characters with actual characters
    cleaned = value.replace('\\r\\n', '\n')
    cleaned = cleaned.replace('\\r', '\n') 
    cleaned = cleaned.replace('\\n', '\n')
    cleaned = cleaned.replace('\\t', ' ')
    
    # Clean up multiple spaces and normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)  # Keep paragraph breaks
    
    return cleaned.strip()