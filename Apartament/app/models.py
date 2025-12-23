from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class Apartment(models.Model):
    """Represents an apartment listing."""
    PRICING_TYPE_CHOICES = [
        ('APARTMENT', _('Per Apartment')),
        ('GUEST', _('Per Guest')),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    capacity = models.PositiveIntegerField(help_text=_("Maximum number of guests"))
    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.PositiveIntegerField(default=1)
    amenities = models.JSONField(default=list, blank=True, help_text=_("List of amenities"))
    pricing_type = models.CharField(
        max_length=20, 
        choices=PRICING_TYPE_CHOICES, 
        default='APARTMENT',
        help_text=_("Pricing model: per apartment or per guest")
    )
    base_price_per_night = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text=_("Base price per night (for apartment) or price for 1 guest")
    )
    price_per_guest = models.JSONField(
        default=dict, 
        blank=True,
        help_text=_("Price per guest count: {1: 100, 2: 150, 3: 200, etc.}")
    )
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
    
    def get_price_for_guests(self, guest_count):
        """Get the price per night based on guest count and pricing type."""
        if self.pricing_type == 'APARTMENT':
            return self.base_price_per_night
        else:  # GUEST pricing
            # Try to get exact guest count price from JSON
            guest_count_str = str(guest_count)
            if self.price_per_guest and guest_count_str in self.price_per_guest:
                return Decimal(str(self.price_per_guest[guest_count_str]))
            # Fallback to base price for 1 guest, multiply by guest count
            return self.base_price_per_night * guest_count
    
    def get_display_price(self):
        """Get the price to display in listings (for 1 guest if guest-based pricing)."""
        if self.pricing_type == 'APARTMENT':
            return self.base_price_per_night
        else:  # GUEST pricing - show price for 1 guest
            return self.get_price_for_guests(1)
    
    def get_blocked_nights(self, start_date, end_date):
        """
        Get all nights that are blocked between start_date and end_date.
        A 'night' is represented by its start date (the night of that date).
        """
        from datetime import timedelta
        blocked = set()
        
        # Get blocked dates from Availability model
        blocked_availability = self.availability.filter(
            date__gte=start_date,
            date__lt=end_date,  # A night is blocked if that DATE is blocked
            is_available=False
        ).values_list('date', flat=True)
        blocked.update(blocked_availability)
        
        return blocked
    
    def get_booked_nights(self, start_date, end_date):
        """
        Get all nights that are booked between start_date and end_date.
        A booking from check_in to check_out occupies nights: check_in, check_in+1, ..., check_out-1
        """
        from datetime import timedelta
        booked = set()
        
        # Get confirmed bookings that overlap with the date range
        bookings = self.bookings.filter(
            status__in=['CONFIRMED', 'PENDING'],
            check_in__lt=end_date,
            check_out__gt=start_date
        )
        
        for booking in bookings:
            current = max(booking.check_in, start_date)
            end = min(booking.check_out, end_date)
            while current < end:
                booked.add(current)
                current += timedelta(days=1)
        
        return booked
    
    def get_unavailable_nights(self, start_date, end_date):
        """
        Get all nights that are unavailable (blocked OR booked).
        """
        blocked = self.get_blocked_nights(start_date, end_date)
        booked = self.get_booked_nights(start_date, end_date)
        return blocked.union(booked)
    
    def is_available_for_booking(self, check_in, check_out, exclude_booking_id=None):
        """
        Check if apartment is available for a booking from check_in to check_out.
        
        A booking occupies the nights: check_in, check_in+1, ..., check_out-1
        So we need to check if any of those nights are blocked or booked.
        """
        from datetime import timedelta
        
        if check_out <= check_in:
            return False, "Check-out must be after check-in"
        
        # Check each night from check_in to check_out-1
        current = check_in
        while current < check_out:
            # Check if this night is blocked
            if self.availability.filter(date=current, is_available=False).exists():
                return False, f"Night of {current} is blocked"
            
            # Check if this night is already booked
            conflicting = self.bookings.filter(
                status__in=['CONFIRMED', 'PENDING'],
                check_in__lte=current,
                check_out__gt=current
            )
            if exclude_booking_id:
                conflicting = conflicting.exclude(pk=exclude_booking_id)
            
            if conflicting.exists():
                return False, f"Night of {current} is already booked"
            
            current += timedelta(days=1)
        
        return True, "Available"
    
    def get_calendar_data(self, start_date, end_date):
        """
        Get calendar data for displaying availability.
        
        Returns dict with:
        - blocked_nights: dates where nights are blocked (cannot check-in on these dates)
        - booked_nights: dates where nights are booked (cannot check-in on these dates)
        - unavailable_for_checkin: all dates where you cannot start a stay
        - unavailable_for_checkout: all dates where you cannot end a stay
        """
        from datetime import timedelta
        
        blocked_nights = self.get_blocked_nights(start_date, end_date)
        booked_nights = self.get_booked_nights(start_date, end_date)
        unavailable_nights = blocked_nights.union(booked_nights)
        
        # Cannot check-in on any date where that night is unavailable
        unavailable_for_checkin = unavailable_nights.copy()
        
        # Cannot check-out on a date if ANY previous night (back to some check-in) is unavailable
        # This is complex - we need to determine which checkout dates are valid
        # A checkout date D is INVALID if there's no valid check-in date before it
        # that doesn't cross an unavailable night
        
        # Simple rule: A date D cannot be a checkout if:
        # 1. The night before D (date D-1) is unavailable
        # This handles the basic case - you can only checkout on D if you stayed night D-1
        unavailable_for_checkout = set()
        
        current = start_date
        while current <= end_date:
            prev_night = current - timedelta(days=1)
            if prev_night in unavailable_nights:
                unavailable_for_checkout.add(current)
            current += timedelta(days=1)
        
        return {
            'blocked_nights': sorted([d.isoformat() for d in blocked_nights]),
            'booked_nights': sorted([d.isoformat() for d in booked_nights]),
            'unavailable_for_checkin': sorted([d.isoformat() for d in unavailable_for_checkin]),
            'unavailable_for_checkout': sorted([d.isoformat() for d in unavailable_for_checkout]),
        }
    
    def generate_ical(self):
        """Generate iCal content for this apartment's bookings and blocked dates."""
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//ApartBook//Apartment Calendar//EN',
            'CALSCALE:GREGORIAN',
            'METHOD:PUBLISH',
            f'X-WR-CALNAME:{self.title}',
        ]
        
        # Add confirmed bookings as events
        bookings = self.bookings.filter(status__in=['CONFIRMED', 'PENDING'])
        for booking in bookings:
            uid = f"booking-{booking.pk}@apartbook"
            start = booking.check_in.strftime('%Y%m%d')
            end = booking.check_out.strftime('%Y%m%d')
            summary = f"Booked - {booking.guests_count} guests"
            status = "CONFIRMED" if booking.status == 'CONFIRMED' else "TENTATIVE"
            created = booking.created_at.strftime('%Y%m%dT%H%M%SZ')
            
            lines.extend([
                'BEGIN:VEVENT',
                f'UID:{uid}',
                f'DTSTART;VALUE=DATE:{start}',
                f'DTEND;VALUE=DATE:{end}',
                f'SUMMARY:{summary}',
                f'STATUS:{status}',
                f'DTSTAMP:{created}',
                'END:VEVENT',
            ])
        
        # Add manually blocked dates as events (group consecutive dates)
        blocked_dates = list(self.availability.filter(
            is_available=False,
            source='MANUAL'
        ).order_by('date').values_list('date', 'note'))
        
        if blocked_dates:
            # Group consecutive dates
            groups = []
            current_group = {'start': blocked_dates[0][0], 'end': blocked_dates[0][0], 'note': blocked_dates[0][1]}
            
            for date_val, note in blocked_dates[1:]:
                if date_val == current_group['end'] + timedelta(days=1):
                    current_group['end'] = date_val
                else:
                    groups.append(current_group)
                    current_group = {'start': date_val, 'end': date_val, 'note': note}
            groups.append(current_group)
            
            for i, group in enumerate(groups):
                uid = f"blocked-{self.pk}-{i}@apartbook"
                start = group['start'].strftime('%Y%m%d')
                # End date is exclusive in iCal, so add 1 day
                end = (group['end'] + timedelta(days=1)).strftime('%Y%m%d')
                summary = group['note'] or 'Blocked'
                
                lines.extend([
                    'BEGIN:VEVENT',
                    f'UID:{uid}',
                    f'DTSTART;VALUE=DATE:{start}',
                    f'DTEND;VALUE=DATE:{end}',
                    f'SUMMARY:{summary}',
                    'STATUS:CONFIRMED',
                    f'DTSTAMP:{timezone.now().strftime("%Y%m%dT%H%M%SZ")}',
                    'END:VEVENT',
                ])
        
        lines.append('END:VCALENDAR')
        
        return '\r\n'.join(lines)


def apartment_image_path(instance, filename):
    """
    Generate a clean, incremental filename for apartment images.
    Format: apartments/{apartment_id}/{next_id}.{extension}
    """
    import os
    from django.utils import timezone
    
    # Get file extension
    ext = os.path.splitext(filename)[1].lower()
    if not ext:
        ext = '.jpg'
    
    # Generate a unique ID based on timestamp and random suffix
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    import random
    random_suffix = random.randint(100, 999)
    
    # If apartment exists, use its ID; otherwise use 'new'
    if instance.apartment_id:
        apt_id = instance.apartment_id
    else:
        apt_id = 'new'
    
    return f'apartments/{apt_id}/{timestamp}_{random_suffix}{ext}'


class ApartmentImage(models.Model):
    """Images for an apartment listing."""
    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=apartment_image_path)
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
    SOURCE_CHOICES = [
        ('MANUAL', _('Manual')),
        ('ICAL', _('iCal Import')),
    ]
    
    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='availability')
    date = models.DateField()
    is_available = models.BooleanField(default=True)
    min_stay_nights = models.PositiveIntegerField(null=True, blank=True)
    max_stay_nights = models.PositiveIntegerField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='MANUAL')
    external_uid = models.CharField(max_length=255, blank=True, help_text=_("UID from external iCal event"))
    ical_feed = models.ForeignKey(
        'ICalFeed', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='blocked_dates',
        help_text=_("The iCal feed this block came from")
    )

    class Meta:
        ordering = ['date']
        unique_together = ['apartment', 'date']
        verbose_name_plural = _('Availabilities')

    def __str__(self):
        status = _("Available") if self.is_available else _("Unavailable")
        return f"{self.apartment.title} - {self.date} ({status})"


class ICalFeed(models.Model):
    """External iCal feeds to sync with apartment calendars."""
    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='ical_feeds')
    name = models.CharField(max_length=100, help_text=_("e.g., Airbnb, Booking.com"))
    url = models.URLField(max_length=500, help_text=_("iCal feed URL"))
    is_active = models.BooleanField(default=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(max_length=50, blank=True)
    sync_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('iCal Feed')
        verbose_name_plural = _('iCal Feeds')

    def __str__(self):
        return f"{self.apartment.title} - {self.name}"
    
    def sync(self):
        """Sync this iCal feed and update blocked dates."""
        import requests
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        try:
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            
            # Parse iCal content
            events = self._parse_ical(response.text)
            
            # Remove old entries from this feed (using FK relationship)
            Availability.objects.filter(ical_feed=self).delete()
            
            # Create new blocked dates from events
            today = datetime.now().date()
            dates_created = 0
            for event in events:
                start_date = event.get('start')
                end_date = event.get('end')
                uid = event.get('uid', '')
                summary = event.get('summary', 'External Booking')
                
                if start_date and end_date and start_date >= today:
                    # Block each night in the event range
                    current = start_date
                    while current < end_date:
                        # Skip if there's already a manual block
                        if not Availability.objects.filter(
                            apartment=self.apartment,
                            date=current,
                            source='MANUAL'
                        ).exists():
                            Availability.objects.update_or_create(
                                apartment=self.apartment,
                                date=current,
                                ical_feed=self,
                                defaults={
                                    'is_available': False,
                                    'note': f"{self.name}: {summary}",
                                    'source': 'ICAL',
                                    'external_uid': uid
                                }
                            )
                            dates_created += 1
                        current += timedelta(days=1)
            
            self.last_synced = timezone.now()
            self.last_sync_status = 'SUCCESS'
            self.sync_error = ''
            self.save()
            
            return True, f"Synced {len(events)} events, {dates_created} nights blocked"
            
        except Exception as e:
            self.last_synced = timezone.now()
            self.last_sync_status = 'ERROR'
            self.sync_error = str(e)
            self.save()
            return False, str(e)
    
    def _parse_ical(self, ical_content):
        """Parse iCal content and extract events."""
        from datetime import datetime, date
        
        events = []
        current_event = None
        
        lines = ical_content.replace('\r\n ', '').replace('\r\n\t', '').split('\r\n')
        if len(lines) <= 1:
            lines = ical_content.replace('\n ', '').replace('\n\t', '').split('\n')
        
        for line in lines:
            line = line.strip()
            
            if line == 'BEGIN:VEVENT':
                current_event = {}
            elif line == 'END:VEVENT':
                if current_event:
                    events.append(current_event)
                current_event = None
            elif current_event is not None:
                if line.startswith('DTSTART'):
                    date_str = line.split(':', 1)[-1] if ':' in line else ''
                    current_event['start'] = self._parse_ical_date(date_str)
                elif line.startswith('DTEND'):
                    date_str = line.split(':', 1)[-1] if ':' in line else ''
                    current_event['end'] = self._parse_ical_date(date_str)
                elif line.startswith('UID:'):
                    current_event['uid'] = line[4:]
                elif line.startswith('SUMMARY:'):
                    current_event['summary'] = line[8:]
        
        return events
    
    def _parse_ical_date(self, date_str):
        """Parse various iCal date formats."""
        from datetime import datetime, date
        
        date_str = date_str.strip()
        
        # Try different formats
        formats = [
            '%Y%m%d',           # 20251215
            '%Y%m%dT%H%M%S',    # 20251215T120000
            '%Y%m%dT%H%M%SZ',   # 20251215T120000Z
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str[:len(fmt.replace('%', ''))], fmt.replace('%', '').replace('Y', '1111').replace('m', '11').replace('d', '11').replace('T', 'T').replace('H', '11').replace('M', '11').replace('S', '11').replace('Z', 'Z'))
            except:
                pass
        
        # Simple parsing
        try:
            if 'T' in date_str:
                date_part = date_str.split('T')[0]
            else:
                date_part = date_str[:8]
            
            year = int(date_part[:4])
            month = int(date_part[4:6])
            day = int(date_part[6:8])
            return date(year, month, day)
        except:
            return None


class PricingRule(models.Model):
    """Dynamic pricing rules for apartments."""
    RULE_TYPES = [
        ('SEASONAL', _('Seasonal')),
        ('WEEKEND', _('Weekend')),
        ('HOLIDAY', _('Holiday')),
    ]

    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='pricing_rules')
    start_date = models.DateField()
    end_date = models.DateField()
    weekday = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text=_("0=Monday, 6=Sunday. Leave blank to apply to all days.")
    )
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    priority = models.PositiveIntegerField(default=0, help_text=_("Higher priority rules override lower ones"))

    class Meta:
        ordering = ['-priority', 'start_date']

    def __str__(self):
        return f"{self.apartment.title} - {self.rule_type} ({self.start_date} to {self.end_date})"


class Booking(models.Model):
    """Represents a booking request/reservation."""
    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('CONFIRMED', _('Confirmed')),
        ('CANCELLED_BY_USER', _('Cancelled by User')),
        ('CANCELLED_BY_ADMIN', _('Cancelled by Admin')),
        ('COMPLETED', _('Completed')),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('NOT_REQUIRED', _('Not Required')),
        ('UNPAID', _('Unpaid')),
        ('PAID', _('Paid')),
        ('REFUNDED', _('Refunded')),
    ]

    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    check_in = models.DateField()
    check_out = models.DateField()
    guests_count = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_breakdown = models.JSONField(default=list, blank=True, help_text=_('Detailed price breakdown per day'))
    currency = models.CharField(max_length=3, default='RON')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='NOT_REQUIRED')
    notes = models.TextField(blank=True, help_text=_("Message from guest to owner"))
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
        Calculate total price based on guest count, pricing type, and pricing rules.
        Returns (total_price, price_breakdown).
        
        Price breakdown includes per-day details with prices.
        """
        from datetime import timedelta
        
        total = Decimal('0.00')
        breakdown = []
        current_date = self.check_in
        
        # Get base price based on guest count and pricing type
        base_price_for_guests = self.apartment.get_price_for_guests(self.guests_count)
        
        while current_date < self.check_out:
            # Get base price for the day (from pricing rules or apartment base price)
            applicable_rule = self.apartment.pricing_rules.filter(
                start_date__lte=current_date,
                end_date__gte=current_date
            ).filter(
                models.Q(weekday__isnull=True) | models.Q(weekday=current_date.weekday())
            ).order_by('-priority').first()
            
            if applicable_rule:
                day_price = applicable_rule.price_per_night
            else:
                day_price = base_price_for_guests
            
            breakdown.append({
                'date': current_date.isoformat(),
                'price': str(day_price),
            })
            
            total += day_price
            current_date += timedelta(days=1)
        
        return total, breakdown

    def clean(self):
        """Validate booking data."""
        from django.core.exceptions import ValidationError
        
        errors = {}
        
        if self.check_out and self.check_in and self.check_out <= self.check_in:
            errors['check_out'] = _('Check-out date must be after check-in date.')
        
        # Use apartment_id to avoid RelatedObjectDoesNotExist when apartment not yet set
        if self.apartment_id and self.guests_count:
            if self.guests_count > self.apartment.capacity:
                errors['guests_count'] = _('Guests count exceeds apartment capacity (%(capacity)s).') % {
                    'capacity': self.apartment.capacity
                }
        
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


class Conversation(models.Model):
    """A conversation thread between a guest and admin, typically about a booking."""
    booking = models.OneToOneField(
        Booking, 
        on_delete=models.CASCADE, 
        related_name='conversation',
        null=True, 
        blank=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.booking:
            return f"Conversation: {self.user.username} - {self.booking.apartment.title}"
        return f"Conversation: {self.user.username}"

    def get_last_message(self):
        """Get the most recent message in this conversation."""
        return self.messages.order_by('-created_at').first()

    def get_unread_count(self, for_user):
        """Get count of unread messages for a specific user."""
        return self.messages.filter(is_read=False).exclude(sender=for_user).count()


class Message(models.Model):
    """A single message within a conversation."""
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.username} at {self.created_at}"

