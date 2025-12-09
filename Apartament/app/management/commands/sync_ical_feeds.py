"""
Management command to sync all iCal feeds.
Can be run from cron: */1 * * * * cd /path/to/project && python manage.py sync_ical_feeds
"""
from django.core.management.base import BaseCommand
from app.models import ICalFeed


class Command(BaseCommand):
    help = 'Synchronize all active iCal feeds from external sources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apartment',
            type=int,
            help='Sync feeds for a specific apartment ID only',
        )
        parser.add_argument(
            '--feed',
            type=int,
            help='Sync a specific feed ID only',
        )

    def handle(self, *args, **options):
        apartment_id = options.get('apartment')
        feed_id = options.get('feed')

        if feed_id:
            # Sync a specific feed
            try:
                feed = ICalFeed.objects.get(pk=feed_id)
                self.sync_feed(feed)
            except ICalFeed.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'Feed {feed_id} not found'))
                return
        elif apartment_id:
            # Sync all feeds for a specific apartment
            feeds = ICalFeed.objects.filter(apartment_id=apartment_id, is_active=True)
            self.stdout.write(f'Syncing {feeds.count()} feeds for apartment {apartment_id}')
            for feed in feeds:
                self.sync_feed(feed)
        else:
            # Sync all active feeds
            feeds = ICalFeed.objects.filter(is_active=True)
            self.stdout.write(f'Syncing {feeds.count()} active feeds')
            for feed in feeds:
                self.sync_feed(feed)

        self.stdout.write(self.style.SUCCESS('Sync complete!'))

    def sync_feed(self, feed):
        """Sync a single feed and print results."""
        self.stdout.write(f'  Syncing: {feed.name} ({feed.apartment.title})...')
        success, message = feed.sync()
        if success:
            self.stdout.write(self.style.SUCCESS(f'    ✓ {message}'))
        else:
            self.stdout.write(self.style.ERROR(f'    ✗ {message}'))
