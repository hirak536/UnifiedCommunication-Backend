"""
apps/webhooks/serializers.py
────────────────────────────
Serializers for WebhookLog.
"""

from rest_framework import serializers
from apps.webhooks.models import WebhookLog


class WebhookLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookLog
        fields = [
            "id",
            "provider",
            "event_type",
            "object_id",
            "tenant_id",
            "tenant_code",
            "processing_status",
            "received_at",
            "expires_at",
            "payload",
        ]
