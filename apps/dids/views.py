"""
apps/dids/views.py
──────────────────
REST API views for DID listing and details.
"""

from rest_framework import generics, permissions
from apps.dids.models import DID
from apps.dids.serializers import DIDSerializer


class DIDListView(generics.ListAPIView):
    """
    GET /api/v1/dids/
    Lists DIDs with tenant filtering, capability filtering, and search.
    """
    serializer_class = DIDSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = DID.objects.select_related("tenant").prefetch_related("user_dids__user").all()

        # Tenant filtering
        tenant_id = self.request.query_params.get("tenant_id")
        if user.is_superuser or user.role == "superadmin":
            if tenant_id:
                qs = qs.filter(tenant_id=tenant_id)
        else:
            if user.tenant_id:
                qs = qs.filter(tenant_id=user.tenant_id)
            else:
                qs = qs.none()

        # Capabilities filtering
        calling = self.request.query_params.get("calling_enabled")
        if calling is not None:
            if calling.lower() in ("true", "1"):
                qs = qs.filter(calling_enabled=True)
            elif calling.lower() in ("false", "0"):
                qs = qs.filter(calling_enabled=False)

        messaging = self.request.query_params.get("messaging_enabled")
        if messaging is not None:
            if messaging.lower() in ("true", "1"):
                qs = qs.filter(messaging_enabled=True)
            elif messaging.lower() in ("false", "0"):
                qs = qs.filter(messaging_enabled=False)

        # Search query (by phone number)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(number__icontains=search)

        return qs.order_by("number")


class DIDDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/dids/{id}/
    Retrieves single DID details.
    """
    serializer_class = DIDSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        qs = DID.objects.select_related("tenant").prefetch_related("user_dids__user").all()
        if user.is_superuser or user.role == "superadmin":
            return qs
        if user.tenant_id:
            return qs.filter(tenant_id=user.tenant_id)
        return qs.none()
