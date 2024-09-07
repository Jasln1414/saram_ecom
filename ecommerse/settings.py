"""
Django settings for ecommerse project.

Generated by 'django-admin startproject' using Django 5.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os
from decouple import config


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool, default=True)

ALLOWED_HOSTS = []
# settings.py

# Time zone settings




# settings.py

# Time zone settings
TIME_ZONE = 'America/New_York'  # Replace with your time zone
USE_TZ = True

# Date and time formats
DATE_FORMAT = '8-28-2024'
TIME_FORMAT = 'H:i:s'
DATETIME_FORMAT = 'Y-m-d H:i:s'

# Localization and internationalization settings
USE_L10N = True
USE_I18N = True


SITE_ID = 2



# Application definition
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"
INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'admin_app',
    'cart_app',
    "crispy_forms",
    "crispy_bootstrap4",
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    
    
    
]
SOCIALACCOUNT_PROVIDERS = {
    "google":{
        "scope": [
            "profile",
            "email"
        ],
        "AUTH_PARAMS": {"access_type": "online"}
    }
}
CRISPY_TEMPLATE_PACK = 'bootstrap4'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
   
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
   

]

ALLOWED_HOSTS = ["*"]

# CORS_ALLOWED_ORIGINS = [
#     'http://localhost:8000',  # Update with your front-end URL
#     'http://127.0.0.1:8000',  # Add more origins as needed
# ]
CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = 'ecommerse.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
         "DIRS": [
            os.path.join(BASE_DIR, "accounts", "templates"),
            os.path.join(BASE_DIR, "admin_app", "templates"),
            os.path.join(BASE_DIR, "cart_app", "templates"),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processor.default',
                
            ],
        },
    },
]

WSGI_APPLICATION = 'ecommerse.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

from decouple import config

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DATABASE_NAME', default='default_db_name'),
        'USER': config('DATABASE_USER', default='default_user'),
        'PASSWORD': config('DATABASE_PASSWORD', default='default_password'),
        'HOST': config('DATABASE_HOST', default='localhost'),
        'PORT': config('DATABASE_PORT', default='5432'),
    }
}




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


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

from decouple import config

RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET')


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/
AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    
)
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
# settings.py


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Include static directories from all apps
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "cart_app/static"),  # Replace 'app_name' with the actual app name
    os.path.join(BASE_DIR, "accounts/static"),  # Repeat for other apps
     os.path.join(BASE_DIR, "admin_app/static"),  # Repeat for other apps



]



MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field


# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
EMAIL_DEBUG = config('EMAIL_DEBUG', default=False, cast=bool)

# Default auto field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRISPY_TEMPLATE_PACK = "bootstrap4"


# settings.py
SOCIALACCOUNT_LOGIN_ON_GET = True








