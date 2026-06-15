"""Django settings for the secpipeline project.

Django is used here as an ORM only - no web layer, no auth, no admin.
All database credentials live in .env; SECRET_KEY and DEBUG are also
overridable via environment so nothing sensitive is hardcoded.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load the same .env the rest of the pipeline uses, so DB credentials
# live in exactly one place and never get hardcoded here.
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY',
    'django-insecure-#*a@wt1g_epa=72u46ngbvr%cgu%1vbx0a3y5wyiat0kyp!cdt',
)

DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = []

# This project uses Django purely as an ORM for the data pipeline -
# no web frontend, auth, or admin. Only contenttypes (the bare minimum
# the ORM relies on) plus our own app are enabled, which keeps the
# database free of unused auth/session/admin tables.
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'pipeline',
]

# No middleware, templates, or URL routing - there is no web layer.
# Django is only here to manage the database schema and run queries.


# PostgreSQL is the intended target (the course server). For local
# development and the test suite there is a SQLite fallback: set
# DB_ENGINE to the sqlite3 backend in .env and the ORM plus the same
# migrations build an identical schema in a single local file - no
# server, no credentials. SQLite ignores host/user/password, so it only
# gets a file path under BASE_DIR; everything else stays the same.
#
# For cloud PostgreSQL providers (Aiven, Neon) that require TLS, set
# DB_SSLMODE=require in .env. CONN_HEALTH_CHECKS=True is recommended
# for Neon to recover from the 5-minute auto-pause reconnect.
DB_ENGINE = os.getenv('DB_ENGINE', 'django.db.backends.postgresql')

if DB_ENGINE.endswith('sqlite3'):
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': BASE_DIR / os.getenv('DB_NAME', 'local.sqlite3'),
        }
    }
else:
    _options = {}
    _sslmode = os.getenv('DB_SSLMODE', '')
    if _sslmode:
        _options['sslmode'] = _sslmode

    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': os.getenv('DB_NAME', 'group01'),
            'USER': os.getenv('DB_USER', ''),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
            'OPTIONS': _options,
            'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '0')),
            'CONN_HEALTH_CHECKS': os.getenv('DB_CONN_HEALTH_CHECKS', 'False') == 'True',
        }
    }


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
