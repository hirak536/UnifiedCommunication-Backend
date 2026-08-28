"""
apps/voicemail/models.py
─────────────────────────
Voicemail module.

Architectural Rule:
The backend does NOT store voicemail messages, audio, transcripts, read states,
or voicemail history in the database. All of those reside solely in FreeSWITCH.

The backend's responsibility for voicemail is strictly RESOURCE-TO-USER ROUTING:
When FreeSWITCH emits a voicemail event (e.g. voicemail.received for box 1001),
the backend locates all Users whose `voicemail_boxes` JSON list contains 1001,
and routes the normalized event to those specific users via OutboxEvent / WebSockets.
"""

# No models required — FreeSWITCH is the sole source of truth.
