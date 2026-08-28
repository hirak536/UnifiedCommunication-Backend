from django.contrib import admin
from apps.outbox.models import OutboxEvent


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "tenant",
        "target_type",
        "target_id",
        "status",
        "created_at",
        "dispatched_at",
    )
    list_filter = ("status", "target_type", "tenant")
    search_fields = ("event_type", "target_id")
    readonly_fields = ("id", "tenant", "target_type", "target_id", "event_type", "payload", "status", "created_at", "dispatched_at")
