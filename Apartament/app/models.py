from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class Apartment(models.Model):
    """Represents an apartment listing."""
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    capacity = models.PositiveIntegerField(help_text="Maximum number of guests")
    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.PositiveIntegerField(default=1)
    amenities = models.JSONField(default=list, blank=True, help_text="List of amenities")
    base_price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            # Ensure unique slug
            original_slug = self.slug
            counter = 1
            while Apartment.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def get_main_image(self):
        """Returns the main image or first image if no main is set."""
        main_image = self.images.filter(is_main=True).first()
        if main_image:
            return main_image
        return self.images.first()


class ApartmentImage(models.Model):
    """Images for an apartment listing."""
    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='apartments/')
    is_main = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', '-is_main']

    def __str__(self):
        return f"Image for {self.apartment.title}"

    def save(self, *args, **kwargs):
        # If this is set as main, unset other main images
        if self.is_main:
            ApartmentImage.objects.filter(apartment=self.apartment, is_main=True).exclude(pk=self.pk).update(is_main=False)
        super().save(*args, **kwargs)


class Availability(models.Model):
    """Tracks availability for specific dates."""
    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='availability')
    date = models.DateField()
    is_available = models.BooleanField(default=True)
    min_stay_nights = models.PositiveIntegerField(null=True, blank=True)
    max_stay_nights = models.PositiveIntegerField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['date']
        unique_together = ['apartment', 'date']
        verbose_name_plural = 'Availabilities'

    def __str__(self):
        status = "Available" if self.is_available else "Unavailable"
        return f"{self.apartment.title} - {self.date} ({status})"


class PricingRule(models.Model):
    """Dynamic pricing rules for apartments."""
    RULE_TYPES = [
        ('SEASONAL', 'Seasonal'),
        ('WEEKEND', 'Weekend'),
        ('DISCOUNT', 'Discount'),
        ('HOLIDAY', 'Holiday'),
    ]

    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='pricing_rules')
    start_date = models.DateField()
    end_date = models.DateField()
    weekday = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="0=Monday, 6=Sunday. Leave blank to apply to all days."
    )
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    priority = models.PositiveIntegerField(default=0, help_text="Higher priority rules override lower ones")

    class Meta:
        ordering = ['-priority', 'start_date']

    def __str__(self):
        return f"{self.apartment.title} - {self.rule_type} ({self.start_date} to {self.end_date})"


class Booking(models.Model):
    """Represents a booking request/reservation."""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED_BY_USER', 'Cancelled by User'),
        ('CANCELLED_BY_ADMIN', 'Cancelled by Admin'),
        ('COMPLETED', 'Completed'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('NOT_REQUIRED', 'Not Required'),
        ('UNPAID', 'Unpaid'),
        ('PAID', 'Paid'),
        ('REFUNDED', 'Refunded'),
    ]

    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    check_in = models.DateField()
    check_out = models.DateField()
    guests_count = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='EUR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='NOT_REQUIRED')
    notes = models.TextField(blank=True, help_text="Message from guest to owner")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking #{self.pk} - {self.apartment.title} by {self.user.username}"

    def get_nights(self):
        """Returns the number of nights for this booking."""
        return (self.check_out - self.check_in).days

    def calculate_total_price(self):
        """
        Calculate total price based on base price and applicable pricing rules.
        """
        from datetime import timedelta
        
        total = Decimal('0.00')
        current_date = self.check_in
        
        while current_date < self.check_out:
            # Check for pricing rules that apply to this date
            applicable_rule = self.apartment.pricing_rules.filter(
                start_date__lte=current_date,
                end_date__gte=current_date
            ).filter(
                models.Q(weekday__isnull=True) | models.Q(weekday=current_date.weekday())
            ).order_by('-priority').first()
            
            if applicable_rule:
                total += applicable_rule.price_per_night
            else:
                total += self.apartment.base_price_per_night
            
            current_date += timedelta(days=1)
        
        return total

    def clean(self):
        """Validate booking data."""
        from django.core.exceptions import ValidationError
        
        errors = {}
        
        if self.check_out and self.check_in and self.check_out <= self.check_in:
            errors['check_out'] = 'Check-out date must be after check-in date.'
        
        if self.apartment and self.guests_count and self.guests_count > self.apartment.capacity:
            errors['guests_count'] = f'Guests count exceeds apartment capacity ({self.apartment.capacity}).'
        
        if errors:
            raise ValidationError(errors)

    def has_overlap(self):
        """Check if this booking overlaps with existing confirmed bookings."""
        overlapping = Booking.objects.filter(
            apartment=self.apartment,
            status='CONFIRMED',
            check_in__lt=self.check_out,
            check_out__gt=self.check_in
        ).exclude(pk=self.pk)
        return overlapping.exists()
