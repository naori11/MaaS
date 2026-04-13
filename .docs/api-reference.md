# MaaS API Reference

This document provides a comprehensive reference of all API endpoints across the MaaS (Math as a Service) microservices ecosystem as configured in the deployed state.

## Service Map

In the deployed state (Docker), only the **API Gateway** is exposed to the host. All other services communicate over the internal Docker network.

| Service | Container Port | Internal Docker URL | Host Port (via Gateway) |
|---------|----------------|----------------------|-------------------------|
| **API Gateway** | 8000 | `http://api-gateway:8000` | **4000** |
| **Identity** | 8000 | `http://identity:8000` | (via Gateway) |
| **Billing** | 8000 | `http://billing:8000` | (via Gateway) |
| **Math Add** | 8000 | `http://math-add:8000` | (via Gateway) |
| **Math Subtract** | 8000 | `http://math-subtract:8000` | (via Gateway) |
| **Math Multiply** | 8000 | `http://math-multiply:8000` | (via Gateway) |
| **Math Divide** | 8000 | `http://math-divide:8000` | (via Gateway) |
| **Ledger** | 8000 | `http://ledger:8000` | (via Gateway) |

---

## 1. API Gateway (Public Entry Point)

The API Gateway is the unified entry point. In production/Docker, it is reached at `http://localhost:4000`.

### Common Headers
- `X-Request-ID`: (Optional) Client-provided UUID for tracing. Returned in all responses.
- `Authorization`: `Bearer <JWT_TOKEN>` (Required for protected routes).

### Global Policies
- **Public Port**: `4000`
- **Rate Limit**: 60 requests per 60 seconds (per IP).
- **JWT Enforcement**: Required for all routes except `/api/v1/auth/register`, `/api/v1/auth/login`, and `/api/v1/billing/webhook/xendit`.

---

## 2. Identity Service

**Gateway Endpoint**: `http://localhost:4000/api/v1/auth/...`

### Register User
`POST /api/v1/auth/register`
- **Internal URL**: `http://identity:8000/api/v1/auth/register`
- **Payload**:
  ```json
  {
    "email": "user@example.com",
    "password": "minimum_8_characters"
  }
  ```
- **Response** (201 Created):
  ```json
  {
    "id": "uuid-string",
    "email": "user@example.com",
    "created_at": "ISO8601-Z-String"
  }
  ```

### Login
`POST /api/v1/auth/login`
- **Internal URL**: `http://identity:8000/api/v1/auth/login`
- **Payload**: `{"email": "...", "password": "..."}`
- **Response**: `{"access_token": "...", "token_type": "bearer", "expires_in": 3600}`

---

## 3. Billing Service

**Gateway Endpoint**: `http://localhost:4000/api/v1/billing/...`

### Subscription Status
`GET /api/v1/billing/status`
- **Internal URL**: `http://billing:8000/api/v1/billing/status`
- **Headers**: `Authorization: Bearer <token>`
- **Response**:
  ```json
  {
    "plan_name": "Free | Standard | Premium",
    "status": "active | pending_payment",
    "expires_at": "ISO8601-Z-String | null"
  }
  ```

### Subscribe/Upgrade
`POST /api/v1/billing/subscribe`
- **Internal URL**: `http://billing:8000/api/v1/billing/subscribe`
- **Headers**:
  - `Authorization: Bearer <token>`
  - `Content-Type: application/json`
- **Request Payload**:
  ```json
  {
    "plan_name": "Standard | Premium"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "components_sdk_key": "xnd_public_development_..."
  }
  ```
- **Contract Notes**:
  - Billing returns `components_sdk_key` for use with the Xendit Components embedded checkout; it no longer returns an `invoice_url`.
  - Billing writes/updates subscription as `pending_payment` until webhook confirmation.
  - If a pending intent for the same `plan_name` exists within the last 30 minutes, the existing `components_sdk_key` is reused (no new Xendit session created).
  - `plan_name` outside `Standard|Premium` is rejected.

### Xendit Webhook
`POST /api/v1/billing/webhook/xendit`
- **Internal URL**: `http://billing:8000/api/v1/billing/webhook/xendit`
- **Auth Boundary**:
  - Gateway bypasses JWT for this route.
  - Billing enforces `x-callback-token` header against `XENDIT_CALLBACK_TOKEN`.
- **Headers**:
  - `Content-Type: application/json`
  - `x-callback-token: <XENDIT_CALLBACK_TOKEN>`
- **Request Payload** (Xendit `payment_session.completed` event):
  ```json
  {
    "id": "ps_xendit_session_id",
    "event": "payment_session.completed",
    "reference_id": "upgrade_<user_id>_<uuid>",
    "status": "PAID",
    "paid_amount": 50,
    "currency": "PHP",
    "data": {
      "reference_id": "upgrade_<user_id>_<uuid>",
      "paid_amount": 50,
      "currency": "PHP"
    }
  }
  ```
  > `event`, `data`, `paid_amount`, and `currency` may appear at the root level or nested inside `data`; the handler checks both locations. `id` (payment-session id) is used for session-id validation when the stored intent has a `xendit_invoice_id`. The plan to activate is derived from the stored invoice intent — no `paid_plan_name` field is needed.
- **Response** (200 OK):
  ```json
  {
    "received": true
  }
  ```
- **Contract Notes**:
  - If `event` is present but is not `payment_session.completed`, or if `status` is not `PAID` (legacy flow), the webhook is acknowledged with `{"received": true}` and no activation occurs.
  - For completed payment sessions, billing validates the invoice intent (`reference_id`, payment-session `id` when present, paid amount, and currency) before activating the subscription.
  - Re-delivered paid events for already-processed intents are idempotently acknowledged with `{"received": true}`.
  - Validation/auth failures return gateway-normalized errors (typically 400/401).

---

## 4. Math Services

**Gateway Endpoint**: `http://localhost:4000/api/v1/calculate/...`

### Operations
All operations require a Bearer Token.

| Operation | Gateway Path | Internal URL |
|-----------|--------------|--------------|
| **Add** | `POST /api/v1/calculate/add` | `http://math-add:8000/api/v1/calculate/add` |
| **Subtract** | `POST /api/v1/calculate/subtract` | `http://math-subtract:8000/api/v1/calculate/subtract` |
| **Multiply** | `POST /api/v1/calculate/multiply` | `http://math-multiply:8000/api/v1/calculate/multiply` |
| **Divide** | `POST /api/v1/calculate/divide` | `http://math-divide:8000/api/v1/calculate/divide` |

**Request Payload**:
```json
{
  "operand_a": 10,
  "operand_b": 5
}
```

---

## 5. Ledger Service (Audit)

The Ledger is primarily an internal service but can be queried via the Gateway for audit logs.

### Get Audit Log
`GET /api/v1/ledger/transactions`
- **Internal URL**: `http://ledger:8000/api/v1/ledger/transactions`
- **Query Params**: `limit` (default 20).

---

## Error Handling

When calling through the Gateway (Port 4000), errors are normalized:

```json
{
  "error": {
    "code": "unauthorized | bad_request | rate_limited | internal_error",
    "message": "Detail message"
  },
  "request_id": "uuid"
}
```
