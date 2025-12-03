from django.conf import settings


def currency_context(request):
    """Add currency information to template context."""
    currency_code = getattr(request, 'currency', settings.DEFAULT_CURRENCY)
    currency_data = getattr(request, 'currency_data', settings.CURRENCIES[settings.DEFAULT_CURRENCY])
    
    return {
        'current_currency': currency_code,
        'currency_symbol': currency_data['symbol'],
        'currency_rate': currency_data['rate'],
        'available_currencies': settings.CURRENCIES,
        'LANGUAGES': settings.LANGUAGES,
    }
