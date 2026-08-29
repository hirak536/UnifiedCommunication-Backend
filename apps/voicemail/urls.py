"""
apps/voicemail/urls.py
───────────────────────
URL routing for Voicemail proxy endpoints.
"""

from django.urls import path
from apps.voicemail.views import (
    VoicemailAudioStreamView,
    VoicemailMessageDetailView,
    VoicemailMessageMarkReadView,
    VoicemailMessagesView,
    VoicemailUnreadCountsView,
)

urlpatterns = [
    path("messages/", VoicemailMessagesView.as_view(), name="voicemail-messages"),
    path("messages/<str:message_uuid>/", VoicemailMessageDetailView.as_view(), name="voicemail-message-detail"),
    path("messages/<str:message_uuid>/audio/", VoicemailAudioStreamView.as_view(), name="voicemail-audio-stream"),
    path("messages/<str:message_uuid>/mark-read/", VoicemailMessageMarkReadView.as_view(), name="voicemail-mark-read"),
    path("unread-counts/", VoicemailUnreadCountsView.as_view(), name="voicemail-unread-counts"),
]
