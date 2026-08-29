"""
apps/common/recording_views.py
──────────────────────────────
Call Recordings REST API endpoints proxying to FreeSWITCH / Cloud PBX Client API.

Enforces:
- Tenant feature flag check: 'calling' must be enabled.
- Streaming audio: streams recorded audio directly without buffering in RAM.
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.services.freeswitch_client import FreeSwitchClientService


def _validate_calling_feature(tenant):
    if not (tenant.features or {}).get("calling", False):
        return Response(
            {"detail": "Calling feature is disabled for this tenant."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


class CallRecordingListView(APIView):
    """
    GET /api/v1/recordings/
    Lists call recordings.
    Params: search, number, start, end, page, page_size.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        tenant = FreeSwitchClientService.get_target_tenant(request)
        feat_err = _validate_calling_feature(tenant)
        if feat_err:
            return feat_err

        return FreeSwitchClientService.proxy_request(
            tenant=tenant,
            method="GET",
            endpoint_path="call-recordings/",
            params=dict(request.query_params),
        )


class CallRecordingDetailView(APIView):
    """
    GET    /api/v1/recordings/{recording_uuid}/ — Metadata
    DELETE /api/v1/recordings/{recording_uuid}/ — Delete recording and audio file
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, recording_uuid, *args, **kwargs):
        tenant = FreeSwitchClientService.get_target_tenant(request)
        feat_err = _validate_calling_feature(tenant)
        if feat_err:
            return feat_err

        return FreeSwitchClientService.proxy_request(
            tenant=tenant,
            method="GET",
            endpoint_path=f"call-recordings/{recording_uuid}/",
        )

    def delete(self, request, recording_uuid, *args, **kwargs):
        tenant = FreeSwitchClientService.get_target_tenant(request)
        feat_err = _validate_calling_feature(tenant)
        if feat_err:
            return feat_err

        return FreeSwitchClientService.proxy_request(
            tenant=tenant,
            method="DELETE",
            endpoint_path=f"call-recordings/{recording_uuid}/",
        )


class CallRecordingAudioStreamView(APIView):
    """
    GET /api/v1/recordings/{recording_uuid}/audio/
    Streams audio recording chunk-by-chunk from FreeSWITCH.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, recording_uuid, *args, **kwargs):
        tenant = FreeSwitchClientService.get_target_tenant(request)
        feat_err = _validate_calling_feature(tenant)
        if feat_err:
            return feat_err

        return FreeSwitchClientService.proxy_stream(
            tenant=tenant,
            endpoint_path=f"call-recordings/{recording_uuid}/audio/",
            default_content_type="audio/wav",
        )
