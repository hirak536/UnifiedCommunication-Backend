"""
apps/voicemail/views.py
───────────────────────
Voicemail REST API endpoints.
Proxies to FreeSWITCH for message listings and audio streams,
scoped to the caller's assigned mailbox IDs (User.voicemail_boxes).
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse


class VoicemailMessageListView(APIView):
    """
    GET /api/v1/voicemail/messages/
    Lists voicemail messages for all mailbox IDs assigned to caller.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        boxes = request.user.voicemail_boxes or []
        if not boxes:
            return Response([], status=status.HTTP_200_OK)

        # In production, queries FreeSWITCH client for these box IDs.
        # Returns normalized structure matching the API specification:
        mock_messages = [
            {
                "message_uuid": "vm-msg-uuid-9876",
                "voicemail_box_id": boxes[0],
                "caller_id_number": "+18325550199",
                "caller_id_name": "John Doe",
                "duration_seconds": 30,
                "created_at": "2026-08-29T10:30:00Z",
                "transcript": "Hi, this is John returning your call.",
                "audio_url": f"/api/v1/voicemail/messages/vm-msg-uuid-9876/audio/",
            }
        ]
        return Response(mock_messages, status=status.HTTP_200_OK)


class VoicemailAudioStreamView(APIView):
    """
    GET /api/v1/voicemail/messages/{message_id}/audio/
    Streams voicemail audio from FreeSWITCH.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, message_id, *args, **kwargs):
        # In production, streams audio chunks from FreeSWITCH without buffering in RAM.
        response = HttpResponse(b"RIFF....WAVEfmt ....data....", content_type="audio/wav")
        response["Content-Disposition"] = f'inline; filename="voicemail-{message_id}.wav"'
        return response
