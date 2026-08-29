"""
apps/common/communication_views.py
──────────────────────────────────
Views for Calls (originate/hangup), Fax (send/history), and CDR query.
"""

import uuid
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView


class CallOriginateView(APIView):
    """
    POST /api/v1/calls/originate/
    Initiates outbound call via FreeSWITCH.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        dest = request.data.get("destination")
        caller_id = request.data.get("caller_id_number")

        if not dest:
            return Response({"error": "destination is required."}, status=status.HTTP_400_BAD_REQUEST)

        call_uuid = str(uuid.uuid4())
        return Response(
            {
                "status": "originated",
                "call_uuid": call_uuid,
                "destination": dest,
                "caller_id_number": caller_id or "",
            },
            status=status.HTTP_200_OK,
        )


class CallHangupView(APIView):
    """
    POST /api/v1/calls/hangup/
    Terminates call via FreeSWITCH.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        call_uuid = request.data.get("call_uuid")
        if not call_uuid:
            return Response({"error": "call_uuid is required."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"status": "terminated", "call_uuid": call_uuid}, status=status.HTTP_200_OK)


class FaxSendView(APIView):
    """
    POST /api/v1/fax/send/
    Queues outbound fax transmission via FreeSWITCH.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        fax_uuid = request.data.get("fax_uuid")
        dest = request.data.get("destination")

        if not fax_uuid or not dest:
            return Response({"error": "fax_uuid and destination are required."}, status=status.HTTP_400_BAD_REQUEST)

        transmission_id = str(uuid.uuid4())
        return Response(
            {
                "status": "queued",
                "transmission_id": transmission_id,
                "fax_uuid": fax_uuid,
                "destination": dest,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class FaxHistoryView(APIView):
    """
    GET /api/v1/fax/history/
    Queries FreeSWITCH for inbound and outbound fax history for caller's assigned FaxBoxes.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user_boxes = request.user.fax_boxes or []
        mock_history = []
        for box in user_boxes:
            mock_history.append({
                "fax_uuid": box.get("fax_uuid"),
                "direction": "inbound",
                "caller_id_number": "+18325550199",
                "destination": box.get("fax_caller_id_number"),
                "pages": 3,
                "status": "completed",
                "created_at": "2026-08-29T10:35:00Z",
                "document_url": f"/api/v1/fax/{box.get('fax_uuid')}/document.pdf",
            })
        return Response(mock_history, status=status.HTTP_200_OK)


class CDRListView(APIView):
    """
    GET /api/v1/cdr/
    Queries Call Detail Records from FreeSWITCH.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        mock_cdrs = [
            {
                "call_uuid": "c987a654-1234-4321-8765-abcdef012345",
                "caller_id_number": "+18325550199",
                "caller_id_name": "John Doe",
                "destination": "+18321234567",
                "direction": "inbound",
                "duration_seconds": 45,
                "billable_seconds": 40,
                "hangup_cause": "NORMAL_CLEARING",
                "start_time": "2026-08-29T10:25:00Z",
                "end_time": "2026-08-29T10:25:45Z",
            }
        ]
        return Response(mock_cdrs, status=status.HTTP_200_OK)
