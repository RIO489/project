from django import template
import json

register = template.Library()

@register.filter
def pprint(value):
    if isinstance(value, dict):
        return json.dumps(value, indent=2)
    return value