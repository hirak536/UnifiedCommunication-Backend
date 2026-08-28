"""
apps/audit/models.py
─────────────────────
AuditLog — permanent record of user/admin/system actions.

Design decisions:
- AuditLog is COMPLETELY SEPARATE from WebhookLog.
  WebhookLog = FreeSWITCH → Django  (temporary, 48h)
  AuditLog   = User/Admin/System → Django  (permanent)
- Retention: permanent (no automatic deletion).
- Created from Phase 1, from day one — every user/resource mutation
  must produce an AuditLog entry.
- tenant is nullable to support platform-level cross-tenant actions
  (e.g., a Superadmin creating a user for another tenant).
- actor is nullable to support system-initiated actions (e.g., reconciliation).
- metadata is sanitized — it must NEVER contain secrets
  (passwords, SIP credentials, API keys).
- Superadmin log access: platform.logs.view permission allows viewing
  logs across all tenants. Normal admin with logs.view sees own tenant only.
"""

from django.db import models

from apps.common.models import UUIDModel


# ---------------------------------------------------------------------------
# Action constants
# ---------------------------------------------------------------------------
# These are the canonical action names used in AuditLog.action.
# Use these constants rather than raw strings throughout the codebase.

class AuditAction:
    # User lifecycle
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_ACTIVATED = "user.activated"
    USER_DEACTIVATED = "user.deactivated"

    # Role / permission changes
    ROLE_CHANGED = "role.changed"
    PERMISSION_CHANGED = "permission.changed"

    # Extension assignment
    EXTENSION_ASSIGNED = "extension.assigned"
    EXTENSION_UNASSIGNED = "extension.unassigned"

    # DID assignment
    DID_ASSIGNED = "did.assigned"
    DID_UNASSIGNED = "did.unassigned"

    # FaxBox assignment
    FAXBOX_ASSIGNED = "faxbox.assigned"
    FAXBOX_UNASSIGNED = "faxbox.unassigned"

    # VoicemailBox assignment
    VOICEMAIL_BOX_ASSIGNED = "voicemail_box.assigned"
    VOICEMAIL_BOX_UNASSIGNED = "voicemail_box.unassigned"

    # Tenant administration
    TENANT_CREATED = "tenant.created"
    TENANT_UPDATED = "tenant.updated"
    TENANT_FEATURES_CHANGED = "tenant.features_changed"
    TENANT_API_KEY_ROTATED = "tenant.api_key_rotated"

    # Platform administration
    PLATFORM_USER_CREATED = "platform.user.created"
    PLATFORM_USER_UPDATED = "platform.user.updated"
    PLATFORM_USER_DELETED = "platform.user.deleted"


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

class AuditLog(UUIDModel):
    """
    Permanent, append-only record of application-level actions.

    Every resource mutation triggered by a User, Admin, or Superadmin
    must produce an AuditLog entry. System-initiated changes (reconciliation,
    webhook processing) may also produce entries.

    Security:
    - metadata must be pre-sanitized by the caller (AuditService.log()).
    - metadata must NEVER contain: passwords, SIP credentials, API keys,
      or any other secrets.
    - ip_address is recorded for human-initiated actions when available.
    """

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text=(
            "The tenant context for this action. "
            "Null for platform-level cross-tenant actions "
            "(e.g., Superadmin creating a user for a different tenant)."
        ),
    )
    actor = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text=(
            "The User who performed this action. "
            "Null for system-initiated actions (reconciliation, webhooks)."
        ),
    )
    action = models.CharField(
        max_length=100,
        db_index=True,
        help_text=(
            "Action identifier (e.g. 'user.created', 'did.assigned'). "
            "Use AuditAction constants — do not use raw strings."
        ),
    )
    target_type = models.CharField(
        max_length=100,
        help_text=(
            "Type of the resource this action was performed on "
            "(e.g. 'User', 'Extension', 'DID', 'Tenant')."
        ),
    )
    target_id = models.CharField(
        max_length=255,
        help_text="UUID or identifier of the affected resource.",
    )
    metadata = models.JSONField(
        default=dict,
        help_text=(
            "Sanitized contextual details about the action. "
            "SECURITY: Must never contain passwords, SIP credentials, "
            "API keys, or any other secrets. "
            "Example: {\"old_role\": \"user\", \"new_role\": \"admin\"}"
        ),
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the actor if the action was HTTP-initiated.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="UTC timestamp of this audit entry. Append-only.",
    )

    class Meta:
        db_table = "audit_logs"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]
        # Note: No updated_at — AuditLog is append-only. Never update existing records.
        indexes = [
            # Tenant-scoped log viewing (admin: logs.view → own tenant)
            models.Index(
                fields=["tenant", "created_at"],
                name="idx_auditlog_tenant_time",
            ),
            # Actor-scoped queries (e.g., "what did user X do?")
            models.Index(
                fields=["actor", "created_at"],
                name="idx_auditlog_actor_time",
            ),
            # Resource-scoped queries (e.g., "what happened to extension Y?")
            models.Index(
                fields=["target_type", "target_id"],
                name="idx_auditlog_target",
            ),
            # Action-type queries (e.g., "all user.deleted events")
            models.Index(
                fields=["action", "created_at"],
                name="idx_auditlog_action_time",
            ),
        ]

    def __str__(self) -> str:
        actor_str = self.actor.email if self.actor_id else "system"
        return f"{self.action} on {self.target_type}/{self.target_id} by {actor_str}"

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} "
            f"action={self.action!r} "
            f"target={self.target_type}/{self.target_id}>"
        )
