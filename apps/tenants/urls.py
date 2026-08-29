from django.urls import path
from apps.tenants.views import TenantDetailView, TenantListCreateView

urlpatterns = [
    path("", TenantListCreateView.as_view(), name="tenant-list-create"),
    path("<uuid:id>/", TenantDetailView.as_view(), name="tenant-detail"),
]
