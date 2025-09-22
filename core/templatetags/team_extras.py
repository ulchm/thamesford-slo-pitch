from django import template
import hashlib

register = template.Library()

@register.filter
def team_placeholder_color(team_name):
    """Generate a consistent color based on team name hash."""
    # Generate a hash of the team name
    hash_object = hashlib.md5(team_name.encode())
    hash_hex = hash_object.hexdigest()
    
    # Use first 6 characters for color, but ensure it's not too dark
    color = hash_hex[:6]
    
    # Convert to RGB and ensure minimum brightness
    r = int(color[0:2], 16)
    g = int(color[2:4], 16) 
    b = int(color[4:6], 16)
    
    # Ensure colors are bright enough (minimum 100)
    r = max(r, 100)
    g = max(g, 100)
    b = max(b, 100)
    
    return f"rgb({r}, {g}, {b})"

@register.inclusion_tag('core/team_logo.html')
def team_logo(team, size="40"):
    """Render team logo or placeholder."""
    return {
        'team': team,
        'size': size,
        'placeholder_color': team_placeholder_color(team.name)
    }