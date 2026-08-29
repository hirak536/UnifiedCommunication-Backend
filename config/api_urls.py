"""
config/api_urls.py
Main API URL routing under /api/v1/
"""

from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.users.urls")),
    path("webhooks/", include("apps.webhooks.urls")),
]
