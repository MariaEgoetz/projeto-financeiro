import json
from django import template

register = template.Library()


@register.filter(name='json_loads')
def json_loads(value):
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None
