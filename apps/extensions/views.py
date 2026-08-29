"""
apps/extensions/views.py
────────────────────────
REST API views for Extension listing and details.
"""

from rest_framework import generics
from apps.common.permissions import IsAdminOrSuperAdmin
from apps.common.tenant_resolver import get_scoped_tenant
from apps.extensions.models import Extension
from apps.extensions.serializers import ExtensionSerializer


class ExtensionListView(generics.ListAPIView):
    """
    GET /api/v1/extensions/
    Lists extensions scoped to a specific tenant.
    For superadmin: 'tenant_id' query parameter or 'X-Tenant-ID' header is required.
    For admin: automatically scoped to the user's tenant.
    """
    serializer_class = ExtensionSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        tenant = get_scoped_tenant(self.request)
        qs = Extension.objects.filter(tenant=tenant).select_related("tenant", "user")

        # Assignment filtering: is_assigned=true / false
        is_assigned = self.request.query_params.get("is_assigned")
        if is_assigned is not None:
            if is_assigned.lower() in ("true", "1"):
                qs = qs.filter(user__isnull=False)
            elif is_assigned.lower() in ("false", "0"):
                qs = qs.filter(user__isnull=True)

        # Search query
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(extension_number__icontains=search) | qs.filter(sip_username__icontains=search)

        return qs.order_by("extension_number")


class ExtensionDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/extensions/{id}/
    Retrieves single extension details.
    Restricted to superadmin and admin roles.
    """
    serializer_class = ExtensionSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        qs = Extension.objects.select_related("tenant", "user").all()
        if user.is_superuser or user.role == "superadmin":
            return qs
        if user.tenant_id:
            return qs.filter(tenant_id=user.tenant_id)
        return qs.none()
