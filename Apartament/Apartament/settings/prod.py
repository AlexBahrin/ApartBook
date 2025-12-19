"""
Production settings for Apartament project.
Use this for Render.com deployment.
"""

import os
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.onrender.com']


# Database - Render PostgreSQL
DATABASES = {
    'default': {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get('DB_NAME', 'ap_db_yuqw'),
        "USER": os.environ.get('DB_USER', 'postgress'),
        "PASSWORD": os.environ.get('DB_PASSWORD', 'dG1hWcTzn5b7XAcfuqvjRKuDQ6HHladS'),
        "HOST": os.environ.get('DB_HOST', 'dpg-d50ht03uibrs73dtb97g-a.oregon-postgres.render.com'),
        "PORT": os.environ.get('DB_PORT', '5432'),
        "OPTIONS": {
            "sslmode": "require",  # important on Render
        },
    }
}


# Email - Console backend (change to SMTP for real emails)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Uncomment and configure for real email sending:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_USE_SSL = False
# EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
# EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')


# Celery - Redis (configure if using Redis on Render)
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')


# Security settings for production
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True


# Cloudflare R2 Storage for media files
INSTALLED_APPS += ['storages']

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = 'apartbook'
AWS_S3_ENDPOINT_URL = 'https://fb7ec4029568dc5fb2edc8b735100669.r2.cloudflarestorage.com'
AWS_S3_REGION_NAME = 'auto'
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False  # Public URLs without query string authentication
AWS_S3_FILE_OVERWRITE = False
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_CUSTOM_DOMAIN = None  # Set this if you have a custom domain for R2

# Use S3-compatible storage for media files
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/'
