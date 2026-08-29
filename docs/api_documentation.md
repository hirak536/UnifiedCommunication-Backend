# Unified Communication System — Backend API Specification

**Version:** 1.1.0  
**Base URL:** `https://api.yourdomain.com/api/v1` (or `http://127.0.0.1:8000/api/v1` in local development)  
**Protocol:** HTTPS / WSS  
**Content-Type:** `application/json`

---

## Table of Contents

1. [Role-Based Access Control (RBAC) & Security Architecture](#1-role-based-access-control-rbac--security-architecture)
2. [Authentication & Authorization](#2-authentication--authorization)
   - [POST /auth/login/](#post-authlogin)
   - [POST /auth/token/refresh/](#post-authtokenrefresh)
   - [GET /auth/me/](#get-authme)
3. [Tenants Management](#3-tenants-management)
   - [GET /tenants/](#get-tenants-superadmin-only)
   - [POST /tenants/](#post-tenants-superadmin-only)
   - [GET /tenants/{id}/](#get-tenantsid)
   - [PATCH /tenants/{id}/](#patch-tenantsid)
4. [Telephony Resources (Extensions & DIDs)](#4-telephony-resources-extensions--dids)
   - [GET /extensions/](#get-extensions)
   - [GET /extensions/{id}/](#get-extensionsid)
   - [GET /dids/](#get-dids)
   - [GET /dids/{id}/](#get-didsid)
5. [Users Management](#5-users-management)
   - [GET /users/](#get-users)
   - [POST /users/](#post-users)
   - [GET /users/{id}/](#get-usersid)
   - [PATCH /users/{id}/](#patch-usersid)
   - [DELETE /users/{id}/](#delete-usersid)
   - [GET /users/{id}/sip-credentials/](#get-usersidsip-credentials)
6. [Telephony Resource Assignments](#6-telephony-resource-assignments)
   - [Extension Assignment: POST/DELETE /users/{id}/extension/](#61-extension-assignment)
   - [DID Assignment: POST/DELETE /users/{id}/dids/](#62-did-assignment)
   - [FaxBox Assignment: POST/DELETE /users/{id}/fax-boxes/](#63-faxbox-assignment)
   - [VoicemailBox Assignment: POST/DELETE /users/{id}/voicemail-boxes/](#64-voicemailbox-assignment)
7. [Communication APIs (Telephony, Fax, Voicemail, CDR)](#7-communication-apis)
   - [Calls: POST /calls/originate/ & POST /calls/hangup/](#71-calls)
   - [Voicemail: GET /voicemail/messages/ & GET /voicemail/messages/{id}/audio/](#72-voicemail)
   - [Fax: POST /fax/send/ & GET /fax/history/](#73-fax)
   - [CDR: GET /cdr/](#74-cdr)
8. [Inbound FreeSWITCH Webhook Ingestion](#8-inbound-freeswitch-webhook-ingestion)
   - [POST /webhooks/freeswitch/](#post-webhooksfreeswitch)
9. [Audit & Monitoring Logs](#9-audit--monitoring-logs)
   - [GET /audit-logs/](#get-audit-logs)
   - [GET /webhook-logs/](#get-webhook-logs)
10. [Realtime WebSocket Protocol](#10-realtime-websocket-protocol)

---

## 1. Role-Based Access Control (RBAC) & Security Architecture

The platform implements a strict 3-tier Role-Based Access Control model:

| Role | Scope | Capabilities | Restrictions |
|---|---|---|---|
| **`superadmin`** | Platform-wide | Manages tenants, views all audit logs, manages resources across all tenants. | **Must provide `tenant_id`** (`?tenant_id=...` or `X-Tenant-ID` header) when listing scoped resources (`/extensions/`, `/dids/`). |
| **`admin`** | Single Tenant | Manages users, extension/DID assignments, fax boxes, voicemail boxes within own tenant. | **Blocked from `GET/POST /tenants/`** (`403 Forbidden`). Can only view/edit own tenant via `/tenants/{id}/`. |
| **`user`** | Personal | Receives calls, sends/receives faxes, listens to voicemails, registers softphone via SIP credentials. | **Blocked from all administrative endpoints** (`/extensions/`, `/dids/`, `/users/`, `/tenants/`, logs). |

### Security Invariants
- **Secret Encryption at Rest**: SIP passwords and FreeSWITCH API keys are stored encrypted via Fernet symmetric encryption (`SecretService`). Decrypted secrets exist strictly in-memory and are NEVER persisted to logs or sent via WebSockets.
- **Secret Sanitization**: Inbound webhooks automatically redact `password`, `sip_password`, `api_key`, `secret`, and `token` fields before writing to `WebhookLog`.
- **48-Hour Webhook Log TTL**: Webhook logs expire and are pruned after 48 hours via indexed `expires_at`.
- **Resource Routing Pattern**: Voicemail and Fax messages are NOT stored locally in PostgreSQL. The backend holds only resource assignments (`User.voicemail_boxes`, `User.fax_boxes`) and routes inbound FreeSWITCH events to assigned users.

---

## 2. Authentication & Authorization

All protected endpoints require an `Authorization` header:
```http
Authorization: Bearer <access_token>
```

### POST `/auth/login/`
Authenticates a user with email and application password. Returns JWT access/refresh tokens and user profile.

#### Request Body
```json
{
  "email": "root@tcx.com",
  "password": "YourSecurePassword123"
}
```

#### Response `200 OK`
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "dc151ca8-2c62-4f48-a3f0-cbb58c2e8aea",
    "email": "root@tcx.com",
    "role": "superadmin",
    "is_active": true,
    "tenant": null,
    "features": {
      "calling": false,
      "messaging": false,
      "fax": false,
      "voicemail": false
    },
    "extension": null,
    "fax_boxes": [],
    "voicemail_boxes": [],
    "created_at": "2026-08-28T20:12:27.756953Z"
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

### GET `/auth/me/`
Returns the currently authenticated user's profile and telephony configurations.

---

## 3. Tenants Management

### GET `/tenants/` *(Superadmin Only)*
Lists all tenants with live telephony resource counts. Blocked for `admin` and `user` roles (`403 Forbidden`).

#### Query Parameters
- `is_active` (boolean, optional): Filter by `true` or `false`.
- `search` (string, optional): Case-insensitive search on `tenant_code` or `tenant_name`.

#### Response `200 OK`
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "faa447b0-f40c-4bcf-b651-4131f6634f27",
      "freeswitch_tenant_uuid": "7fae0a2e-4b21-4322-81fa-223456789abc",
      "tenant_code": "TCX",
      "tenant_name": "TCX Communications",
      "features": {
        "calling": true,
        "messaging": true,
        "fax": true,
        "voicemail": true
      },
      "is_active": true,
      "extensions_count": 12,
      "dids_count": 4,
      "users_count": 8,
      "created_at": "2026-08-29T11:40:15.437672Z",
      "updated_at": "2026-08-29T11:40:15.437685Z"
    }
  ]
}
```

### POST `/tenants/` *(Superadmin Only)*
Creates a new tenant.

### GET `/tenants/{id}/` *(Superadmin & Tenant Admin)*
Retrieves tenant details. Tenant admins can only access their own tenant ID.

### PATCH `/tenants/{id}/` *(Superadmin & Tenant Admin)*
Updates tenant features or details.

---

## 4. Telephony Resources (Extensions & DIDs)

### GET `/extensions/`
Lists extensions for softphone assignment.
- **For `superadmin`**: `tenant_id` query parameter (or `X-Tenant-ID` header) is **strictly required**. Accepts Tenant UUID, FreeSWITCH UUID, or Tenant Code (e.g. `?tenant_id=TCX`).
- **For `admin`**: Automatically scoped to the administrator's tenant.

#### Query Parameters
- `tenant_id` *(required for superadmin)*: Internal UUID, FreeSWITCH UUID, or Tenant Code.
- `is_assigned` *(boolean, optional)*: `true` to filter assigned, `false` to filter unassigned pool.
- `search` *(string, optional)*: Search by extension number or SIP username.

#### Response `200 OK`
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "3163c924-e0fd-458e-8a05-912889f428f6",
      "tenant_id": "faa447b0-f40c-4bcf-b651-4131f6634f27",
      "tenant_code": "TCX",
      "tenant_name": "TCX Communications",
      "freeswitch_object_id": "fs-ext-101-uuid",
      "extension_number": "101",
      "sip_username": "101-TCX",
      "sip_server": "sip.example.com",
      "transport_type": "TLS",
      "assigned_user_id": "18f2f458-bf87-43c3-888a-2115f5d8e785",
      "assigned_user_email": "user@example.com",
      "created_at": "2026-08-29T11:44:54.671641Z",
      "updated_at": "2026-08-29T11:51:04.640230Z"
    }
  ]
}
```

### GET `/extensions/{id}/`
Retrieves single extension details.

---

### GET `/dids/`
Lists phone numbers (DIDs) with tenant scoping, capabilities, and assigned users.
- **For `superadmin`**: `tenant_id` is strictly required (`?tenant_id=TCX` or header `X-Tenant-ID: TCX`).
- **For `admin`**: Automatically scoped to own tenant.

#### Query Parameters
- `tenant_id` *(required for superadmin)*: Internal UUID, FreeSWITCH UUID, or Tenant Code.
- `calling_enabled` *(boolean, optional)*: `true` / `false`.
- `messaging_enabled` *(boolean, optional)*: `true` / `false`.
- `search` *(string, optional)*: Search by phone number (e.g. `+1832`).

#### Response `200 OK`
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "38a784eb-e08a-441f-9e01-893b15728163",
      "tenant_id": "faa447b0-f40c-4bcf-b651-4131f6634f27",
      "tenant_code": "TCX",
      "tenant_name": "TCX Communications",
      "freeswitch_object_id": "fs-did-8321234567-uuid",
      "number": "+18321234567",
      "calling_enabled": true,
      "messaging_enabled": true,
      "assigned_users_count": 1,
      "assigned_users": [
        {
          "id": "18f2f458-bf87-43c3-888a-2115f5d8e785",
          "email": "user@example.com"
        }
      ],
      "created_at": "2026-08-29T11:45:02.156591Z",
      "updated_at": "2026-08-29T11:45:02.156602Z"
    }
  ]
}
```

### GET `/dids/{id}/`
Retrieves single DID details.

---

## 5. Users Management (Unified Provisioning & Updates)

*(Restricted to `superadmin` and `admin` roles)*

The User API provides **unified, atomic endpoints**: you can create or update a user profile and simultaneously assign/unassign their **Extension**, **DIDs**, **FaxBoxes**, and **VoicemailBoxes** in a **single API call**.

---

### POST `/users/` — Unified User Creation
Creates a user and atomically provisions all telephony resources in a single transaction.

#### Request Body
```json
{
  "email": "agent1@tcx.com",
  "password": "SecurePassword123!",
  "role": "user",
  "tenant_id": "TCX",
  "extension_id": "101",
  "did_ids": ["+18321234567"],
  "fax_boxes": [
    {
      "fax_uuid": "978c7337-d642-4cd7-a38a-d0a61c2cfbde",
      "fax_caller_id_name": "Sales Fax",
      "fax_caller_id_number": "+18325550123"
    }
  ],
  "voicemail_boxes": [101, 1001]
}
```

> **Flexible Identifiers**:
> - `tenant_id`: Accepts internal UUID, FreeSWITCH UUID, or Tenant Code (e.g. `TCX`).
> - `extension_id`: Accepts Extension UUID or Extension Number (e.g. `101`).
> - `did_ids`: Accepts list of DID UUIDs or phone numbers (e.g. `["+18321234567"]`).

#### Response `201 Created`
```json
{
  "id": "378289bb-2ad2-479e-b466-2ec2ae79651f",
  "email": "agent1@tcx.com",
  "role": "user",
  "is_active": true,
  "tenant": {
    "id": "faa447b0-f40c-4bcf-b651-4131f6634f27",
    "freeswitch_tenant_uuid": "7fae0a2e-4b21-4322-81fa-223456789abc",
    "tenant_code": "TCX",
    "tenant_name": "TCX Communications"
  },
  "features": { ... },
  "extension": {
    "id": "3163c924-e0fd-458e-8a05-912889f428f6",
    "extension_number": "101",
    "sip_username": "101-TCX",
    "sip_server": "sip.example.com",
    "transport_type": "TLS"
  },
  "dids": [
    {
      "id": "38a784eb-e08a-441f-9e01-893b15728163",
      "number": "+18321234567",
      "calling_enabled": true,
      "messaging_enabled": true
    }
  ],
  "fax_boxes": [
    {
      "fax_uuid": "978c7337-d642-4cd7-a38a-d0a61c2cfbde",
      "fax_caller_id_name": "Sales Fax",
      "fax_caller_id_number": "+18325550123"
    }
  ],
  "voicemail_boxes": [101, 1001],
  "created_at": "2026-08-29T12:20:00.000000Z"
}
```

---

### PATCH `/users/{id}/` — Unified User Update
Atomically updates user attributes and/or updates/replaces resource assignments. Any field omitted remains unchanged.

#### Request Body
```json
{
  "role": "admin",
  "extension_id": null,
  "did_ids": ["+18321234567"],
  "voicemail_boxes": [101, 2002]
}
```

> **Unassigning Resources**:
> - Pass `"extension_id": null` to unassign the current extension.
> - Pass `"did_ids": []` to remove all assigned DIDs, or provide a new list to synchronize.

#### Response `200 OK`
Returns the updated user profile with all nested resources.

---

### GET `/users/`
Lists users. Superadmins can filter by `?tenant_id=...`; tenant admins are scoped to their own tenant.

### GET `/users/{id}/`
Retrieves full user profile with all nested resources (`tenant`, `extension`, `dids`, `fax_boxes`, `voicemail_boxes`).

### DELETE `/users/{id}/`
Deletes user and unlinks all assigned resources.

### GET `/users/{id}/sip-credentials/`
Decrypts in-memory and returns SIP credentials for softphone client registration.  
*Authorized for: the user themselves, their tenant administrator, or a superadmin.*

#### Response `200 OK`
```json
{
  "extension_number": "101",
  "sip_username": "101-TCX",
  "sip_password": "PlaintextSipPasswordDecryptedInMemory",
  "sip_server": "sip.example.com",
  "transport_type": "TLS"
}
```

---

## 6. Telephony Resource Assignments

### 6.1 Extension Assignment
- **Assign:** `POST /users/{id}/extension/` with `{"extension_id": "<uuid>"}`
- **Unassign:** `DELETE /users/{id}/extension/`

### 6.2 DID Assignment
- **Grant Access:** `POST /users/{id}/dids/` with `{"did_id": "<uuid>"}`
- **Revoke Access:** `DELETE /users/{id}/dids/{did_id}/`

### 6.3 FaxBox Assignment
- **Assign FaxBox:** `POST /users/{id}/fax-boxes/`
  ```json
  {
    "fax_uuid": "978c7337-d642-4cd7-a38a-d0a61c2cfbde",
    "fax_caller_id_name": "Sales Fax",
    "fax_caller_id_number": "+18325550123"
  }
  ```
- **Remove FaxBox:** `DELETE /users/{id}/fax-boxes/{fax_uuid}/`

### 6.4 VoicemailBox Assignment
- **Assign VoicemailBox:** `POST /users/{id}/voicemail-boxes/`
  ```json
  {
    "voicemail_box_id": 1001
  }
  ```
- **Remove VoicemailBox:** `DELETE /users/{id}/voicemail-boxes/{box_id}/`

---

## 7. Communication APIs

### 7.1 Calls
- **POST `/calls/originate/`**: Initiates outbound call (`{"destination": "+18325550199", "caller_id_number": "+18321234567"}`).
- **POST `/calls/hangup/`**: Terminates active call (`{"call_uuid": "<uuid>"}`).

### 7.2 Voicemail
- **GET `/voicemail/messages/`**: Lists messages for caller's assigned mailbox IDs (`User.voicemail_boxes`).
- **GET `/voicemail/messages/{message_id}/audio/`**: Streams voicemail WAV audio directly from FreeSWITCH.

### 7.3 Fax
- **POST `/fax/send/`**: Sends outbound PDF fax (`multipart/form-data`: `fax_uuid`, `destination`, `document`).
- **GET `/fax/history/`**: Lists inbound/outbound fax history for caller's assigned FaxBoxes.

### 7.4 CDR
- **GET `/cdr/`**: Queries Call Detail Records.

---

## 8. Inbound FreeSWITCH Webhook Ingestion

### POST `/webhooks/freeswitch/`
Receives FreeSWITCH notifications and synchronizes database state.

#### Supported Events & Behaviors
1. **`api_key.created`**:
   - In-memory encryption via `SecretService.encrypt()`.
   - Auto-provisions or updates `Tenant` with `encrypted_api_key`.
2. **`extension.created` & `extension.updated`**:
   - Native field mapping: accepts `phone` for `extension_number` and `password` for `sip_password`.
   - Partial update safe: preserves existing fields when only object notifications are received.
   - Encrypts SIP password in-memory.
   - Auto-provisions parent tenant if not already present.
3. **`extension.deleted`**:
   - Unlinks from assigned user (`on_delete=SET_NULL`) and deletes local extension.
4. **`did.created` & `did.updated`**:
   - Synchronizes DID number, `calling_enabled`, and `messaging_enabled`.
5. **`did.deleted`**:
   - Cleans up DID and associated `UserDID` assignments.
6. **`voicemail.received` & `fax.received`**:
   - Routes inbound communication events to users based on PostgreSQL JSONB containment (`@>`) over `User.voicemail_boxes` and `User.fax_boxes`.
7. **Secret Sanitization**:
   - All `password`, `sip_password`, and `api_key` values are replaced with `[REDACTED]` before writing to `WebhookLog`.
8. **Retention**:
   - `WebhookLog` records auto-expire after 48 hours.

---

## 9. Audit & Monitoring Logs

- **GET `/audit-logs/`**: Permanent append-only security trail. Scoped to tenant for admins; global for superadmins.
- **GET `/webhook-logs/`**: 48-hour temporary troubleshooting logs for carrier/FreeSWITCH webhooks.

---

## 10. Realtime WebSocket Protocol

**Endpoint:** `wss://api.yourdomain.com/ws/realtime/?token=<JWT_ACCESS_TOKEN>`

When connected, clients receive real-time call states, fax events, and voicemail notifications routed through Django Channels and the PostgreSQL Outbox pattern.
