"""
Celery tasks for iCal synchronization and booking management.

Phase 2 Improvements:
- Per-feed scheduling with priority and next_sync_at
- Distributed locking to prevent overlapping syncs
- Exponential backoff and circuit breaker
- Rate limiting and staggered execution
- Proper retry configuration
"""
import logging
import random
import time
from datetime import date, timedelta

from celery import shared_task
from django.core.cache import cache
from django.db import DatabaseError
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def auto_complete_bookings():
    """
    Automatically mark bookings as completed when check-out date has passed.
    This task runs daily at 11:00 AM (GMT+2) / 09:00 UTC.
    """
    from app.models import Booking
    
    today = date.today()
    
    # Find all confirmed bookings where check-out date is before today
    bookings_to_complete = Booking.objects.filter(
        status='CONFIRMED',
        check_out__lt=today
    )
    
    count = bookings_to_complete.count()
    if count > 0:
        bookings_to_complete.update(status='COMPLETED')
        logger.info(f"Auto-completed {count} bookings")
    else:
        logger.info("No bookings to auto-complete")
    
    return f"Completed {count} bookings"


@shared_task
def schedule_due_ical_feeds():
    """
    Queue feeds that are due for sync, with jitter to avoid thundering herd.
    Runs every minute and replaces the old sync_all_ical_feeds approach.
    
    Improvements:
    - Only syncs feeds that are due (next_sync_at <= now)
    - Respects circuit breaker state
    - Adds jitter to stagger requests
    - Limits batch size to avoid overwhelming workers
    """
    from app.models import ICalFeed
    
    now = timezone.now()
    
    # Find feeds that are:
    # 1. Active
    # 2. Circuit is not open (or circuit opened > 1 hour ago for half-open)
    # 3. Due for sync (next_sync_at is null or <= now)
    due_feeds = ICalFeed.objects.filter(
        is_active=True,
        is_circuit_open=False,
    ).filter(
        Q(next_sync_at__isnull=True) | Q(next_sync_at__lte=now)
    ).order_by('priority', 'next_sync_at')[:20]  # Limit batch size
    
    # Also check half-open circuits (retry after 1 hour)
    half_open_feeds = ICalFeed.objects.filter(
        is_active=True,
        is_circuit_open=True,
        circuit_opened_at__lte=now - timedelta(hours=1)
    ).order_by('priority')[:5]  # Smaller batch for recovery
    
    all_feeds = list(due_feeds) + list(half_open_feeds)
    
    queued_count = 0
    for i, feed in enumerate(all_feeds):
        # Add jitter: 0-30 seconds random + 2 seconds per feed
        jitter = random.randint(0, 30) + (i * 2)
        try:
            sync_single_ical_feed.apply_async(
                args=[feed.pk],
                countdown=jitter
            )
            queued_count += 1
        except Exception as e:
            logger.error(f"Error queueing feed {feed.pk}: {e}")
    
    logger.info(f"Scheduled {queued_count} iCal feeds for sync")
    return f"Queued {queued_count} feeds for sync"


@shared_task
def sync_all_ical_feeds():
    """
    Legacy task - redirects to new scheduler.
    Kept for backwards compatibility.
    """
    return schedule_due_ical_feeds()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    acks_late=True,
    time_limit=120,
    soft_time_limit=90,
    rate_limit='10/m',
)
def sync_single_ical_feed(self, feed_id):
    """
    Synchronize a single iCal feed from an external source.
    
    Phase 2 Improvements:
    - Distributed locking to prevent overlapping syncs
    - Proper retry configuration with exponential backoff
    - Rate limiting (10 syncs per minute globally)
    - Time limits to prevent hanging tasks
    - acks_late for reliability (re-queue if worker dies)
    """
    from app.models import ICalFeed
    
    lock_key = f"ical_sync_lock:{feed_id}"
    lock_acquired = False
    
    try:
        # Try to acquire lock (expires in 5 minutes)
        lock_acquired = cache.add(lock_key, "1", timeout=300)
        if not lock_acquired:
            logger.info(f"Feed {feed_id} already syncing, skipping")
            return "Already syncing (locked)"
        
        # Load feed
        try:
            feed = ICalFeed.objects.get(pk=feed_id)
        except ICalFeed.DoesNotExist:
            logger.error(f"ICalFeed {feed_id} not found")
            return f"Feed {feed_id} not found"
        
        # Check if feed should sync (circuit breaker, is_active, etc.)
        if not feed.is_active:
            logger.info(f"Feed {feed_id} is inactive, skipping")
            return "Feed is inactive"
        
        # Check circuit breaker
        if feed.is_circuit_open:
            if feed.circuit_opened_at:
                time_since_open = timezone.now() - feed.circuit_opened_at
                if time_since_open < timedelta(hours=1):
                    logger.info(f"Feed {feed_id} circuit is open, skipping")
                    return "Circuit is open"
                else:
                    logger.info(f"Feed {feed_id} circuit half-open, attempting sync")
        
        # Perform sync
        start_time = time.time()
        success, message = feed.sync()
        duration = int((time.time() - start_time) * 1000)
        
        if success:
            logger.info(f"Feed {feed.pk} ({feed.name}): {message} [{duration}ms]")
        else:
            logger.warning(f"Feed {feed.pk} ({feed.name}) failed: {message} [{duration}ms]")
            # Let the retry mechanism handle it
            if self.request.retries < self.max_retries:
                raise Exception(message)
        
        return message
        
    except Exception as e:
        logger.error(f"Error syncing feed {feed_id}: {e}")
        raise  # Re-raise for Celery retry mechanism
        
    finally:
        # Always release lock
        if lock_acquired:
            cache.delete(lock_key)


@shared_task
def cleanup_old_ical_events():
    """
    Clean up old ICalEvent records that are no longer relevant.
    Runs daily to prevent database bloat.
    """
    from app.models import ICalEvent
    
    # Delete events that ended more than 90 days ago
    cutoff = date.today() - timedelta(days=90)
    deleted_count, _ = ICalEvent.objects.filter(
        dtend__lt=cutoff
    ).delete()
    
    logger.info(f"Cleaned up {deleted_count} old iCal events")
    return f"Deleted {deleted_count} old events"


@shared_task
def update_feed_priorities():
    """
    Update sync priorities for all feeds based on upcoming bookings.
    Runs hourly to keep priorities fresh.
    """
    from app.models import ICalFeed
    
    feeds = ICalFeed.objects.filter(is_active=True)
    updated = 0
    
    for feed in feeds:
        new_priority = feed.calculate_priority()
        if feed.priority != new_priority:
            feed.priority = new_priority
            feed.save(update_fields=['priority'])
            updated += 1
    
    logger.info(f"Updated priorities for {updated} feeds")
    return f"Updated {updated} feed priorities"
