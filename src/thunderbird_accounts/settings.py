"""
Django settings for thunderbird_accounts project.

Generated by 'django-admin startproject' using Django 5.1.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
IS_TEST = 'test' in sys.argv

if DEBUG:
    if IS_TEST:
        load_dotenv(dotenv_path='.env.test')
    else:
        load_dotenv(dotenv_path='.env')

APP_ENV = os.getenv('APP_ENV')

# URL for public facing absolute links
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL')

ADMIN_CLIENT_NAME = 'Accounts Admin Panel'
ADMIN_WEBSITE = os.getenv('ADMIN_WEBSITE')
ADMIN_CONTACT = os.getenv('ADMIN_CONTACT')
SUPPORT_CONTACT = os.getenv('SUPPORT_CONTACT')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

LOGIN_CODE_SECRET = os.getenv('LOGIN_CODE_SECRET')
LOGIN_MAX_AGE = 120  # 2 minutes

FXA_CLIENT_ID: str = os.getenv('FXA_CLIENT_ID')
FXA_SECRET: str = os.getenv('FXA_SECRET')
FXA_CALLBACK: str = os.getenv('FXA_CALLBACK')
FXA_OAUTH_SERVER_URL: str = os.getenv('FXA_OAUTH_SERVER_URL')
FXA_PROFILE_SERVER_URL: str = os.getenv('FXA_PROFILE_SERVER_URL')
FXA_ENCRYPT_SECRET: bytes = os.getenv('FXA_ENCRYPT_SECRET', '').encode()

ALLOWED_HOSTS = ['localhost']

# For local docker usage
if DEBUG:
    ALLOWED_HOSTS += ['accounts']

# Application definition

INSTALLED_APPS = [
    # Internal
    'thunderbird_accounts.authentication',
    'thunderbird_accounts.client',
    'thunderbird_accounts.subscription',
    'thunderbird_accounts.mail',
    'thunderbird_accounts.utils',
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
]

MIDDLEWARE = [
    # This needs to be first, as we're setting up our allowed hosts
    'thunderbird_accounts.authentication.middleware.ClientSetAllowedHostsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'thunderbird_accounts.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR.joinpath('templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'thunderbird_accounts.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
AVAILABLE_DATABASES = {
    'dev': {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DATABASE_NAME'),
            'USER': os.getenv('DATABASE_USER'),
            'PASSWORD': os.getenv('DATABASE_PASSWORD'),
            'HOST': os.getenv('DATABASE_HOST', '127.0.0.1'),
            'PORT': os.getenv('DATABASE_PORT', '5432'),
        },
    },
    'test': {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        },
    },
}

DATABASES = AVAILABLE_DATABASES['test'] if IS_TEST else AVAILABLE_DATABASES['dev']

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_simplejwt.authentication.JWTAuthentication'],
}

AVAILABLE_CACHES = {
    'dev': {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.getenv('REDIS_URL'),
        }
    },
    'test': {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    },
}

CACHES = AVAILABLE_CACHES['test'] if IS_TEST else AVAILABLE_CACHES['dev']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[{levelname}] {asctime}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}

SIMPLE_JWT = {
    'USER_ID_FIELD': 'uuid',
    'USER_ID_CLAIM': 'user_uuid',
}

AUTH_SCHEME = os.getenv('AUTH_SCHEME', 'password')

# If we're fxa use the fxa backend instead of standard user/pass
if AUTH_SCHEME == 'fxa':
    AUTHENTICATION_BACKENDS = ['thunderbird_accounts.authentication.middleware.FXABackend']

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR.joinpath('static')

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'authentication.User'

ALLOWED_HOSTS_CACHE_KEY = '__ALLOWED_HOSTS'

USE_X_FORWARDED_HOST = True
