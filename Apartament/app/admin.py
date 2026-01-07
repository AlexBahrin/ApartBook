from django.contrib import admin, messages
from django.utils.html import format_html
from .models import (
    Apartment, ApartmentImage, Availability, PricingRule, 
    Booking, Conversation, Message, ICalFeed, ICalEvent
)


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
    list_display = ['apartment', 'date', 'is_available', 'source', 'note']
    list_filter = ['is_available', 'source', 'apartment']
    date_hierarchy = 'date'
    search_fields = ['apartment__title', 'note']


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


# ============================================================
# iCal Admin with Observability and Actions
# ============================================================

@admin.action(description="🔄 Sync selected feeds now")
def sync_feeds_now(modeladmin, request, queryset):
    """Queue selected feeds for immediate sync."""
    from app.tasks import sync_single_ical_feed
    queued = 0
    for feed in queryset:
        if feed.is_active:
            sync_single_ical_feed.delay(feed.pk)
            queued += 1
    messages.success(request, f"Queued {queued} feeds for sync")


@admin.action(description="🧪 Test URL connectivity")
def test_feed_urls(modeladmin, request, queryset):
    """Test if feed URLs are reachable."""
    import requests
    for feed in queryset:
        try:
            resp = requests.head(feed.url, timeout=10, allow_redirects=True)
            if resp.status_code == 200:
                messages.success(request, f"✅ {feed.name}: OK (200)")
            elif resp.status_code == 405:
                # Some servers don't allow HEAD, try GET
                resp = requests.get(feed.url, timeout=10, stream=True)
                resp.close()
                messages.success(request, f"✅ {feed.name}: OK ({resp.status_code})")
            else:
                messages.warning(request, f"⚠️ {feed.name}: HTTP {resp.status_code}")
        except requests.Timeout:
            messages.error(request, f"❌ {feed.name}: Timeout")
        except requests.RequestException as e:
            messages.error(request, f"❌ {feed.name}: {str(e)[:50]}")


@admin.action(description="🔴 Disable feeds (open circuit)")
def disable_feeds(modeladmin, request, queryset):
    """Disable feeds and open circuit breaker."""
    from django.utils import timezone
    count = queryset.update(
        is_active=False, 
        is_circuit_open=True,
        circuit_opened_at=timezone.now()
    )
    messages.warning(request, f"Disabled {count} feeds")


@admin.action(description="🟢 Enable feeds (close circuit)")
def enable_feeds(modeladmin, request, queryset):
    """Enable feeds and reset circuit breaker."""
    count = queryset.update(
        is_active=True,
        is_circuit_open=False,
        circuit_opened_at=None,
        consecutive_failures=0
    )
    messages.success(request, f"Enabled {count} feeds")


@admin.action(description="🔄 Reset failure counters")
def reset_failure_counters(modeladmin, request, queryset):
    """Reset consecutive failures and close circuit."""
    count = queryset.update(
        consecutive_failures=0,
        is_circuit_open=False,
        circuit_opened_at=None
    )
    messages.success(request, f"Reset counters for {count} feeds")


@admin.register(ICalFeed)
class ICalFeedAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'apartment', 'is_active_display', 'circuit_status',
        'last_sync_display', 'consecutive_failures', 
        'events_summary', 'next_sync_at', 'priority'
    ]
    list_filter = ['is_active', 'is_circuit_open', 'last_sync_status', 'apartment']
    search_fields = ['name', 'apartment__title', 'url']
    ordering = ['priority', '-last_synced']
    
    actions = [sync_feeds_now, test_feed_urls, disable_feeds, enable_feeds, reset_failure_counters]
    
    readonly_fields = [
        'last_synced', 'last_sync_status', 'sync_error',
        'last_etag', 'last_modified_header', 'last_content_hash',
        'consecutive_failures', 'is_circuit_open', 'circuit_opened_at',
        'total_syncs', 'successful_syncs', 'last_sync_duration_ms',
        'last_fetch_bytes', 'last_events_parsed', 'last_events_created',
        'last_events_updated', 'last_events_removed',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Feed Configuration', {
            'fields': ('apartment', 'name', 'url', 'is_active')
        }),
        ('Scheduling', {
            'fields': ('sync_interval_minutes', 'priority', 'next_sync_at'),
            'classes': ('collapse',)
        }),
        ('Last Sync Status', {
            'fields': (
                'last_synced', 'last_sync_status', 'sync_error',
                'last_sync_duration_ms', 'last_fetch_bytes'
            )
        }),
        ('Event Statistics', {
            'fields': (
                'last_events_parsed', 'last_events_created',
                'last_events_updated', 'last_events_removed',
                'total_syncs', 'successful_syncs'
            ),
            'classes': ('collapse',)
        }),
        ('Circuit Breaker', {
            'fields': (
                'is_circuit_open', 'consecutive_failures', 'circuit_opened_at'
            ),
            'classes': ('collapse',)
        }),
        ('Conditional GET Headers', {
            'fields': ('last_etag', 'last_modified_header', 'last_content_hash'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    @admin.display(description='Active', boolean=True)
    def is_active_display(self, obj):
        return obj.is_active
    
    @admin.display(description='Circuit')
    def circuit_status(self, obj):
        if obj.is_circuit_open:
            return format_html('<span style="color: red;">🔴 OPEN</span>')
        return format_html('<span style="color: green;">🟢 Closed</span>')
    
    @admin.display(description='Last Sync')
    def last_sync_display(self, obj):
        if not obj.last_synced:
            return format_html('<span style="color: gray;">Never</span>')
        
        status_colors = {
            'SUCCESS': 'green',
            'NOT_MODIFIED': 'blue',
            'HASH_MATCH': 'blue',
            'ERROR': 'red',
        }
        color = status_colors.get(obj.last_sync_status, 'gray')
        
        duration = f" ({obj.last_sync_duration_ms}ms)" if obj.last_sync_duration_ms else ""
        return format_html(
            '<span style="color: {};">{}{}</span>',
            color, obj.last_sync_status, duration
        )
    
    @admin.display(description='Events')
    def events_summary(self, obj):
        if obj.last_events_parsed == 0 and obj.last_synced:
            return "0"
        return f"{obj.last_events_parsed} (+{obj.last_events_created}/-{obj.last_events_removed})"


@admin.register(ICalEvent)
class ICalEventAdmin(admin.ModelAdmin):
    list_display = [
        'uid_short', 'feed', 'summary_short', 'dtstart', 'dtend', 
        'status', 'is_deleted', 'missing_since'
    ]
    list_filter = ['is_deleted', 'status', 'feed', 'feed__apartment']
    search_fields = ['uid', 'summary', 'feed__name']
    date_hierarchy = 'dtstart'
    ordering = ['-dtstart']
    
    readonly_fields = [
        'uid', 'recurrence_id', 'dtstart', 'dtend', 'summary', 'status',
        'sequence', 'dtstamp', 'first_seen_at', 'last_seen_at',
        'missing_since', 'is_deleted', 'raw_vevent'
    ]
    
    @admin.display(description='UID')
    def uid_short(self, obj):
        return obj.uid[:40] + '...' if len(obj.uid) > 40 else obj.uid
    
    @admin.display(description='Summary')
    def summary_short(self, obj):
        if not obj.summary:
            return '-'
        return obj.summary[:30] + '...' if len(obj.summary) > 30 else obj.summary
