"""
Email notification utilities for the booking system.
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.models import User


def get_admin_emails():
    """Get email addresses of all staff users."""
    return list(User.objects.filter(is_staff=True).values_list('email', flat=True))


def send_new_booking_notification(booking):
    """
    Send email to admin when a new booking request is submitted.
    """
    admin_emails = get_admin_emails()
    if not admin_emails:
        return
    
    subject = f"New Booking Request: {booking.apartment.title}"
    
    context = {
        'booking': booking,
        'apartment': booking.apartment,
        'user': booking.user,
    }
    
    html_message = render_to_string('emails/new_booking_admin.html', context)
    plain_message = render_to_string('emails/new_booking_admin.txt', context)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=admin_emails,
        html_message=html_message,
        fail_silently=True,
    )


def send_booking_confirmed_notification(booking):
    """
    Send email to user when their booking is confirmed.
    """
    if not booking.user.email:
        return
    
    subject = f"Booking Confirmed: {booking.apartment.title}"
    
    context = {
        'booking': booking,
        'apartment': booking.apartment,
        'user': booking.user,
    }
    
    html_message = render_to_string('emails/booking_confirmed.html', context)
    plain_message = render_to_string('emails/booking_confirmed.txt', context)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[booking.user.email],
        html_message=html_message,
        fail_silently=True,
    )


def send_booking_cancelled_notification(booking, cancelled_by='admin'):
    """
    Send email to user when their booking is cancelled.
    """
    if not booking.user.email:
        return
    
    subject = f"Booking Cancelled: {booking.apartment.title}"
    
    context = {
        'booking': booking,
        'apartment': booking.apartment,
        'user': booking.user,
        'cancelled_by': cancelled_by,
    }
    
    html_message = render_to_string('emails/booking_cancelled.html', context)
    plain_message = render_to_string('emails/booking_cancelled.txt', context)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[booking.user.email],
        html_message=html_message,
        fail_silently=True,
    )
