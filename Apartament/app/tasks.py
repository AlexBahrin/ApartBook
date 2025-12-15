"""
Celery tasks for iCal synchronization and booking management.
"""
import logging
from datetime import date
from celery import shared_task

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
def sync_all_ical_feeds():
    """
    Synchronize all iCal feeds from external sources.
    This task is scheduled to run every minute.
    """
    from app.models import ICalFeed
    
    feeds = ICalFeed.objects.filter(is_active=True)
    logger.info(f"Syncing {feeds.count()} iCal feeds")
    
    for feed in feeds:
        try:
            sync_single_ical_feed.delay(feed.pk)
        except Exception as e:
            logger.error(f"Error queueing sync for feed {feed.pk}: {e}")
    
    return f"Queued {feeds.count()} feeds for sync"


@shared_task
def sync_single_ical_feed(feed_id):
    """
    Synchronize a single iCal feed from an external source.
    Uses the model's sync method.
    """
    from app.models import ICalFeed
    
    try:
        feed = ICalFeed.objects.get(pk=feed_id)
        success, message = feed.sync()
        logger.info(f"Feed {feed.pk} ({feed.name}): {message}")
        return message
    except ICalFeed.DoesNotExist:
        logger.error(f"ICalFeed {feed_id} not found")
        return f"Feed {feed_id} not found"
    except Exception as e:
        logger.error(f"Error syncing feed {feed_id}: {e}")
        return f"Error: {str(e)}"
