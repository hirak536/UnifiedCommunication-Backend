"""
apps/webhooks/views.py
───────────────────────
Inbound webhook ingestion endpoint for FreeSWITCH (and telephony carriers).

Architectural Invariants:
1. Secret Sanitization: Raw secrets (api_key, password, sip_password) are redacted
   BEFORE persisting to WebhookLog.
2. In-Memory api_key.created Handling:
   The plaintext api_key is encrypted immediately via SecretService and saved to Tenant,
   without ever passing through Celery task args or unencrypted storage.
3. Fast Acknowledgment: Returns HTTP 202 Accepted immediately.
4. Idempotency: WebhookLog stores provider_timestamp, event_type, object_id.
"""

import copy
import logging
from datetime import datetime

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.services.secret_service import SecretService
from apps.tenants.models import Tenant
from apps.webhooks.models import ProcessingStatus, WebhookLog

logger = logging.getLogger(__name__)

# Keys that must always be sanitized before persisting
SENSITIVE_KEYS = frozenset({"api_key", "password", "sip_password", "secret", "token"})


def sanitize_payload(obj):
    """Recursively redacts sensitive keys in JSON payloads."""
    if isinstance(obj, dict):
        sanitized = {}
        for key, value in obj.items():
            if key.lower() in SENSITIVE_KEYS:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, (dict, list)):
                sanitized[key] = sanitize_payload(value)
            else:
                sanitized[key] = value
        return sanitized
    elif isinstance(obj, list):
        return [sanitize_payload(item) for item in obj]
    return obj


class FreeSwitchWebhookView(APIView):
    """
    Receives inbound FreeSWITCH webhooks.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        payload = request.data
        if not isinstance(payload, dict):
            return Response(
                {"error": "Invalid payload; expected a JSON object."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event_type = payload.get("event") or payload.get("event_type", "unknown")
        tenant_id = str(payload.get("tenant_id", "")).strip()
        tenant_code = str(payload.get("tenant_code", "")).strip()
        object_id = str(payload.get("object_id") or payload.get("call_uuid") or payload.get("fax_uuid") or payload.get("message_uuid") or "")

        # Parse provider timestamp
        raw_ts = payload.get("timestamp") or payload.get("provider_timestamp")
        provider_timestamp = None
        if raw_ts:
            try:
                provider_timestamp = parse_datetime(raw_ts)
            except Exception:
                provider_timestamp = None

        # ------------------------------------------------------------------
        # Special In-Memory Handling: api_key.created
        # Automatically creates or updates the Tenant with encrypted API key
        # ------------------------------------------------------------------
        raw_api_key = payload.get("api_key")
        if event_type == "api_key.created" and raw_api_key and tenant_id:
            try:
                encrypted_key = SecretService.encrypt(raw_api_key)
                code = tenant_code or "TENANT"
                name = payload.get("tenant_name") or f"{code} Tenant"
                tenant, created = Tenant.objects.update_or_create(
                    freeswitch_tenant_uuid=tenant_id,
                    defaults={
                        "tenant_code": code,
                        "tenant_name": name,
                        "encrypted_api_key": encrypted_key,
                        "is_active": True,
                    },
                )
                logger.info(
                    "Provisioned FreeSWITCH API key for tenant %s (created=%s)",
                    tenant_id,
                    created,
                )
            except Exception as exc:
                logger.error("Failed to encrypt/save api_key.created for tenant %s: %s", tenant_id, exc)

        # ------------------------------------------------------------------
        # Sanitize secrets before storing in WebhookLog
        # ------------------------------------------------------------------
        sanitized = sanitize_payload(payload)

        # Create temporary WebhookLog record (48h retention with indexed expires_at)
        log_entry = WebhookLog.objects.create(
            provider="freeswitch",
            event_type=event_type,
            object_id=object_id if object_id else None,
            tenant_id=tenant_id,
            tenant_code=tenant_code,
            provider_timestamp=provider_timestamp,
            payload=sanitized,
            processing_status=ProcessingStatus.PENDING,
        )

        logger.info(
            "FreeSWITCH webhook logged: id=%s event=%s tenant=%s object=%s",
            log_entry.id,
            event_type,
            tenant_id,
            object_id,
        )

        return Response(
            {
                "status": "accepted",
                "log_id": str(log_entry.id),
                "event": event_type,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class WebhookLogListView(generics.ListAPIView):
    """
    GET /api/v1/webhook-logs/
    Lists temporary 48-hour webhook records.
    """
    permission_classes = [permissions.IsAuthenticated]
    from apps.webhooks.serializers import WebhookLogSerializer
    serializer_class = WebhookLogSerializer

    def get_queryset(self):
        user = self.request.user
        qs = WebhookLog.objects.all()

        status_param = self.request.query_params.get("processing_status")
        if status_param:
            qs = qs.filter(processing_status=status_param)

        event_type = self.request.query_params.get("event_type")
        if event_type:
            qs = qs.filter(event_type=event_type)

        if not user.is_superuser and user.role != "superadmin":
            if user.tenant and user.tenant.freeswitch_tenant_uuid:
                qs = qs.filter(tenant_id=str(user.tenant.freeswitch_tenant_uuid))
            else:
                qs = qs.none()

        return qs.order_by("-received_at")
