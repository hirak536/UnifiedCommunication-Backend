"""
apps/webhooks/models.py
────────────────────────
WebhookLog — temporary storage for inbound FreeSWITCH webhook events.

Design decisions:
- Retention: 48 hours. This is NOT permanent telephony storage.
- Purpose: debugging, troubleshooting, delivery investigation,
           short-term audit, replay/recovery, failed event analysis.
- Sensitive fields (api_key, password) are REDACTED before storage
  by the webhook ingestion pipeline. Never stored in plaintext.
- expires_at has a DB index — the cleanup query
  (DELETE WHERE expires_at < now()) runs against potentially millions
  of call event rows and must be fast.

This is NOT AuditLog:
  WebhookLog = FreeSWITCH → Django  (temporary, 48h)
  AuditLog   = User/Admin → Django  (permanent)
"""

from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.common.models import UUIDModel

# Retention period for webhook logs.
WEBHOOK_LOG_RETENTION_HOURS = 48


def _default_expires_at():
    """Default expiry = now + 48 hours."""
    return timezone.now() + timedelta(hours=WEBHOOK_LOG_RETENTION_HOURS)


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

class ProcessingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    DONE = "done", "Done"
    FAILED = "failed", "Failed"


# ---------------------------------------------------------------------------
# WebhookLog
# ---------------------------------------------------------------------------

class WebhookLog(UUIDModel):
    """
    Temporary log of every inbound FreeSWITCH webhook.

    Lifecycle:
      1. Webhook received → ingestion pipeline redacts secrets → written here
         with status=pending.
      2. Celery task picks up → status=processing.
      3. Processing succeeds → status=done.
      4. Processing fails after all retries → status=failed.
         Reconciliation can repair failed events.
      5. Celery periodic task purges records where expires_at < now().

    Sensitive field redaction (applied before DB write, not after):
      api_key   → "[REDACTED]"
      password  → "[REDACTED]"
      Any other pattern matching sensitive keys → "[REDACTED]"

    The payload field stores the sanitized version. The unsanitized
    payload is never persisted.
    """

    provider = models.CharField(
        max_length=50,
        default="freeswitch",
        help_text="Source of this webhook (e.g. 'freeswitch').",
    )
    event_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text=(
            "The event type as sent by FreeSWITCH "
            "(e.g. 'extension.created', 'call.incoming')."
        ),
    )
    object_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "The FreeSWITCH object_id of the affected resource, if applicable. "
            "Used for idempotency checks and ordering logic."
        ),
    )

    # FreeSWITCH tenant context (stored as strings, not FK, because
    # the Tenant record may not exist yet when a tenant.created webhook arrives)
    tenant_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="FreeSWITCH tenant UUID string from the webhook payload.",
    )
    tenant_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="FreeSWITCH tenant_code from the webhook payload (informational).",
    )

    provider_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Timestamp of the event as reported by FreeSWITCH. "
            "Used for ordering/stale-event detection."
        ),
    )
    received_at = models.DateTimeField(
        auto_now_add=True,
        help_text="UTC timestamp when Django received this webhook.",
    )

    # Sanitized payload — sensitive fields already redacted
    payload = models.JSONField(
        help_text=(
            "The sanitized webhook payload. "
            "Sensitive fields (api_key, password, etc.) are replaced "
            "with '[REDACTED]' before this record is written. "
            "The unsanitized payload is never persisted."
        ),
    )

    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        db_index=True,
        help_text="Current processing state of this webhook event.",
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="UTC timestamp when processing completed (success or final failure).",
    )
    error = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if processing failed. Never contains secrets.",
    )

    # !! INDEXED — cleanup query hits this column !!
    expires_at = models.DateTimeField(
        default=_default_expires_at,
        db_index=True,
        help_text=(
            "UTC expiry timestamp (received_at + 48h). "
            "Celery periodic task deletes records where expires_at < now(). "
            "This index is critical for cleanup query performance."
        ),
    )

    class Meta:
        db_table = "webhook_logs"
        verbose_name = "Webhook Log"
        verbose_name_plural = "Webhook Logs"
        ordering = ["-received_at"]
        indexes = [
            # Idempotency check index: event_type + object_id + provider_timestamp
            models.Index(
                fields=["event_type", "object_id", "provider_timestamp"],
                name="idx_webhooklog_idempotency",
            ),
            # Cleanup + monitoring: find failed events that haven't expired
            models.Index(
                fields=["processing_status", "expires_at"],
                name="idx_webhooklog_status_expiry",
            ),
            # Tenant-scoped troubleshooting queries
            models.Index(
                fields=["tenant_id", "event_type", "received_at"],
                name="idx_webhooklog_tenant_event",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.event_type} / {self.object_id or 'no-object'} "
            f"[{self.processing_status}] @ {self.received_at}"
        )

    def __repr__(self) -> str:
        return (
            f"<WebhookLog id={self.id} "
            f"event_type={self.event_type!r} "
            f"status={self.processing_status!r}>"
        )

    def mark_processing(self) -> None:
        """Transition to processing state."""
        self.processing_status = ProcessingStatus.PROCESSING
        self.save(update_fields=["processing_status"])

    def mark_done(self) -> None:
        """Transition to done state."""
        self.processing_status = ProcessingStatus.DONE
        self.processed_at = timezone.now()
        self.save(update_fields=["processing_status", "processed_at"])

    def mark_failed(self, error: str) -> None:
        """Transition to failed state, recording the error."""
        self.processing_status = ProcessingStatus.FAILED
        self.processed_at = timezone.now()
        self.error = error
        self.save(update_fields=["processing_status", "processed_at", "error"])
