"""
Django base settings for Apartament project.
Common settings shared between development and production.
"""

from pathlib import Path
from django.utils.translation import gettext_lazy as _

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',  # S3/R2 storage backend
    'app',
    'authentication',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # Must be after SessionMiddleware and before CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'app.middleware.CurrencyMiddleware',  # Custom currency middleware
]

ROOT_URLCONF = 'Apartament.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ BASE_DIR / "templates" ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',  # For i18n template tags
                'app.context_processors.currency_context',  # Custom currency context
                'app.context_processors.staff_unread_messages',  # Staff unread messages
                'app.context_processors.user_unread_messages',  # User unread messages
            ],
        },
    },
]

WSGI_APPLICATION = 'Apartament.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en'

LANGUAGES = [
    ('en', _('English')),
    ('ro', _('Romanian')),
    ('ru', _('Russian')),
    ('uk', _('Ukrainian')),
    ('de', _('German')),
    ('fr', _('French')),
    ('es', _('Spanish')),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Language cookie settings
LANGUAGE_COOKIE_NAME = 'django_language'
LANGUAGE_COOKIE_AGE = None  # Session cookie
LANGUAGE_COOKIE_DOMAIN = None
LANGUAGE_COOKIE_PATH = '/'

TIME_ZONE = 'UTC'

USE_I18N = True
USE_L10N = True
USE_TZ = True

# Currency settings
CURRENCIES = {
    'RON': {'symbol': 'lei', 'name': 'Romanian Leu', 'rate': 1.0},
}
DEFAULT_CURRENCY = 'RON'


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Only add to STATICFILES_DIRS if the directory exists
_static_dir = BASE_DIR / 'static'
STATICFILES_DIRS = [_static_dir] if _static_dir.exists() else []

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = "login"
LOGOUT_REDIRECT_URL = "login"
LOGIN_REDIRECT_URL = "landing"

DEFAULT_FROM_EMAIL = 'ApartBook <noreply@apartbook.com>'

# Celery Configuration
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Celery Beat Schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # iCal sync scheduler - runs every minute, queues only due feeds
    'schedule-ical-feeds': {
        'task': 'app.tasks.schedule_due_ical_feeds',
        'schedule': 60.0,  # every 60 seconds
    },
    # Auto-complete bookings - daily at 09:00 UTC
    'auto-complete-bookings-daily': {
        'task': 'app.tasks.auto_complete_bookings',
        'schedule': crontab(hour=9, minute=0),
    },
    # Clean up old iCal events - daily at 03:00 UTC
    'cleanup-old-ical-events': {
        'task': 'app.tasks.cleanup_old_ical_events',
        'schedule': crontab(hour=3, minute=0),
    },
    # Update feed priorities - hourly
    'update-feed-priorities': {
        'task': 'app.tasks.update_feed_priorities',
        'schedule': crontab(minute=30),  # every hour at :30
    },
}
