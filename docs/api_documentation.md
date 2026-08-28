# Unified Communication System — Backend API Specification

**Version:** 1.0.0  
**Base URL:** `https://api.yourdomain.com/api/v1` (or `http://localhost:8000/api/v1` in local development)  
**Protocol:** HTTPS / WSS  
**Content-Type:** `application/json`

---

## Table of Contents

1. [Architectural Principles & Security](#1-architectural-principles--security)
2. [Authentication & Authorization](#2-authentication--authorization)
   - [POST /auth/login/](#post-authlogin)
   - [POST /auth/token/refresh/](#post-authtokenrefresh)
   - [GET /auth/me/](#get-authme)
3. [Tenants Management](#3-tenants-management)
   - [GET /tenants/](#get-tenants)
   - [POST /tenants/](#post-tenants)
   - [GET /tenants/{id}/](#get-tenantsid)
   - [PATCH /tenants/{id}/](#patch-tenantsid)
4. [Users Management](#4-users-management)
   - [GET /users/](#get-users)
   - [POST /users/](#post-users)
   - [GET /users/{id}/](#get-usersid)
   - [PATCH /users/{id}/](#patch-usersid)
   - [DELETE /users/{id}/](#delete-usersid)
   - [GET /users/{id}/sip-credentials/](#get-usersidsip-credentials)
5. [Telephony Resource Assignments](#5-telephony-resource-assignments)
   - [Extension Assignment](#51-extension-assignment)
   - [DID Assignment](#52-did-assignment)
   - [FaxBox Assignment](#53-faxbox-assignment)
   - [VoicemailBox Assignment](#54-voicemailbox-assignment)
6. [Communication APIs (Telephony, Fax, Voicemail)](#6-communication-apis)
   - [Calls (Origination & Termination)](#61-calls)
   - [Voicemail Messages & Audio](#62-voicemail)
   - [Fax (Send & History)](#63-fax)
   - [CDR (Call Detail Records)](#64-cdr)
7. [Inbound FreeSWITCH Webhook Ingestion](#7-inbound-freeswitch-webhook-ingestion)
   - [POST /webhooks/freeswitch/](#post-webhooksfreeswitch)
8. [Audit & Monitoring Logs](#8-audit--monitoring-logs)
   - [GET /audit-logs/](#get-audit-logs)
   - [GET /webhook-logs/](#get-webhook-logs)
9. [Realtime WebSocket Protocol](#9-realtime-websocket-protocol)

---

## 1. Architectural Principles & Security

1. **Strict Multi-Tenancy**: All client queries are scoped to the authenticated user's `tenant_id`. Cross-tenant data leaks are prevented at the queryset level.
2. **Platform Superadmin vs. Telephony Scope**: 
   - A Superadmin has platform-wide management rights (managing tenants, users, audit logs).
   - If a Superadmin has no tenant (`tenant=null`), they operate strictly as a platform administrator. If assigned a tenant, that tenant bounds their communication/telephony scope.
3. **Zero Plaintext Secrets**:
   - Application passwords are one-way hashed using Argon2/PBKDF2.
   - SIP passwords and FreeSWITCH API keys are encrypted at rest using Fernet encryption (`SecretService`).
   - Plaintext credentials are never included in webhook logs, audit logs, or WebSocket events.
4. **Normalized Identifiers**:
   - User `email` addresses are normalized to lowercase and stripped of leading/trailing whitespace before comparison and storage.

---

## 2. Authentication & Authorization

All protected endpoints require an `Authorization` header:
```http
Authorization: Bearer <access_token>
```

### POST `/auth/login/`
Authenticates a user using email and application password. Returns JWT pair and user profile.

#### Request Body
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

#### Response `200 OK`
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "18f2f458-bf87-43c3-888a-2115f5d8e785",
    "email": "user@example.com",
    "role": "admin",
    "tenant": {
      "id": "7fae0a2e-4b21-4322-81fa-223456789abc",
      "tenant_code": "TCX",
      "tenant_name": "TCX Communications"
    },
    "features": {
      "calling": true,
      "messaging": true,
      "fax": true,
      "voicemail": true
    },
    "extension": {
      "id": "b34e5a6f-1234-4567-89ab-cdef01234567",
      "extension_number": "101",
      "sip_username": "101-TCX",
      "sip_server": "sip.provider.com",
      "transport_type": "TLS"
    }
  }
}
```

### POST `/auth/token/refresh/`
Refreshes an expired access token using a valid refresh token.

#### Request Body
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Response `200 OK`
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### GET `/auth/me/`
Returns the currently authenticated user's profile and telephony configurations.

---

## 3. Tenants Management

*(Requires `platform.tenants.manage` permission — Superadmin only)*

### GET `/tenants/`
Lists all tenants in the system.

#### Query Parameters
- `is_active` (boolean, optional): Filter by active/inactive status.
- `search` (string, optional): Search by `tenant_name` or `tenant_code`.

#### Response `200 OK`
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "7fae0a2e-4b21-4322-81fa-223456789abc",
      "freeswitch_tenant_uuid": "e81d4a8e-49b0-4f51-b0e6-123456789abc",
      "tenant_code": "TCX",
      "tenant_name": "TCX Communications",
      "is_active": true,
      "features": {
        "calling": true,
        "messaging": true,
        "fax": true,
        "voicemail": true
      },
      "created_at": "2026-08-29T00:00:00Z"
    }
  ]
}
```

### POST `/tenants/`
Creates a new tenant record and configures tenant-level features.

---

## 4. Users Management

### GET `/users/`
Lists users. Regular administrators see only users within their own tenant. Superadmins can filter by `tenant_id`.

#### Query Parameters
- `tenant_id` (UUID, optional for Superadmins)
- `role` (`superadmin`, `admin`, `user`)
- `is_active` (boolean)
- `search` (searches email)

### POST `/users/`
Creates a new user.

#### Request Body
```json
{
  "email": "agent@example.com",
  "password": "TemporaryPassword123!",
  "role": "user",
  "tenant_id": "7fae0a2e-4b21-4322-81fa-223456789abc"
}
```

### GET `/users/{id}/sip-credentials/`
Secure in-memory retrieval of SIP registration credentials for the client softphone (Electron / WebRTC / SIP.js).
*(Requires caller to be the user themselves or a tenant admin).*

#### Response `200 OK`
```json
{
  "extension_number": "101",
  "sip_username": "101-TCX",
  "sip_password": "DecryptedPlaintextPasswordForRegistration",
  "sip_server": "sip.provider.com",
  "transport_type": "TLS"
}
```

---

## 5. Telephony Resource Assignments

### 5.1 Extension Assignment

#### POST `/users/{id}/extension/`
Assigns an unassigned Extension to a User.
```json
{
  "extension_id": "b34e5a6f-1234-4567-89ab-cdef01234567"
}
```

#### DELETE `/users/{id}/extension/`
Unassigns the current extension from the user, returning the extension to the unassigned pool.

---

### 5.2 DID Assignment

A DID is owned by the Tenant. Multiple users may be granted access to the same DID via `UserDID`.

#### POST `/users/{id}/dids/`
Assigns DID access to a user.
```json
{
  "did_id": "c84e5a6f-5678-4567-89ab-cdef01234567"
}
```

#### DELETE `/users/{id}/dids/{did_id}/`
Revokes user access to the DID.

---

### 5.3 FaxBox Assignment

FaxBoxes are stored in `User.fax_boxes` JSONField:
```json
[
  {
    "fax_uuid": "978c7337-d642-4cd7-a38a-d0a61c2cfbde",
    "fax_caller_id_name": "Customer Support",
    "fax_caller_id_number": "+13468310766"
  }
]
```

#### POST `/users/{id}/fax-boxes/`
Assigns a FaxBox to the user.
```json
{
  "fax_uuid": "978c7337-d642-4cd7-a38a-d0a61c2cfbde",
  "fax_caller_id_name": "Customer Support",
  "fax_caller_id_number": "+13468310766"
}
```

#### DELETE `/users/{id}/fax-boxes/{fax_uuid}/`
Removes the FaxBox assignment from the user's list.

---

### 5.4 VoicemailBox Assignment

VoicemailBoxes are stored in `User.voicemail_boxes` JSONField (e.g. `[101, 1001]`).

#### POST `/users/{id}/voicemail-boxes/`
```json
{
  "voicemail_box_id": 1001
}
```

#### DELETE `/users/{id}/voicemail-boxes/{box_id}/`
Removes the voicemail box assignment.

---

## 6. Communication APIs

### 6.1 Calls

#### POST `/calls/originate/`
Initiates an outbound call via FreeSWITCH.
```json
{
  "destination": "+18325550199",
  "caller_id_number": "+13468310766"
}
```

#### POST `/calls/hangup/`
```json
{
  "call_uuid": "3a4f6d88-1234-4567-89ab-cdef01234567"
}
```

---

### 6.2 Voicemail (Resource-to-User Event Routing)

**Core Principle:**
Voicemail messages, audio, transcripts, read states, and history remain strictly in FreeSWITCH. The backend does **not** store voicemail records or read states in the database.

The primary backend responsibility for Voicemail is **Resource-to-User Event Routing**:
```text
FreeSWITCH: voicemail.received (voicemail_id: "1001")
        ↓
Backend finds Users where voicemail_boxes contains 1001
        ↓
        ├── User A (receives WebSocket event)
        └── User B (receives WebSocket event)
(User C whose voicemail_boxes = [2001] receives nothing)
```

#### GET `/voicemail/messages/`
Proxies to FreeSWITCH to list voicemail messages for all mailbox IDs assigned to the authenticated user (`user.voicemail_boxes`).

#### GET `/voicemail/messages/{message_id}/audio/`
Streams the audio file (`audio/wav` or `audio/mp3`) directly from FreeSWITCH after verifying the requested message belongs to one of the user's assigned mailbox IDs.

### 6.3 Fax (Resource-to-User Event Routing)

**Core Principle:**
Fax history, documents, and transmission states remain strictly in FreeSWITCH. The backend does **not** store fax files or transmission logs in the database.

The backend's responsibility for FaxBox is **Resource-to-User Event Routing**:
```text
FreeSWITCH: fax.received / fax.sent (fax_uuid: "978c7337-...")
        ↓
Backend finds Users where fax_boxes contains fax_uuid
        ↓
Transmits normalized event to those specific Users via WebSockets
```

#### POST `/fax/send/`
Uploads a document and queues outbound fax transmission via FreeSWITCH.
- Content-Type: `multipart/form-data`
- Parameters:
  - `fax_uuid` (UUID of the user's assigned FaxBox)
  - `destination` (E.164 phone number)
  - `document` (PDF or TIFF file)

#### GET `/fax/history/`
Queries FreeSWITCH for inbound and outbound fax history for the caller's assigned FaxBoxes.

---

### 6.4 CDR (Call Detail Records)

#### GET `/cdr/`
Queries Call Detail Records from FreeSWITCH filtered by the caller's tenant and extension permissions.

---

## 7. Inbound FreeSWITCH Webhook Ingestion

### POST `/webhooks/freeswitch/`
Receives inbound webhook notifications from FreeSWITCH.

#### Ingestion Behavior:
1. **Secret Sanitization**: Any `api_key` or `password` fields are immediately redacted before logging.
2. **Persistence**: Payload is stored in `WebhookLog` with `status="pending"` and `expires_at = now() + 48h`.
3. **Special Handling for `api_key.created`**: Processed **synchronously in-memory** so the plaintext API key is encrypted and stored in `Tenant.encrypted_api_key` without entering background worker queues or unencrypted logs.
4. **Immediate Acknowledgment**: Returns `HTTP 202 Accepted` to FreeSWITCH.

---

## 8. Audit & Monitoring Logs

### GET `/audit-logs/`
Permanent audit trail. Regular admins only see events for their own tenant; Superadmins see all events.

#### Query Filters:
- `actor_id` (UUID)
- `action` (e.g. `user.created`, `extension.assigned`, `tenant.updated`)
- `date_from`, `date_to`

---

## 9. Realtime WebSocket Protocol

**Endpoint:** `wss://api.yourdomain.com/ws/realtime/?token=<JWT_ACCESS_TOKEN>`

### Connection Lifecycle:
1. Client connects with query param `token`.
2. Server validates JWT, resolves `user` and `tenant`.
3. User is joined to channel groups:
   - `user:{user_id}` (personal calls, faxes, assignments)
   - `tenant:{tenant_id}` (tenant-wide alerts, if authorized)

### Normalized Server Events:
```json
{
  "event": "call.incoming",
  "data": {
    "call_uuid": "3a4f6d88-1234-4567-89ab-cdef01234567",
    "caller_id_number": "+18325550199",
    "caller_id_name": "John Doe",
    "destination": "101",
    "timestamp": "2026-08-29T01:30:00Z"
  }
}
```

```json
{
  "event": "sip.credentials.updated",
  "data": {
    "requires_refresh": true
  }
}
```
*(Notice: SIP passwords are NEVER dispatched across WebSockets).*
