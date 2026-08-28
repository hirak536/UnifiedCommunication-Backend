"""
config/asgi.py
ASGI config for UnifiedCommunication-Backend.
Used by Django Channels (WebSockets) and Daphne.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

# Basic ASGI application — Django Channels routing will be layered on top
# in Phase 4 when WebSocket consumers are implemented.
application = get_asgi_application()
