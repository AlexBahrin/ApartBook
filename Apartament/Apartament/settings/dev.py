"""
Development settings for Apartament project.
Use this for local development.
"""

from .base import *

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
