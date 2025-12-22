"""
Development settings for Apartament project.
Use this for local development.
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env file

from .base import *
import os

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-+wpby&ge4yzx((y@7)pu_w7!9)o1)2z1tqdtw6_&rt48pmmztv'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']


# Database - Local PostgreSQL
DATABASES = {
    'default': {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "ap_db",
        "USER": "postgres",
        "PASSWORD": "admin",
        "HOST": "localhost",
        "PORT": "5432",
    }
}


# Email - Console backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# Celery - Local Redis
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'


# Cloudflare R2 Storage for media files (same as production)
INSTALLED_APPS += ['storages']

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = 'apartbook'
AWS_S3_ENDPOINT_URL = 'https://fb7ec4029568dc5fb2edc8b735100669.eu.r2.cloudflarestorage.com'
AWS_S3_REGION_NAME = 'auto'
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False  # Public URLs without query string authentication
AWS_S3_FILE_OVERWRITE = False
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_CUSTOM_DOMAIN = 'media.itchoice.store'

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
