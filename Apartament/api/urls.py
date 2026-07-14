from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

router = DefaultRouter()
router.register('apartments', views.PublicApartmentViewSet, basename='apartment')
router.register('my/bookings', views.MyBookingViewSet, basename='my-booking')
router.register('my/conversations', views.MyConversationViewSet, basename='my-conversation')
router.register('staff/apartments', views.StaffApartmentViewSet, basename='staff-apartment')
router.register('staff/bookings', views.StaffBookingViewSet, basename='staff-booking')
router.register('staff/conversations', views.StaffConversationViewSet, basename='staff-conversation')

urlpatterns = [
    # Auth
    path('auth/login/', views.LoginView.as_view(), name='api_login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    path('auth/register/', views.RegisterView.as_view(), name='api_register'),
    path('auth/activate/', views.activate_account, name='api_activate'),
    path('auth/password-reset/', views.password_reset_request, name='api_password_reset'),
    path('auth/password-reset/confirm/', views.password_reset_confirm, name='api_password_reset_confirm'),
    path('auth/me/', views.MeView.as_view(), name='api_me'),

    # Misc
    path('config/', views.config_view, name='api_config'),
    path('unread-counts/', views.unread_counts, name='api_unread_counts'),

    # Staff global calendar
    path('staff/calendar-events/', views.staff_global_calendar_events, name='api_staff_global_calendar'),

    # iCal export (public)
    path('apartments/<int:pk>/calendar.ics', views.apartment_ical_export, name='api_ical_export'),

    path('', include(router.urls)),
]
