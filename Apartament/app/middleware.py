from django.conf import settings


class CurrencyMiddleware:
    """Middleware to handle currency selection from session/cookie."""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get currency from session or cookie, default to EUR
        currency = request.session.get('currency')
        if not currency:
            currency = request.COOKIES.get('currency', settings.DEFAULT_CURRENCY)
        
        # Validate currency
        if currency not in settings.CURRENCIES:
            currency = settings.DEFAULT_CURRENCY
        
        # Store on request for easy access
        request.currency = currency
        request.currency_data = settings.CURRENCIES[currency]
        
        response = self.get_response(request)
        
        return response
