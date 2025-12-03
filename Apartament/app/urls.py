from django.urls import path
from . import views

urlpatterns = [
    # ==========================================================================
    # PUBLIC URLS
    # ==========================================================================
    path('', views.landing_page, name='landing'),
    path('apartments/', views.ApartmentListView.as_view(), name='apartment_list'),
    path('apartments/<slug:slug>/', views.ApartmentDetailView.as_view(), name='apartment_detail'),
    path('apartments/<slug:slug>/book/', views.create_booking, name='create_booking'),
    path('api/apartments/<slug:slug>/availability/', views.apartment_availability_api, name='apartment_availability_api'),

    # ==========================================================================
    # USER DASHBOARD URLS
    # ==========================================================================
    path('dashboard/', views.MyBookingsListView.as_view(), name='dashboard'),
    path('dashboard/bookings/', views.MyBookingsListView.as_view(), name='my_bookings'),
    path('dashboard/bookings/<int:pk>/', views.MyBookingDetailView.as_view(), name='my_booking_detail'),
    path('dashboard/bookings/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),

    # ==========================================================================
    # STAFF DASHBOARD URLS
    # ==========================================================================
    # Apartments management
    path('staff/', views.StaffBookingsListView.as_view(), name='staff_dashboard'),
    path('staff/apartments/', views.StaffApartmentListView.as_view(), name='staff_apartments'),
    path('staff/apartments/create/', views.StaffApartmentCreateView.as_view(), name='staff_apartment_create'),
    path('staff/apartments/<int:pk>/edit/', views.StaffApartmentUpdateView.as_view(), name='staff_apartment_edit'),
    path('staff/apartments/<int:pk>/delete/', views.StaffApartmentDeleteView.as_view(), name='staff_apartment_delete'),
    path('staff/apartments/<int:pk>/images/', views.staff_apartment_images, name='staff_apartment_images'),
    path('staff/images/<int:pk>/delete/', views.staff_delete_image, name='staff_delete_image'),
    
    # Availability & Pricing
    path('staff/apartments/<int:pk>/availability/', views.staff_availability, name='staff_availability'),
    path('staff/availability/<int:pk>/delete/', views.staff_delete_availability, name='staff_delete_availability'),
    path('staff/apartments/<int:pk>/pricing-rules/', views.staff_pricing_rules, name='staff_pricing_rules'),
    path('staff/pricing-rules/<int:pk>/delete/', views.staff_delete_pricing_rule, name='staff_delete_pricing_rule'),
    
    # Bookings management
    path('staff/bookings/', views.StaffBookingsListView.as_view(), name='staff_bookings'),
    path('staff/bookings/<int:pk>/', views.staff_booking_detail, name='staff_booking_detail'),
]