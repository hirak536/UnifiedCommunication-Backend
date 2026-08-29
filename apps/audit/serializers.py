"""
apps/audit/serializers.py
─────────────────────────
Serializers for AuditLog.
"""

from rest_framework import serializers
from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "actor_id",
            "actor_email",
            "tenant_id",
            "target_type",
            "target_id",
            "metadata",
            "created_at",
        ]
