from django.contrib import admin
from .models import Apartment, ApartmentImage, Availability, PricingRule, Booking, Conversation, Message


@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'city', 'country', 'capacity', 'base_price_per_night', 'is_active', 'created_at']
    list_filter = ['is_active', 'city', 'country']
    search_fields = ['title', 'description', 'address', 'city']
    prepopulated_fields = {'slug': ('title',)}


@admin.register(ApartmentImage)
class ApartmentImageAdmin(admin.ModelAdmin):
    list_display = ['apartment', 'is_main', 'order']
    list_filter = ['is_main', 'apartment']


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ['apartment', 'date', 'is_available']
    list_filter = ['is_available', 'apartment']
    date_hierarchy = 'date'


@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    list_display = ['apartment', 'rule_type', 'start_date', 'end_date', 'price_per_night', 'priority']
    list_filter = ['rule_type', 'apartment']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'apartment', 'user', 'check_in', 'check_out', 'status', 'total_price', 'created_at']
    list_filter = ['status', 'payment_status', 'apartment']
    search_fields = ['user__username', 'user__email', 'apartment__title']
    date_hierarchy = 'created_at'


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'booking', 'created_at', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'booking__apartment__title']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['body', 'sender__username']
