from django import forms
from django.core.exceptions import ValidationError
from datetime import date
from .models import Apartment, ApartmentImage, Availability, PricingRule, Booking, Message


class BookingForm(forms.ModelForm):
    """Form for creating a booking request."""
    
    check_in = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'min': date.today().isoformat()
        })
    )
    check_out = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'min': date.today().isoformat()
        })
    )
    guests_count = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1
        })
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Any special requests or notes for the owner...'
        })
    )

    class Meta:
        model = Booking
        fields = ['check_in', 'check_out', 'guests_count', 'notes']

    def __init__(self, *args, apartment=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.apartment = apartment
        if apartment:
            self.fields['guests_count'].widget.attrs['max'] = apartment.capacity
            self.fields['guests_count'].help_text = f'Maximum {apartment.capacity} guests'

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')
        guests_count = cleaned_data.get('guests_count')

        if check_in and check_out:
            if check_out <= check_in:
                raise ValidationError('Check-out date must be after check-in date.')
            
            if check_in < date.today():
                raise ValidationError('Check-in date cannot be in the past.')

        if self.apartment and guests_count:
            if guests_count > self.apartment.capacity:
                raise ValidationError(
                    f'Number of guests exceeds apartment capacity ({self.apartment.capacity}).'
                )

        return cleaned_data

    def check_availability(self):
        """Check if the apartment is available for the selected dates."""
        check_in = self.cleaned_data.get('check_in')
        check_out = self.cleaned_data.get('check_out')
        
        if not self.apartment or not check_in or not check_out:
            return True
        
        # Use the new clean model method
        is_available, message = self.apartment.is_available_for_booking(check_in, check_out)
        return is_available


class ApartmentForm(forms.ModelForm):
    """Form for creating/editing apartments (staff only)."""
    
    class Meta:
        model = Apartment
        fields = [
            'title', 'description', 'address', 'capacity', 'bedrooms', 'bathrooms',
            'amenities', 'pricing_type', 'base_price_per_night', 'price_per_guest', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'bedrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'bathrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'pricing_type': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'base_price_per_night': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'price_per_guest': forms.HiddenInput(attrs={'id': 'id_price_per_guest'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    amenities = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter amenities separated by commas (e.g., WiFi, Air Conditioning, Parking)'
        }),
        help_text='Enter amenities separated by commas'
    )

    def clean_amenities(self):
        """Convert comma-separated string to list."""
        amenities_str = self.cleaned_data.get('amenities', '')
        if not amenities_str:
            return []
        return [a.strip() for a in amenities_str.split(',') if a.strip()]
    
    def clean(self):
        """Validate pricing configuration."""
        cleaned_data = super().clean()
        pricing_type = cleaned_data.get('pricing_type')
        base_price = cleaned_data.get('base_price_per_night')
        price_per_guest = cleaned_data.get('price_per_guest')
        
        if pricing_type == 'GUEST':
            # For guest pricing, validate that we have guest prices
            if not price_per_guest or price_per_guest == {}:
                raise ValidationError('Please set prices for each guest count when using per-guest pricing.')
            # Set a minimal base price (required by model but not used for GUEST pricing)
            if not base_price or base_price <= 0:
                # Get the price for 1 guest from price_per_guest
                if price_per_guest and '1' in price_per_guest:
                    from decimal import Decimal
                    cleaned_data['base_price_per_night'] = Decimal(str(price_per_guest['1']))
                else:
                    cleaned_data['base_price_per_night'] = Decimal('1.00')
        else:
            # For apartment pricing, ensure base price is set
            if not base_price or base_price <= 0:
                raise ValidationError('Please set a base price per night.')
            # Clear guest prices for apartment pricing
            cleaned_data['price_per_guest'] = {}
        
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Convert list to comma-separated string for display
        if self.instance and self.instance.pk and self.instance.amenities:
            self.initial['amenities'] = ', '.join(self.instance.amenities)


class ApartmentImageForm(forms.ModelForm):
    """Form for uploading apartment images."""
    
    class Meta:
        model = ApartmentImage
        fields = ['image', 'is_main', 'order']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_main': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class AvailabilityForm(forms.ModelForm):
    """Form for managing availability dates."""
    
    class Meta:
        model = Availability
        fields = ['date', 'is_available', 'min_stay_nights', 'max_stay_nights', 'note']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'min_stay_nights': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'max_stay_nights': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'note': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PricingRuleForm(forms.ModelForm):
    """Form for managing pricing rules."""
    
    class Meta:
        model = PricingRule
        fields = ['start_date', 'end_date', 'weekday', 'rule_type', 'price_per_night', 'priority']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'weekday': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('', 'All days'),
                (0, 'Monday'),
                (1, 'Tuesday'),
                (2, 'Wednesday'),
                (3, 'Thursday'),
                (4, 'Friday'),
                (5, 'Saturday'),
                (6, 'Sunday'),
            ]),
            'rule_type': forms.Select(attrs={'class': 'form-select'}),
            'price_per_night': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'priority': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date < start_date:
            raise ValidationError('End date must be after or equal to start date.')

        return cleaned_data


class BookingStatusForm(forms.Form):
    """Form for staff to update booking status."""
    STATUS_CHOICES = [
        ('CONFIRMED', 'Confirm Booking'),
        ('CANCELLED_BY_ADMIN', 'Cancel Booking'),
        ('COMPLETED', 'Mark as Completed'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class MessageForm(forms.ModelForm):
    """Form for sending a message in a conversation."""
    
    class Meta:
        model = Message
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Type your message here...'
            })
        }
        labels = {
            'body': ''
        }
