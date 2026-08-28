"""
apps/common/models.py
─────────────────────
Abstract base models shared across all apps.

Rules:
- Every concrete model must use UUID as its primary key.
- Every concrete model should include created_at / updated_at timestamps.
- These are abstract — they create no database tables.
"""

import uuid

from django.db import models


class UUIDModel(models.Model):
    """
    Abstract base that replaces the default integer PK with a UUID.

    Using uuid.uuid4 (random UUID, v4) — does not leak ordering information
    or creation time, which is preferable for externally-visible IDs.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier (UUID v4).",
    )

    class Meta:
        abstract = True


class TimestampedModel(UUIDModel):
    """
    Abstract base that adds auto-managed created_at and updated_at timestamps.
    Inherits UUIDModel so every timestamped model also has a UUID PK.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="UTC timestamp of record creation.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="UTC timestamp of last record update.",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]
