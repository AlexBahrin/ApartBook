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
    path('api/apartments/<slug:slug>/price/', views.apartment_price_api, name='apartment_price_api'),

    # ==========================================================================
    # USER DASHBOARD URLS
    # ==========================================================================
    path('dashboard/', views.MyBookingsListView.as_view(), name='dashboard'),
    path('dashboard/bookings/', views.MyBookingsListView.as_view(), name='my_bookings'),
    path('dashboard/bookings/<int:pk>/', views.MyBookingDetailView.as_view(), name='my_booking_detail'),
    path('dashboard/bookings/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('dashboard/bookings/<int:booking_pk>/message/', views.start_conversation, name='start_conversation'),
    path('dashboard/messages/', views.MyConversationsListView.as_view(), name='my_messages'),
    path('dashboard/messages/<int:pk>/', views.conversation_detail, name='conversation_detail'),

    # ==========================================================================
    # STAFF DASHBOARD URLS
    # ==========================================================================
    # Calendar
    path('staff/calendar/', views.staff_global_calendar, name='staff_calendar'),
    path('api/staff/calendar-events/', views.staff_global_calendar_events_api, name='staff_global_calendar_events'),
    
    # Apartments management
    path('staff/', views.StaffBookingsListView.as_view(), name='staff_dashboard'),
    path('staff/apartments/', views.StaffApartmentListView.as_view(), name='staff_apartments'),
    path('staff/apartments/create/', views.StaffApartmentCreateView.as_view(), name='staff_apartment_create'),
    path('staff/apartments/<int:pk>/edit/', views.StaffApartmentUpdateView.as_view(), name='staff_apartment_edit'),
    path('staff/apartments/<int:pk>/delete/', views.StaffApartmentDeleteView.as_view(), name='staff_apartment_delete'),
    path('staff/apartments/<int:pk>/images/', views.staff_apartment_images, name='staff_apartment_images'),
    path('staff/apartments/<int:pk>/images/reorder/', views.staff_reorder_images, name='staff_reorder_images'),
    path('staff/images/<int:pk>/delete/', views.staff_delete_image, name='staff_delete_image'),
    
    # Availability & Pricing
    path('staff/apartments/<int:pk>/availability/', views.staff_availability, name='staff_availability'),
    path('staff/apartments/<int:pk>/calendar/', views.staff_calendar, name='staff_calendar'),
    path('api/staff/apartments/<int:pk>/calendar-events/', views.staff_calendar_events_api, name='staff_calendar_events'),
    path('staff/apartments/<int:pk>/block-dates/', views.staff_block_dates, name='staff_block_dates'),
    path('staff/apartments/<int:pk>/unblock-date/<int:availability_id>/', views.staff_unblock_date, name='staff_unblock_date'),
    path('staff/availability/<int:pk>/delete/', views.staff_delete_availability, name='staff_delete_availability'),
    path('staff/apartments/<int:pk>/pricing-rules/', views.staff_pricing_rules, name='staff_pricing_rules'),
    path('staff/pricing-rules/<int:pk>/delete/', views.staff_delete_pricing_rule, name='staff_delete_pricing_rule'),
    
    # iCal Import/Export
    path('staff/apartments/<int:pk>/ical/', views.staff_ical_feeds, name='staff_ical_feeds'),
    path('api/apartments/<int:pk>/calendar.ics', views.apartment_ical_export, name='apartment_ical_export'),
    path('api/staff/sync-ical/', views.staff_sync_all_ical, name='staff_sync_all_ical'),
    
    # Bookings management
    path('staff/bookings/', views.StaffBookingsListView.as_view(), name='staff_bookings'),
    path('staff/bookings/<int:pk>/', views.staff_booking_detail, name='staff_booking_detail'),
    
    # Messages management
    path('staff/messages/', views.StaffConversationsListView.as_view(), name='staff_messages'),
    path('staff/messages/<int:pk>/', views.staff_conversation_detail, name='staff_conversation_detail'),
    
    # Settings
    path('set-currency/', views.set_currency, name='set_currency'),
]