from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Avg
from datetime import date, timedelta

from .models import Apartment, ApartmentImage, Availability, PricingRule, Booking
from .forms import (
    BookingForm, ApartmentForm, ApartmentImageForm, 
    AvailabilityForm, PricingRuleForm, BookingStatusForm
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
        context['cities'] = Apartment.objects.filter(is_active=True).values_list('city', flat=True).distinct()
        context['countries'] = Apartment.objects.filter(is_active=True).values_list('country', flat=True).distinct()
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
        
        # Get upcoming unavailable dates for calendar
        today = date.today()
        three_months_later = today + timedelta(days=90)
        
        unavailable_dates = list(
            Availability.objects.filter(
                apartment=apartment,
                date__gte=today,
                date__lte=three_months_later,
                is_available=False
            ).values_list('date', flat=True)
        )
        
        # Also get dates from confirmed bookings
        confirmed_bookings = Booking.objects.filter(
            apartment=apartment,
            status='CONFIRMED',
            check_out__gte=today
        )
        for booking in confirmed_bookings:
            current = booking.check_in
            while current < booking.check_out:
                if current not in unavailable_dates:
                    unavailable_dates.append(current)
                current += timedelta(days=1)
        
        context['unavailable_dates'] = [d.isoformat() for d in unavailable_dates]
        
        return context


@login_required
def create_booking(request, slug):
    """Handle booking form submission."""
    apartment = get_object_or_404(Apartment, slug=slug, is_active=True)
    
    if request.method == 'POST':
        form = BookingForm(request.POST, apartment=apartment)
        if form.is_valid():
            # Check availability
            if not form.check_availability():
                messages.error(request, 'The apartment is not available for the selected dates.')
                return redirect('apartment_detail', slug=slug)
            
            # Create booking
            booking = form.save(commit=False)
            booking.apartment = apartment
            booking.user = request.user
            booking.total_price = booking.calculate_total_price()
            booking.save()
            
            messages.success(request, 'Your booking request has been submitted! The owner will review it shortly.')
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
    
    # Get unavailable dates
    unavailable = Availability.objects.filter(
        apartment=apartment,
        date__gte=today,
        date__lte=end_date,
        is_available=False
    ).values_list('date', flat=True)
    
    # Get booked dates
    booked_dates = []
    confirmed_bookings = Booking.objects.filter(
        apartment=apartment,
        status='CONFIRMED',
        check_out__gte=today
    )
    for booking in confirmed_bookings:
        current = booking.check_in
        while current < booking.check_out:
            booked_dates.append(current.isoformat())
            current += timedelta(days=1)
    
    return JsonResponse({
        'unavailable': [d.isoformat() for d in unavailable],
        'booked': booked_dates,
        'base_price': str(apartment.base_price_per_night),
    })


# =============================================================================
# USER DASHBOARD VIEWS
# =============================================================================

class MyBookingsListView(LoginRequiredMixin, ListView):
    """List current user's bookings."""
    model = Booking
    template_name = 'dashboard/bookings_list.html'
    context_object_name = 'bookings'

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).order_by('-created_at')


class MyBookingDetailView(LoginRequiredMixin, DetailView):
    """Show booking details for current user."""
    model = Booking
    template_name = 'dashboard/booking_detail.html'
    context_object_name = 'booking'

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)


@login_required
def cancel_booking(request, pk):
    """Allow user to cancel their pending booking."""
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    
    if booking.status == 'PENDING':
        booking.status = 'CANCELLED_BY_USER'
        booking.save()
        messages.success(request, 'Your booking has been cancelled.')
    else:
        messages.error(request, 'Only pending bookings can be cancelled.')
    
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
        messages.success(self.request, 'Apartment created successfully!')
        return super().form_valid(form)


class StaffApartmentUpdateView(StaffRequiredMixin, UpdateView):
    """Staff view: edit apartment."""
    model = Apartment
    form_class = ApartmentForm
    template_name = 'staff/apartment_form.html'
    success_url = reverse_lazy('staff_apartments')

    def form_valid(self, form):
        messages.success(self.request, 'Apartment updated successfully!')
        return super().form_valid(form)


class StaffApartmentDeleteView(StaffRequiredMixin, DeleteView):
    """Staff view: delete apartment."""
    model = Apartment
    template_name = 'staff/apartment_confirm_delete.html'
    success_url = reverse_lazy('staff_apartments')

    def form_valid(self, form):
        messages.success(self.request, 'Apartment deleted successfully!')
        return super().form_valid(form)


@staff_member_required
def staff_apartment_images(request, pk):
    """Staff view: manage apartment images."""
    apartment = get_object_or_404(Apartment, pk=pk)
    
    if request.method == 'POST':
        form = ApartmentImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.apartment = apartment
            image.save()
            messages.success(request, 'Image uploaded successfully!')
            return redirect('staff_apartment_images', pk=pk)
    else:
        form = ApartmentImageForm()
    
    images = apartment.images.all()
    return render(request, 'staff/apartment_images.html', {
        'apartment': apartment,
        'images': images,
        'form': form,
    })


@staff_member_required
def staff_delete_image(request, pk):
    """Staff view: delete apartment image."""
    image = get_object_or_404(ApartmentImage, pk=pk)
    apartment_pk = image.apartment.pk
    image.delete()
    messages.success(request, 'Image deleted successfully!')
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
    """Staff view: booking detail with status management."""
    booking = get_object_or_404(Booking, pk=pk)
    
    if request.method == 'POST':
        form = BookingStatusForm(request.POST)
        if form.is_valid():
            new_status = form.cleaned_data['status']
            booking.status = new_status
            booking.save()
            messages.success(request, f'Booking status updated to {booking.get_status_display()}!')
            return redirect('staff_booking_detail', pk=pk)
    else:
        form = BookingStatusForm()
    
    return render(request, 'staff/booking_detail.html', {
        'booking': booking,
        'form': form,
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
            messages.success(request, 'Availability updated!')
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
def staff_pricing_rules(request, pk):
    """Staff view: manage pricing rules."""
    apartment = get_object_or_404(Apartment, pk=pk)
    
    if request.method == 'POST':
        form = PricingRuleForm(request.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.apartment = apartment
            rule.save()
            messages.success(request, 'Pricing rule added!')
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
    messages.success(request, 'Pricing rule deleted!')
    return redirect('staff_pricing_rules', pk=apartment_pk)


@staff_member_required
def staff_delete_availability(request, pk):
    """Staff view: delete availability entry."""
    availability = get_object_or_404(Availability, pk=pk)
    apartment_pk = availability.apartment.pk
    availability.delete()
    messages.success(request, 'Availability entry deleted!')
    return redirect('staff_availability', pk=apartment_pk)