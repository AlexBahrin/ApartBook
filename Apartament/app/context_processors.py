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


def staff_unread_messages(request):
    """Add unread message count for staff members."""
    unread_count = 0
    
    if request.user.is_authenticated and request.user.is_staff:
        from app.models import Message
        # Count messages sent by non-staff users that are unread
        unread_count = Message.objects.filter(
            is_read=False,
            sender__is_staff=False  # Messages from guests to staff
        ).count()
    
    return {
        'staff_unread_messages_count': unread_count,
    }


def user_unread_messages(request):
    """Add unread message count for regular users."""
    unread_count = 0
    
    if request.user.is_authenticated and not request.user.is_staff:
        from app.models import Message
        # Count unread messages in user's conversations where sender is staff
        unread_count = Message.objects.filter(
            conversation__user=request.user,
            is_read=False,
            sender__is_staff=True  # Messages from staff to this user
        ).count()
    
    return {
        'user_unread_messages_count': unread_count,
    }
