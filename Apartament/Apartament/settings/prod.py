"""
Production settings for Apartament project.
Use this for Render.com deployment.
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env file

import os
from .base import *


def _env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


# SECURITY WARNING: keep the secret key used in production secret!
# Must be provided via environment in production. No insecure fallback.
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('SECRET_KEY environment variable is required in production.')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = _env_bool('DEBUG', False)

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.onrender.com', 'iasicazare.com', 'www.iasicazare.com']


# Database - Render PostgreSQL
DATABASES = {
    'default': {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get('DB_NAME'),
        "USER": os.environ.get('DB_USER'),
        "PASSWORD": os.environ.get('DB_PASSWORD'),
        "HOST": os.environ.get('DB_HOST'),
        "PORT": os.environ.get('DB_PORT'),
        "OPTIONS": {
            "sslmode": "require",  # important on Render
        },
    }
}


# Email - Gmail SMTP
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = os.environ.get('EMAIL_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASS')
DEFAULT_FROM_EMAIL = os.environ.get('EMAIL_USER', 'noreply@iasicazare.com')


# Celery - Redis (configure if using Redis on Render)
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')


# Security settings for production
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HTTP Strict Transport Security
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Additional hardening headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'

# CSRF trusted origins for cross-site POSTs from the deployed domains
CSRF_TRUSTED_ORIGINS = [
    'https://iasicazare.com',
    'https://www.iasicazare.com',
    'https://*.onrender.com',
]


# Cloudflare R2 Storage for media files

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = 'iasicazare'
AWS_S3_ENDPOINT_URL = 'https://320927796294bb05a5ebbc8b51bd8d6f.eu.r2.cloudflarestorage.com'
AWS_S3_REGION_NAME = 'auto'
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False  # Public URLs without query string authentication
AWS_S3_FILE_OVERWRITE = False
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_CUSTOM_DOMAIN = 'media.iasicazare.com'

# Use S3-compatible storage for media files (Django 5.x format)
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'


# Cron secret key for external cron services (cron-job.org)
CRON_SECRET_KEY = os.environ.get('CRON_SECRET_KEY')

# iCal domain for stable UIDs in exported calendars
ICAL_DOMAIN = 'iasicazare.com'
