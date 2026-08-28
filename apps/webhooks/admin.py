from django.contrib import admin
from apps.webhooks.models import WebhookLog


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ("event_type", "tenant_id", "object_id", "processing_status", "received_at", "expires_at")
    list_filter = ("processing_status", "event_type")
    search_fields = ("event_type", "object_id", "tenant_id")
    readonly_fields = [f.name for f in WebhookLog._meta.fields]
