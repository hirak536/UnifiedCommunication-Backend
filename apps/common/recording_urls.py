"""
apps/common/recording_urls.py
─────────────────────────────
URL routing for Call Recordings proxy endpoints.
"""

from django.urls import path
from apps.common.recording_views import (
    CallRecordingAudioStreamView,
    CallRecordingDetailView,
    CallRecordingListView,
)

urlpatterns = [
    path("", CallRecordingListView.as_view(), name="recordings-list"),
    path("<str:recording_uuid>/", CallRecordingDetailView.as_view(), name="recording-detail"),
    path("<str:recording_uuid>/audio/", CallRecordingAudioStreamView.as_view(), name="recording-audio-stream"),
]
