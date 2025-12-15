from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils.translation import gettext as _
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Avg, Max
from datetime import date, timedelta
from decimal import Decimal
import json

from .models import Apartment, ApartmentImage, Availability, PricingRule, Booking, Conversation, Message
from .forms import (
    BookingForm, ApartmentForm, ApartmentImageForm, 
    AvailabilityForm, PricingRuleForm, BookingStatusForm, BookingEditForm, MessageForm
)
from .emails import (
    send_new_booking_notification,
    send_booking_confirmed_notification,
    send_booking_cancelled_notification
)


# =============================================================================
# PUBLIC VIEWS
# =============================================================================

def landing_page(request):
    """Landing page with featured apartments."""
    featured_apartments = Apartment.objects.filter(is_active=True)[:6]
    return render(request, 'public/landing.html', {
        'featured_apartments': featured_apartments,
    })


class ApartmentListView(ListView):
    """List all active apartments with optional filters."""
    model = Apartment
    template_name = 'public/apartment_list.html'
    context_object_name = 'apartments'
    paginate_by = 12

    def get_queryset(self):
        queryset = Apartment.objects.filter(is_active=True)
        
        # Filter by availability dates
        check_in = self.request.GET.get('check_in')
        check_out = self.request.GET.get('check_out')
        if check_in and check_out:
            try:
                from datetime import datetime
                check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
                check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
                
                # Filter to only available apartments
                available_apartment_ids = []
                for apartment in queryset:
                    is_available, _ = apartment.is_available_for_booking(check_in_date, check_out_date)
                    if is_available:
                        available_apartment_ids.append(apartment.pk)
                
                queryset = queryset.filter(pk__in=available_apartment_ids)
            except ValueError:
                pass
        
        # Filter by city
        city = self.request.GET.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        # Filter by country
        country = self.request.GET.get('country')
        if country:
            queryset = queryset.filter(country__icontains=country)
        
        # Filter by capacity
        guests = self.request.GET.get('guests')
        if guests:
            try:
                queryset = queryset.filter(capacity__gte=int(guests))
            except ValueError:
                pass
        
        # Filter by price range
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            try:
                queryset = queryset.filter(base_price_per_night__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                queryset = queryset.filter(base_price_per_night__lte=float(max_price))
            except ValueError:
                pass
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass guest filter value to template for pricing display
        guests = self.request.GET.get('guests')
        filtered_guests = int(guests) if guests and guests.isdigit() else 1
        context['filtered_guests'] = filtered_guests
        
        # Add price for filtered guest count to each apartment
        apartments = context['apartments']
        for apartment in apartments:
            apartment.display_price_for_filter = apartment.get_price_for_guests(filtered_guests)
        
        return context
        return context


class ApartmentDetailView(DetailView):
    """Show apartment details with availability and booking form."""
    model = Apartment
    template_name = 'public/apartment_detail.html'
    context_object_name = 'apartment'

    def get_queryset(self):
        return Apartment.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        apartment = self.object
        
        # Get images
        context['images'] = apartment.images.all()
        
        # Initialize booking form
        context['booking_form'] = BookingForm(apartment=apartment)
        
        # Get calendar data for availability
        today = date.today()
        three_months_later = today + timedelta(days=90)
        
        # Use the new clean calendar data method
        calendar_data = apartment.get_calendar_data(today, three_months_later)
        
        # For flatpickr:
        # - Check-in picker: disable dates where that night is unavailable
        # - Check-out picker: disable dates where the previous night is unavailable
        context['unavailable_for_checkin'] = calendar_data['unavailable_for_checkin']
        context['unavailable_for_checkout'] = calendar_data['unavailable_for_checkout']
        
        # Legacy support - keep unavailable_dates for any other usage
        context['unavailable_dates'] = calendar_data['unavailable_for_checkin']
        context['blocked_checkin_dates'] = calendar_data['blocked_nights']
        context['booked_dates'] = calendar_data['booked_nights']
        
        return context


@login_required
def create_booking(request, slug):
    """Handle booking form submission."""
    # Prevent staff users from creating bookings
    if request.user.is_staff:
        messages.error(request, _('Staff members cannot create bookings. Please use a regular user account.'))
        return redirect('apartment_detail', slug=slug)
    
    apartment = get_object_or_404(Apartment, slug=slug, is_active=True)
    
    if request.method == 'POST':
        form = BookingForm(request.POST, apartment=apartment)
        if form.is_valid():
            # Check availability
            if not form.check_availability():
                messages.error(request, _('The apartment is not available for the selected dates.'))
                return redirect('apartment_detail', slug=slug)
            
            # Create booking
            booking = form.save(commit=False)
            booking.apartment = apartment
            booking.user = request.user
            
            # Calculate price
            total_price, price_breakdown = booking.calculate_total_price()
            booking.total_price = total_price
            booking.price_breakdown = price_breakdown
            
            booking.save()
            
            # Send email notification to admin
            send_new_booking_notification(booking)
            
            messages.success(request, _('Your booking request has been submitted! The owner will review it shortly.'))
            return redirect('my_bookings')
        else:
            for error in form.errors.values():
                messages.error(request, error)
            return redirect('apartment_detail', slug=slug)
    
    return redirect('apartment_detail', slug=slug)


def apartment_availability_api(request, slug):
    """API endpoint for fetching apartment availability (for calendar)."""
    apartment = get_object_or_404(Apartment, slug=slug, is_active=True)
    
    today = date.today()
    end_date = today + timedelta(days=365)
    
    # Use the clean model method
    calendar_data = apartment.get_calendar_data(today, end_date)
    
    return JsonResponse({
        'unavailable_for_checkin': calendar_data['unavailable_for_checkin'],
        'unavailable_for_checkout': calendar_data['unavailable_for_checkout'],
        'blocked_nights': calendar_data['blocked_nights'],
        'booked_nights': calendar_data['booked_nights'],
        'base_price': str(apartment.base_price_per_night),
    })


def apartment_price_api(request, slug):
    """API endpoint for calculating booking price with dynamic pricing and guest count."""
    apartment = get_object_or_404(Apartment, slug=slug, is_active=True)
    
    check_in_str = request.GET.get('check_in')
    check_out_str = request.GET.get('check_out')
    guests_count = request.GET.get('guests_count', 1)
    
    if not check_in_str or not check_out_str:
        return JsonResponse({'error': 'check_in and check_out are required'}, status=400)
    
    try:
        from datetime import datetime
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        guests_count = int(guests_count)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format or guest count'}, status=400)
    
    if check_out <= check_in:
        return JsonResponse({'error': 'check_out must be after check_in'}, status=400)
    
    # Get base price based on guest count and pricing type
    base_price_for_guests = apartment.get_price_for_guests(guests_count)
    
    # Calculate total price with pricing rules
    total = 0
    current_date = check_in
    daily_prices = []
    
    while current_date < check_out:
        # Check for applicable pricing rule
        applicable_rule = PricingRule.objects.filter(
            apartment=apartment,
            start_date__lte=current_date,
            end_date__gte=current_date
        ).order_by('-priority').first()
        
        if applicable_rule:
            day_price = applicable_rule.price_per_night
        else:
            day_price = base_price_for_guests
        
        daily_prices.append({
            'date': current_date.isoformat(),
            'price': str(day_price)
        })
        total += day_price
        current_date += timedelta(days=1)
    
    nights = (check_out - check_in).days
    
    return JsonResponse({
        'total_price': str(total),
        'nights': nights,
        'base_price': str(base_price_for_guests),
        'pricing_type': apartment.pricing_type,
        'guests_count': guests_count,
        'daily_prices': daily_prices,
    })


# =============================================================================
# USER DASHBOARD VIEWS
# =============================================================================

class NonStaffRequiredMixin(UserPassesTestMixin):
    """Mixin to require non-staff users (regular users only)."""
    def test_func(self):
        return self.request.user.is_authenticated and not self.request.user.is_staff
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated and self.request.user.is_staff:
            messages.error(self.request, _('Staff members cannot access user bookings. Please use the Staff Dashboard.'))
            return redirect('staff_dashboard')
        return super().handle_no_permission()


class MyBookingsListView(NonStaffRequiredMixin, LoginRequiredMixin, ListView):
    """List current user's bookings."""
    model = Booking
    template_name = 'dashboard/bookings_list.html'
    context_object_name = 'bookings'

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).order_by('-created_at')


class MyBookingDetailView(NonStaffRequiredMixin, LoginRequiredMixin, DetailView):
    """Show booking details for current user."""
    model = Booking
    template_name = 'dashboard/booking_detail.html'
    context_object_name = 'booking'

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)


@login_required
def cancel_booking(request, pk):
    """Allow user to cancel their pending booking."""
    # Prevent staff from cancelling bookings through user interface
    if request.user.is_staff:
        messages.error(request, _('Staff members cannot cancel bookings through this interface. Please use the Staff Dashboard.'))
        return redirect('staff_dashboard')
    
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    
    if booking.status == 'PENDING':
        booking.status = 'CANCELLED_BY_USER'
        booking.save()
        # Send notification (user cancelled their own booking)
        send_booking_cancelled_notification(booking, cancelled_by='user')
        messages.success(request, _('Your booking has been cancelled.'))
    else:
        messages.error(request, _('Only pending bookings can be cancelled.'))
    
    return redirect('my_booking_detail', pk=pk)


# =============================================================================
# STAFF DASHBOARD VIEWS
# =============================================================================

class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin to require staff status."""
    def test_func(self):
        return self.request.user.is_staff


class StaffApartmentListView(StaffRequiredMixin, ListView):
    """Staff view: list all apartments."""
    model = Apartment
    template_name = 'staff/apartments_list.html'
    context_object_name = 'apartments'

    def get_queryset(self):
        return Apartment.objects.all().order_by('-created_at')


class StaffApartmentCreateView(StaffRequiredMixin, CreateView):
    """Staff view: create new apartment."""
    model = Apartment
    form_class = ApartmentForm
    template_name = 'staff/apartment_form.html'
    success_url = reverse_lazy('staff_apartments')

    def form_valid(self, form):
        messages.success(self.request, _('Apartment created successfully!'))
        return super().form_valid(form)


class StaffApartmentUpdateView(StaffRequiredMixin, UpdateView):
    """Staff view: edit apartment."""
    model = Apartment
    form_class = ApartmentForm
    template_name = 'staff/apartment_form.html'
    success_url = reverse_lazy('staff_apartments')

    def form_valid(self, form):
        messages.success(self.request, _('Apartment updated successfully!'))
        return super().form_valid(form)


class StaffApartmentDeleteView(StaffRequiredMixin, DeleteView):
    """Staff view: delete apartment."""
    model = Apartment
    template_name = 'staff/apartment_confirm_delete.html'
    success_url = reverse_lazy('staff_apartments')

    def form_valid(self, form):
        messages.success(self.request, _('Apartment deleted successfully!'))
        return super().form_valid(form)


@staff_member_required
@staff_member_required
def staff_apartment_images(request, pk):
    """Staff view: manage apartment images with drag-and-drop upload."""
    apartment = get_object_or_404(Apartment, pk=pk)
    
    if request.method == 'POST':
        # Handle multiple image upload via AJAX
        images_files = request.FILES.getlist('images')
        if images_files:
            uploaded_count = 0
            errors = []
            
            # Get current max order
            from django.db.models import Max
            max_order_result = apartment.images.aggregate(Max('order'))['order__max']
            max_order = max_order_result if max_order_result is not None else -1
            
            for uploaded_file in images_files:
                try:
                    max_order += 1
                    image = ApartmentImage.objects.create(
                        apartment=apartment,
                        image=uploaded_file,
                        order=max_order,
                        is_main=False  # Will be set by reordering
                    )
                    uploaded_count += 1
                except Exception as e:
                    errors.append(str(e))
            
            # Set first image as main if no main image exists
            if not apartment.images.filter(is_main=True).exists():
                first_image = apartment.images.order_by('order').first()
                if first_image:
                    first_image.is_main = True
                    first_image.save()
            
            # Check if AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': uploaded_count > 0,
                    'uploaded': uploaded_count,
                    'errors': errors
                })
            
            # Regular form submission
            if uploaded_count > 0:
                messages.success(request, _(f'{uploaded_count} image(s) uploaded successfully!'))
            if errors:
                messages.warning(request, _('Some images failed to upload.'))
            
            return redirect('staff_apartment_images', pk=pk)
    
    images = apartment.images.all().order_by('order')
    return render(request, 'staff/apartment_images.html', {
        'apartment': apartment,
        'images': images,
    })


@staff_member_required
def staff_reorder_images(request, pk):
    """Staff view: handle image reordering via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})
    
    apartment = get_object_or_404(Apartment, pk=pk)
    
    try:
        import json
        data = json.loads(request.body)
        order = data.get('order', [])
        
        # Update order and set main image
        for index, image_id in enumerate(order):
            try:
                image = ApartmentImage.objects.get(pk=image_id, apartment=apartment)
                image.order = index
                image.is_main = (index == 0)  # First image is main
                image.save()
            except ApartmentImage.DoesNotExist:
                pass
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@staff_member_required
def staff_delete_image(request, pk):
    """Staff view: delete apartment image."""
    image = get_object_or_404(ApartmentImage, pk=pk)
    apartment_pk = image.apartment.pk
    image.delete()
    messages.success(request, _('Image deleted successfully!'))
    return redirect('staff_apartment_images', pk=apartment_pk)


class StaffBookingsListView(StaffRequiredMixin, ListView):
    """Staff view: list all bookings."""
    model = Booking
    template_name = 'staff/bookings_list.html'
    context_object_name = 'bookings'
    paginate_by = 20

    def get_queryset(self):
        queryset = Booking.objects.all().order_by('-created_at')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by apartment
        apartment_id = self.request.GET.get('apartment')
        if apartment_id:
            queryset = queryset.filter(apartment_id=apartment_id)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['apartments'] = Apartment.objects.all()
        context['status_choices'] = Booking.STATUS_CHOICES
        return context


@staff_member_required
def staff_booking_detail(request, pk):
    """Staff view: booking detail with status management and editing."""
    booking = get_object_or_404(Booking, pk=pk)
    old_status = booking.status
    
    if request.method == 'POST':
        # Check which form was submitted
        if 'update_status' in request.POST:
            status_form = BookingStatusForm(request.POST)
            edit_form = BookingEditForm(instance=booking)
            
            if status_form.is_valid():
                new_status = status_form.cleaned_data['status']
                booking.status = new_status
                booking.save()
                
                # Send email notifications based on status change
                if new_status == 'CONFIRMED' and old_status != 'CONFIRMED':
                    send_booking_confirmed_notification(booking)
                elif new_status == 'CANCELLED_BY_ADMIN':
                    send_booking_cancelled_notification(booking, cancelled_by='admin')
                
                messages.success(request, _('Booking status updated to %(status)s!') % {
                    'status': booking.get_status_display()
                })
                return redirect('staff_booking_detail', pk=pk)
        
        elif 'update_booking' in request.POST:
            edit_form = BookingEditForm(request.POST, instance=booking)
            status_form = BookingStatusForm()
            
            if edit_form.is_valid():
                # Save the form but don't commit yet
                booking = edit_form.save(commit=False)
                
                # Recalculate total price
                try:
                    total_price, price_breakdown = booking.calculate_total_price()
                    booking.total_price = total_price
                    booking.price_breakdown = price_breakdown
                    booking.save()
                    
                    messages.success(request, _('Booking updated successfully! New total: %(price)s') % {
                        'price': total_price
                    })
                    return redirect('staff_booking_detail', pk=pk)
                except Exception as e:
                    messages.error(request, _('Error calculating price: %(error)s') % {
                        'error': str(e)
                    })
        else:
            status_form = BookingStatusForm()
            edit_form = BookingEditForm(instance=booking)
    else:
        status_form = BookingStatusForm()
        edit_form = BookingEditForm(instance=booking)
    
    # Get calendar availability data for the apartment (excluding current booking)
    start_date = date.today()
    end_date = start_date + timedelta(days=365)
    calendar_data = booking.apartment.get_calendar_data(start_date, end_date)
    
    # Exclude current booking's dates from unavailable dates
    current_booking_dates = []
    current = booking.check_in
    while current < booking.check_out:
        current_booking_dates.append(current.isoformat())
        current += timedelta(days=1)
    
    # Remove current booking dates from unavailable lists
    unavailable_for_checkin = [d for d in calendar_data['unavailable_for_checkin'] if d not in current_booking_dates]
    unavailable_for_checkout = [d for d in calendar_data['unavailable_for_checkout'] if d not in current_booking_dates]
    
    return render(request, 'staff/booking_detail.html', {
        'booking': booking,
        'form': status_form,
        'edit_form': edit_form,
        'unavailable_for_checkin': unavailable_for_checkin,
        'unavailable_for_checkout': unavailable_for_checkout,
    })


@staff_member_required
def staff_availability(request, pk):
    """Staff view: manage apartment availability."""
    apartment = get_object_or_404(Apartment, pk=pk)
    
    if request.method == 'POST':
        form = AvailabilityForm(request.POST)
        if form.is_valid():
            availability = form.save(commit=False)
            availability.apartment = apartment
            # Update or create for this date
            Availability.objects.update_or_create(
                apartment=apartment,
                date=availability.date,
                defaults={
                    'is_available': availability.is_available,
                    'min_stay_nights': availability.min_stay_nights,
                    'max_stay_nights': availability.max_stay_nights,
                    'note': availability.note,
                }
            )
            messages.success(request, _('Availability updated!'))
            return redirect('staff_availability', pk=pk)
    else:
        form = AvailabilityForm()
    
    # Get availability for next 3 months
    today = date.today()
    three_months = today + timedelta(days=90)
    availabilities = Availability.objects.filter(
        apartment=apartment,
        date__gte=today,
        date__lte=three_months
    ).order_by('date')
    
    # Get bookings for calendar display
    bookings = Booking.objects.filter(
        apartment=apartment,
        status='CONFIRMED',
        check_out__gte=today
    )
    
    return render(request, 'staff/availability.html', {
        'apartment': apartment,
        'form': form,
        'availability_list': availabilities,
        'upcoming_bookings': bookings,
    })


@staff_member_required
def staff_calendar(request, pk):
    """Staff view: visual calendar for apartment bookings and availability."""
    apartment = get_object_or_404(Apartment, pk=pk)
    return render(request, 'staff/calendar.html', {
        'apartment': apartment,
    })


@staff_member_required
def staff_calendar_events_api(request, pk):
    """API endpoint for calendar events (bookings and blocked dates)."""
    apartment = get_object_or_404(Apartment, pk=pk)
    
    start_str = request.GET.get('start', '')
    end_str = request.GET.get('end', '')
    
    events = []
    
    # Get bookings
    bookings = Booking.objects.filter(
        apartment=apartment,
        status__in=['PENDING', 'CONFIRMED']
    )
    
    for booking in bookings:
        color = '#198754' if booking.status == 'CONFIRMED' else '#ffc107'
        events.append({
            'id': f'booking-{booking.pk}',
            'title': f'{booking.user.username} ({booking.guests_count} guests)',
            'start': booking.check_in.isoformat(),
            'end': booking.check_out.isoformat(),
            'color': color,
            'url': f'/staff/bookings/{booking.pk}/',
            'extendedProps': {
                'type': 'booking',
                'status': booking.status,
            }
        })
    
    # Get blocked dates
    blocked_dates = Availability.objects.filter(
        apartment=apartment,
        is_available=False
    )
    
    for blocked in blocked_dates:
        events.append({
            'id': f'blocked-{blocked.pk}',
            'title': blocked.note or _('Blocked'),
            'start': blocked.date.isoformat(),
            'end': blocked.date.isoformat(),
            'color': '#dc3545',
            'display': 'background',
            'extendedProps': {
                'type': 'blocked',
            }
        })
    
    return JsonResponse(events, safe=False)


@staff_member_required
def staff_global_calendar(request):
    """Staff view: global calendar showing all apartments' bookings."""
    apartments = Apartment.objects.all().order_by('title')
    return render(request, 'staff/global_calendar.html', {
        'apartments': apartments,
    })


@staff_member_required
def staff_global_calendar_events_api(request):
    """API endpoint for global calendar events across all apartments."""
    from datetime import timedelta
    events = []
    
    # Get all confirmed and pending bookings
    bookings = Booking.objects.filter(
        status__in=['PENDING', 'CONFIRMED']
    ).select_related('apartment', 'user')
    
    for booking in bookings:
        color = '#198754' if booking.status == 'CONFIRMED' else '#ffc107'
        base_title = f'{booking.apartment.title} - {booking.user.username} ({booking.guests_count} guests)'
        
        # Create events for each day of the booking
        current_date = booking.check_in
        while current_date <= booking.check_out:
            if current_date == booking.check_in:
                day_type = 'Check-in'
            elif current_date == booking.check_out:
                day_type = 'Check-out'
            else:
                day_type = 'Stay-over'
            
            events.append({
                'id': f'booking-{booking.pk}-{current_date.isoformat()}',
                'title': f'{base_title}',
                'start': current_date.isoformat(),
                'end': current_date.isoformat(),
                'color': color,
                'url': f'/en/staff/bookings/{booking.pk}/',
                'allDay': True,
                'extendedProps': {
                    'type': 'booking',
                    'status': booking.status,
                    'apartment': booking.apartment.title,
                    'apartmentId': booking.apartment.pk,
                    'dayType': day_type,
                }
            })
            current_date += timedelta(days=1)
    
    # Get all blocked dates
    blocked_dates = Availability.objects.filter(
        is_available=False
    ).select_related('apartment')
    
    for blocked in blocked_dates:
        events.append({
            'id': f'blocked-{blocked.pk}',
            'title': f'{blocked.apartment.title} - {blocked.note or "Blocked"}',
            'start': blocked.date.isoformat(),
            'end': blocked.date.isoformat(),
            'color': '#dc3545',
            'display': 'background',
            'extendedProps': {
                'type': 'blocked',
                'apartment': blocked.apartment.title,
                'apartmentId': blocked.apartment.pk,
            }
        })
    
    return JsonResponse(events, safe=False)


@staff_member_required
def staff_pricing_rules(request, pk):
    """Staff view: manage pricing rules."""
    apartment = get_object_or_404(Apartment, pk=pk)
    
    if request.method == 'POST':
        form = PricingRuleForm(request.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.apartment = apartment
            rule.save()
            messages.success(request, _('Pricing rule added!'))
            return redirect('staff_pricing_rules', pk=pk)
    else:
        form = PricingRuleForm()
    
    rules = apartment.pricing_rules.all().order_by('-priority', 'start_date')
    
    return render(request, 'staff/pricing_rules.html', {
        'apartment': apartment,
        'form': form,
        'pricing_rules': rules,
    })


@staff_member_required
def staff_delete_pricing_rule(request, pk):
    """Staff view: delete pricing rule."""
    rule = get_object_or_404(PricingRule, pk=pk)
    apartment_pk = rule.apartment.pk
    rule.delete()
    messages.success(request, _('Pricing rule deleted!'))
    return redirect('staff_pricing_rules', pk=apartment_pk)


@staff_member_required
@staff_member_required
def staff_delete_availability(request, pk):
    """Staff view: delete availability entry."""
    availability = get_object_or_404(Availability, pk=pk)
    apartment_pk = availability.apartment.pk
    availability.delete()
    messages.success(request, _('Availability entry deleted!'))
    return redirect('staff_availability', pk=apartment_pk)


@staff_member_required
@staff_member_required
def staff_block_dates(request, pk):
    """Staff view: block date range for an apartment (blocking nights)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})
    
    apartment = get_object_or_404(Apartment, pk=pk)
    
    try:
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        note = request.POST.get('note', '').strip()
        
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
        
        if start_date > end_date:
            return JsonResponse({'success': False, 'error': _('Start date must be before end date')})
        
        if start_date < date.today():
            return JsonResponse({'success': False, 'error': _('Cannot block past dates')})
        
        # Check for existing bookings that occupy any of the nights we want to block
        # A booking occupies nights from check_in to check_out-1
        # So we check if any booking's nights overlap with our range
        existing_bookings = Booking.objects.filter(
            apartment=apartment,
            status__in=['PENDING', 'CONFIRMED'],
            check_in__lte=end_date,  # Booking starts on or before our end
            check_out__gt=start_date  # Booking ends after our start (so it occupies at least one night in range)
        )
        
        if existing_bookings.exists():
            return JsonResponse({
                'success': False, 
                'error': _('Cannot block nights that have existing bookings')
            })
        
        # Create blocked dates (each date represents a blocked NIGHT)
        current_date = start_date
        blocked_count = 0
        while current_date <= end_date:
            Availability.objects.update_or_create(
                apartment=apartment,
                date=current_date,
                defaults={
                    'is_available': False,
                    'note': note or _('Blocked')
                }
            )
            blocked_count += 1
            current_date += timedelta(days=1)
        
        return JsonResponse({
            'success': True,
            'message': _(f'{blocked_count} night(s) blocked successfully')
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@staff_member_required
@staff_member_required
def staff_unblock_date(request, pk, availability_id):
    """Staff view: unblock a single date."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})
    
    apartment = get_object_or_404(Apartment, pk=pk)
    availability = get_object_or_404(Availability, pk=availability_id, apartment=apartment)
    
    availability.delete()
    
    return JsonResponse({'success': True, 'message': _('Date unblocked successfully')})


# =============================================================================
# ICAL IMPORT/EXPORT VIEWS
# =============================================================================

def apartment_ical_export(request, pk):
    """Public endpoint to export apartment calendar as iCal."""
    apartment = get_object_or_404(Apartment, pk=pk)
    
    ical_content = apartment.generate_ical()
    
    response = HttpResponse(ical_content, content_type='text/calendar')
    response['Content-Disposition'] = f'attachment; filename="{apartment.slug}-calendar.ics"'
    return response


@staff_member_required
def staff_ical_feeds(request, pk):
    """Staff view: manage iCal feeds for an apartment."""
    from .models import ICalFeed
    
    apartment = get_object_or_404(Apartment, pk=pk)
    feeds = apartment.ical_feeds.all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            name = request.POST.get('name', '').strip()
            url = request.POST.get('url', '').strip()
            
            if name and url:
                feed = ICalFeed.objects.create(
                    apartment=apartment,
                    name=name,
                    url=url
                )
                # Try initial sync
                success, message = feed.sync()
                if success:
                    messages.success(request, _(f'iCal feed "{name}" added and synced successfully!'))
                else:
                    messages.warning(request, _(f'iCal feed "{name}" added but sync failed: {message}'))
            else:
                messages.error(request, _('Please provide both name and URL'))
                
        elif action == 'delete':
            feed_id = request.POST.get('feed_id')
            try:
                feed = ICalFeed.objects.get(pk=feed_id, apartment=apartment)
                # Blocked dates with ical_feed FK will be cascade deleted
                feed.delete()
                messages.success(request, _('iCal feed deleted!'))
            except ICalFeed.DoesNotExist:
                messages.error(request, _('Feed not found'))
                
        elif action == 'sync':
            feed_id = request.POST.get('feed_id')
            try:
                feed = ICalFeed.objects.get(pk=feed_id, apartment=apartment)
                success, message = feed.sync()
                if success:
                    messages.success(request, _(f'Feed synced: {message}'))
                else:
                    messages.error(request, _(f'Sync failed: {message}'))
            except ICalFeed.DoesNotExist:
                messages.error(request, _('Feed not found'))
                
        elif action == 'sync_all':
            for feed in feeds.filter(is_active=True):
                feed.sync()
            messages.success(request, _('All feeds synced!'))
        
        return redirect('staff_ical_feeds', pk=pk)
    
    # Generate export URL
    export_url = request.build_absolute_uri(
        reverse('apartment_ical_export', kwargs={'pk': apartment.pk})
    )
    
    return render(request, 'staff/ical_feeds.html', {
        'apartment': apartment,
        'feeds': feeds,
        'export_url': export_url,
    })


@staff_member_required
def staff_sync_all_ical(request):
    """Staff view: sync all active iCal feeds (called by cron/management command)."""
    from .models import ICalFeed
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})
    
    feeds = ICalFeed.objects.filter(is_active=True)
    results = []
    
    for feed in feeds:
        success, message = feed.sync()
        results.append({
            'feed_id': feed.pk,
            'apartment': feed.apartment.title,
            'name': feed.name,
            'success': success,
            'message': message
        })
    
    return JsonResponse({'success': True, 'results': results})


# =============================================================================
# MESSAGING VIEWS - USER DASHBOARD
# =============================================================================

class MyConversationsListView(NonStaffRequiredMixin, LoginRequiredMixin, ListView):
    """List user's conversations."""
    model = Conversation
    template_name = 'dashboard/messages_list.html'
    context_object_name = 'conversations'

    def get_queryset(self):
        queryset = Conversation.objects.filter(user=self.request.user).order_by('-updated_at')
        # Annotate with unread count for the current user
        conversations = list(queryset)
        for conv in conversations:
            conv.unread_count = conv.get_unread_count(self.request.user)
        return conversations


@login_required
def conversation_detail(request, pk):
    """View and reply to a conversation."""
    # Prevent staff from accessing user conversations directly
    if request.user.is_staff:
        messages.error(request, _('Staff members should use the Staff Dashboard to manage conversations.'))
        return redirect('staff_conversations')
    
    conversation = get_object_or_404(Conversation, pk=pk, user=request.user)
    
    # Mark messages as read (those not sent by current user)
    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            # Update conversation timestamp
            conversation.save()
            messages.success(request, _('Message sent!'))
            return redirect('conversation_detail', pk=pk)
    else:
        form = MessageForm()
    
    return render(request, 'dashboard/conversation_detail.html', {
        'conversation': conversation,
        'messages_list': conversation.messages.all(),
        'form': form,
    })


@login_required
def start_conversation(request, booking_pk):
    """Start a new conversation for a booking."""
    booking = get_object_or_404(Booking, pk=booking_pk, user=request.user)
    
    # Check if conversation already exists
    conversation, created = Conversation.objects.get_or_create(
        booking=booking,
        user=request.user
    )
    
    return redirect('conversation_detail', pk=conversation.pk)


# =============================================================================
# MESSAGING VIEWS - STAFF DASHBOARD
# =============================================================================

class StaffConversationsListView(StaffRequiredMixin, ListView):
    """Staff view: list all conversations."""
    model = Conversation
    template_name = 'staff/messages_list.html'
    context_object_name = 'conversations'
    paginate_by = 20

    def get_queryset(self):
        queryset = Conversation.objects.all().order_by('-updated_at')
        # Annotate with unread count for staff (messages not from staff)
        conversations = list(queryset)
        for conv in conversations:
            conv.unread_count = conv.get_unread_count(self.request.user)
        return conversations


@staff_member_required
def staff_conversation_detail(request, pk):
    """Staff view: view and reply to a conversation."""
    conversation = get_object_or_404(Conversation, pk=pk)
    
    # Mark messages as read (those not sent by staff/admin)
    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            # Update conversation timestamp
            conversation.save()
            messages.success(request, _('Message sent!'))
            return redirect('staff_conversation_detail', pk=pk)
    else:
        form = MessageForm()
    
    return render(request, 'staff/conversation_detail.html', {
        'conversation': conversation,
        'messages_list': conversation.messages.all(),
        'form': form,
    })


# =============================================================================
# SETTINGS VIEWS
# =============================================================================

def set_currency(request):
    """Set user's preferred currency in session and cookie."""
    from django.conf import settings as django_settings
    
    currency = request.POST.get('currency') or request.GET.get('currency')
    next_url = request.POST.get('next') or request.GET.get('next') or request.META.get('HTTP_REFERER', '/')
    
    if currency and currency in django_settings.CURRENCIES:
        request.session['currency'] = currency
        response = redirect(next_url)
        # Set cookie for 1 year
        response.set_cookie('currency', currency, max_age=365*24*60*60)
        return response
    
    return redirect(next_url)