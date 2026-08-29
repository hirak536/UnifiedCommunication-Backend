from django.urls import path
from apps.voicemail.views import VoicemailAudioStreamView, VoicemailMessageListView

urlpatterns = [
    path("messages/", VoicemailMessageListView.as_view(), name="voicemail-messages"),
    path("messages/<str:message_id>/audio/", VoicemailAudioStreamView.as_view(), name="voicemail-audio"),
]
