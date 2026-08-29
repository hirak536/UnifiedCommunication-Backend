"""
config/api_urls.py
Main API URL routing under /api/v1/
Wires up all REST endpoints defined in the API specification and Postman collection.
"""

from django.urls import include, path

from apps.audit.views import AuditLogListView
from apps.common.communication_views import (
    CallHangupView,
    CallOriginateView,
    CDRListView,
    FaxHistoryView,
    FaxSendView,
)
from apps.users.urls import auth_urlpatterns, user_urlpatterns
from apps.webhooks.views import WebhookLogListView

urlpatterns = [
    # 1. Authentication
    path("auth/", include(auth_urlpatterns)),

    # 2. Tenants Management
    path("tenants/", include("apps.tenants.urls")),

    # 3. Users Management & Resource Assignments
    path("users/", include(user_urlpatterns)),

    # 4. Calls
    path("calls/originate/", CallOriginateView.as_view(), name="calls-originate"),
    path("calls/hangup/", CallHangupView.as_view(), name="calls-hangup"),

    # 5. Voicemail
    path("voicemail/", include("apps.voicemail.urls")),

    # 6. Fax
    path("fax/send/", FaxSendView.as_view(), name="fax-send"),
    path("fax/history/", FaxHistoryView.as_view(), name="fax-history"),

    # 7. CDR
    path("cdr/", CDRListView.as_view(), name="cdr-list"),

    # 8. Webhooks
    path("webhooks/", include("apps.webhooks.urls")),

    # 9. Audit & Monitoring Logs
    path("audit-logs/", AuditLogListView.as_view(), name="audit-logs-list"),
    path("webhook-logs/", WebhookLogListView.as_view(), name="webhook-logs-list"),
]
