"""
apps/tenants/views.py
─────────────────────
REST API views for Tenant management.
"""

from rest_framework import generics, permissions
from apps.tenants.models import Tenant
from apps.tenants.serializers import TenantSerializer


class TenantListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/tenants/  — List all tenants
    POST /api/v1/tenants/  — Create a new tenant
    """
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Tenant.objects.all()

        # Filter by active status if requested
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() in ("true", "1"):
                qs = qs.filter(is_active=True)
            elif is_active.lower() in ("false", "0"):
                qs = qs.filter(is_active=False)

        # Search by code or name
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(tenant_name__icontains=search) | qs.filter(tenant_code__icontains=search)

        # Non-superadmins only see their own tenant
        if not user.is_superuser and user.role != "superadmin":
            if user.tenant_id:
                qs = qs.filter(id=user.tenant_id)
            else:
                qs = qs.none()

        return qs.order_by("tenant_name")


class TenantDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/tenants/{id}/ — Retrieve tenant details
    PATCH /api/v1/tenants/{id}/ — Update tenant features or details
    """
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role == "superadmin":
            return Tenant.objects.all()
        if user.tenant_id:
            return Tenant.objects.filter(id=user.tenant_id)
        return Tenant.objects.none()
