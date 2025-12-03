from decimal import Decimal, ROUND_HALF_UP
from django import template
from django.conf import settings

register = template.Library()


@register.filter
def convert_currency(value, currency_code=None):
    """
    Convert a price from EUR to the specified currency.
    Usage: {{ price|convert_currency:"USD" }} or {{ price|convert_currency:current_currency }}
    """
    if value is None:
        return value
    
    try:
        value = Decimal(str(value))
    except (ValueError, TypeError):
        return value
    
    if currency_code is None or currency_code == 'EUR':
        return value
    
    currency_data = settings.CURRENCIES.get(currency_code)
    if not currency_data:
        return value
    
    rate = Decimal(str(currency_data['rate']))
    converted = value * rate
    return converted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


@register.filter
def format_price(value, currency_code=None):
    """
    Format a price with currency symbol.
    Usage: {{ price|format_price:"USD" }} or {{ price|format_price:current_currency }}
    """
    if value is None:
        return ''
    
    try:
        value = Decimal(str(value))
    except (ValueError, TypeError):
        return str(value)
    
    if currency_code is None:
        currency_code = 'EUR'
    
    currency_data = settings.CURRENCIES.get(currency_code, settings.CURRENCIES['EUR'])
    symbol = currency_data['symbol']
    
    # Convert from EUR if needed
    if currency_code != 'EUR':
        rate = Decimal(str(currency_data['rate']))
        value = value * rate
    
    value = value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Format based on currency
    if currency_code in ['EUR', 'GBP', 'CHF']:
        return f"{symbol}{value}"
    elif currency_code == 'RON':
        return f"{value} {symbol}"
    else:
        return f"{symbol}{value}"


@register.simple_tag(takes_context=True)
def price(context, value):
    """
    Display price in user's selected currency.
    Usage: {% price apartment.base_price_per_night %}
    """
    currency_code = context.get('current_currency', 'EUR')
    return format_price(value, currency_code)


@register.simple_tag
def currency_symbol(currency_code):
    """Get symbol for a currency code."""
    currency_data = settings.CURRENCIES.get(currency_code, {})
    return currency_data.get('symbol', currency_code)
