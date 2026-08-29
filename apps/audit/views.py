"""
apps/audit/views.py
───────────────────
AuditLog listing API.
"""

from rest_framework import generics, permissions
from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    """
    GET /api/v1/audit-logs/
    """
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = AuditLog.objects.all()

        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)

        actor_id = self.request.query_params.get("actor_id")
        if actor_id:
            qs = qs.filter(actor_id=actor_id)

        # Scoping: non-superadmins only see their tenant
        if not user.is_superuser and user.role != "superadmin":
            if user.tenant_id:
                qs = qs.filter(tenant_id=user.tenant_id)
            else:
                qs = qs.none()

        return qs.order_by("-created_at")
