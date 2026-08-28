"""config/settings/development.py"""

from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS += [  # noqa: F405
    "django_extensions",
]

# Relax password validators in development
AUTH_PASSWORD_VALIDATORS = []
