# API Testing Guide

All routes in this guide are relative to `/api/v1/` and use trailing slashes.
For example, `POST /auth/login/` means `POST http://127.0.0.1:8000/api/v1/auth/login/`.
Use JSON (`Content-Type: application/json`) except for verification document uploads,
which use `multipart/form-data`.

## 1. Run the automated tests

From the backend directory in PowerShell:

```powershell
.\getto_env\Scripts\python.exe manage.py test --settings=config.test_settings
```

The test settings use an in-memory SQLite database. The suite is a quick baseline,
not a substitute for the route-by-route manual checks below.

## 2. Start a local API

Use the project's configured development database and environment:

```powershell
.\getto_env\Scripts\python.exe manage.py migrate
.\getto_env\Scripts\python.exe manage.py runserver
```

Create test accounts and reference records (regions, streets, universities,
campuses, roles, and permissions) through the project's normal setup/admin process.
Keep this data isolated from production. Have at least one customer, owner, and
staff account available; for staff permission tests, create separate staff roles
with and without the relevant permissions.

In Postman, define:

- `baseUrl`: `http://127.0.0.1:8000/api/v1`
- `customerToken`, `ownerToken`, and `staffToken`: each account's `access` token
- Any IDs returned by create requests, such as `propertyId`, `roomId`,
  `bookingId`, `verificationId`, and `documentId`

For protected routes, set the `Authorization` header to the `Bearer` scheme and
the access token. Obtain tokens from login or registration responses. Access
tokens expire; log in or refresh to obtain a current one. Never save real
credentials or refresh tokens in a shared collection or commit them to source
control.

## 3. Route-by-route checklist

For every route, test the listed method with valid data, then test an invalid or
missing ID and the access-denied behavior where applicable. A missing/invalid
credential on protected routes should be rejected; using a different account
type or accessing another user's resource should not disclose that resource.

### Authentication and accounts

| Method | Route | Access | Basic check |
|---|---|---|---|
| POST | `/auth/login/` | Public | Valid credentials return `access`, `refresh`, `token_type`, account type, and account ID. Bad credentials are rejected. |
| POST | `/auth/refresh/` | Public | Send `{"refresh_token":"..."}`; verify token rotation, then verify replaying the old token is rejected. |
| POST | `/auth/logout/` | Authenticated | Send the active session's refresh token and bearer access token; expect `204`, then verify the revoked access token no longer works. |
| POST | `/auth/register/customer/` | Public | Create a customer with required fields below; expect `201` and a token pair. Also try a duplicate email/phone. |
| POST | `/auth/register/owner/` | Public | Create an owner with required fields below; expect `201` and a token pair. Also try duplicate contact details. |
| POST | `/auth/password-reset/` | Public | Send account type and email; expect the same `202` response whether the account exists or not. |
| POST | `/auth/password-reset/confirm/` | Public | Use a valid one-time token and `new_password`; expect `204`, then verify the old password/session is invalid and the new password works. |

Customer registration JSON (use existing university/campus IDs):

```json
{
  "firstname": "Test",
  "lastname": "Customer",
  "phone": "+255711000001",
  "email": "customer.test@example.test",
  "password": "Unique-test-password-839!",
  "university": 1,
  "campus": 1,
  "admission_info": "Test admission"
}
```

Owner registration requires `firstname`, `lastname`, `phone`, `email`, and
`password`. Login requires `account_type` (`customer`, `owner`, or `staff`),
`email`, and `password`.

### Customer routes

| Method | Route | Access | Basic check |
|---|---|---|---|
| GET, PUT, PATCH | `/customers/me/` | Customer | Read the signed-in customer's profile; update allowed fields and verify password/status fields are not writable. |
| GET, PUT, PATCH | `/customers/me/preferences/` | Customer | Read, fully set, and partially update preferences. Try an invalid location ID and min/max price validation. |
| GET, POST | `/customers/me/favourites/` | Customer | List favourites; add a property using `{"property_id": <id>}` and confirm it appears. |
| DELETE | `/customers/me/favourites/{property_id}/` | Customer | Remove an existing favourite; check a missing/non-owned favourite is not reported as successfully removed. |
| GET | `/reviews/` | Public | List reviews; test optional `?property_id=<id>`. |
| POST | `/reviews/` | Customer | Submit `property_id`, `rating` (1–5), and optional `comment`; try out-of-range rating. |
| PATCH, DELETE | `/reviews/{review_id}/` | Review's customer | Update or delete your review; try another customer's review ID. A confirmed booking is required, and each customer can review a property once. |
| POST | `/reports/` | Customer | Submit `property_id`, `reason`, and optional `description`; expect `201`. |

Example preference body:

```json
{
  "region": 1,
  "district": 1,
  "ward": 1,
  "preferred_room_type": "single",
  "min_price": "100000.00",
  "max_price": "500000.00"
}
```

### Owner, property, and verification routes

| Method | Route | Access | Basic check |
|---|---|---|---|
| GET, POST | `/owners/me/properties/` | Owner | List only this owner's properties; create a property using the body below. |
| GET | `/owners/me/` | Owner | Read your profile. |
| PATCH | `/owners/me/` | Owner | Update your own profile fields. |
| GET | `/owners/me/dashboard/` | Owner | Read aggregate property, room, booking, revenue, and review statistics. |
| GET | `/owners/me/bookings/` | Owner | List bookings for your properties; optionally filter by `?status=pending`. |
| POST | `/owners/me/bookings/{booking_id}/confirm/` | Booking's owner | Confirm a pending booking on your property; try another owner's booking. |
| POST | `/owners/me/bookings/{booking_id}/reject/` | Booking's owner | Reject a pending booking on your property. |
| PATCH | `/owners/me/properties/{property_id}/` | Owner | Update an owned property; verify another owner's property cannot be changed. |
| GET, POST | `/owners/me/properties/{property_id}/media/` | Owner | List or upload media for owned property using `multipart/form-data` with `file` (optional `type`). |
| DELETE | `/owners/me/properties/{property_id}/media/{media_id}/` | Owner | Delete property media; verify other owners cannot delete it. |
| POST | `/owners/me/properties/{property_id}/rooms/` | Owner | Add a room to an owned property using the body below. |
| GET, POST | `/owners/me/rooms/{room_id}/media/` | Owner | List or upload media for owned room using `multipart/form-data` with `file` (optional `type`). |
| DELETE | `/owners/me/rooms/{room_id}/media/{media_id}/` | Owner | Delete room media; verify other owners cannot delete it. |
| GET, POST | `/properties/media/` | Public (GET) / Owner, Staff (POST) | List verified media; upload media with `property_id` and `file`. |
| DELETE | `/properties/media/{media_id}/` | Owner or Staff | Delete property media. |
| GET, POST | `/rooms/media/` | Public (GET) / Owner, Staff (POST) | List available room media; upload media with `room_id` and `file`. |
| DELETE | `/rooms/media/{media_id}/` | Owner or Staff | Delete room media. |
| GET | `/owners/me/verifications/` | Owner | List only this owner's verification submissions. |
| POST | `/owners/me/properties/{property_id}/verifications/` | Owner | Upload one valid PDF/JPEG/PNG with `file` (and optional `description`) as multipart form data. Try unsupported, mismatched, and oversized files. |
| GET, POST | `/owners/me/verifications/{verification_id}/documents/` | Owner | List documents; add a file to a pending verification. Try a verification belonging to another owner and a non-pending verification. |
| GET | `/verifications/documents/{document_id}/download/` | Owner or staff | Download as the document owner and as staff; verify another owner/customer cannot access it. |
| POST | `/staff/verifications/{verification_id}/approve/` | Staff with review permission | Approve a pending verification; try missing ID and staff lacking the permission. |
| POST | `/staff/verifications/{verification_id}/reject/` | Staff with review permission | Reject a pending verification, optionally sending `{"remarks":"..."}`; verify invalid state transitions are rejected. |
| GET | `/staff/reports/` | Staff with `property.report.review` | List reports; optionally filter by `?status=open`. |
| PATCH | `/staff/reports/{report_id}/` | Staff with `property.report.review` | Set `status` to `reviewed` or `dismissed`, with an optional `resolution_note`. |
| GET | `/staff/reviews/` | Staff with `property.review.moderate` | List pending reviews; filter with `?status=approved` or `?status=rejected`. |
| PATCH | `/staff/reviews/{review_id}/` | Staff with `property.review.moderate` | Approve or reject a pending review; verify non-pending reviews cannot be moderated twice. |

Property creation JSON:

```json
{
  "name": "Test property",
  "description": "API test listing",
  "street": 1,
  "latitude": "-6.8000000",
  "longitude": "39.2800000"
}
```

Room creation JSON:

```json
{
  "room_type": "single",
  "price": "250000.00",
  "capacity": 1,
  "length_m": "4.00",
  "width_m": "3.00",
  "facilities": "Desk",
  "security_info": "Secure entry"
}
```

The same verification file requirements and upload workflow apply when adding
additional documents. See [API_WORKFLOWS.md](./API_WORKFLOWS.md) for file limits,
storage behavior, and verification workflow details.

### Booking, payment, notification, and webhook routes

| Method | Route | Access | Basic check |
|---|---|---|---|
| GET, POST | `/bookings/` | Customer | List own bookings; create with `{"room_id": <available room id>}`. |
| GET | `/bookings/{booking_id}/` | Booking's customer | Read own booking; try another customer's booking. |
| POST | `/bookings/{booking_id}/cancel/` | Booking's customer | Cancel a cancellable booking; retry to check invalid transition handling. |
| POST | `/bookings/{booking_id}/confirm/` | Staff | Confirm a pending booking. |
| POST | `/bookings/{booking_id}/reject/` | Staff | Reject a pending booking. |
| GET, POST | `/payments/` | Customer | List own payments; create using `booking_id` and `payment_method` for an eligible booking. |
| GET | `/payments/{payment_id}/` | Payment's customer | Read own payment; try another customer's payment. |
| GET | `/receipts/` | Customer | List only the signed-in customer's receipts. |
| GET | `/notifications/` | Authenticated | List notifications for the signed-in account. |
| POST | `/notifications/{notification_id}/read/` | Authenticated | Mark an owned notification read; try a notification for another recipient. |
| GET, POST, DELETE | `/webhooks/` | Authenticated owner or staff | List own subscriptions; create with body below; delete by sending `{"subscription_id": <id>}`. |

Webhook creation example (use an HTTPS test receiver that you control):

```json
{
  "target_url": "https://example.test/webhook",
  "event_types": ["verification.submitted"]
}
```

Save the secret from the create response only in a secure test environment.
Verify rejection of HTTP URLs, private-network targets, unsupported events, and
deleting a subscription owned by another account. Delivery is asynchronous; see
[API_WORKFLOWS.md](./API_WORKFLOWS.md) for dispatch and signature verification.

### Staff and system routes

| Method | Route | Access | Basic check |
|---|---|---|---|
| GET | `/staff/me/` | Staff | Read the current staff profile. |
| GET, POST | `/staff/accounts/` | Staff with `staff.manage` | List staff; create staff using required identity/contact/password/branch/role fields. |
| PATCH | `/staff/accounts/{staff_id}/role/` | Staff with `staff.manage` | Send `{"role_id": <id>}`; verify no permission escalation and no self-role change. |
| PATCH | `/staff/accounts/{staff_id}/status/` | Staff with `staff.manage` | Send a valid `{"status":"..."}` from `Staff.Status.choices`; verify self-status change is rejected. |
| GET, PATCH | `/system/settings/` | Staff | Read settings and patch a valid setting field; verify invalid values are rejected. |
| GET | `/system/audit-logs/` and `/system/audit-logs/{id}/` | Staff | List and retrieve audit records; try a non-staff token. |
| GET | `/system/visitor-logs/` and `/system/visitor-logs/{id}/` | Staff | List and retrieve visitor records; try a non-staff token. |

Create a separate staff account with `property.verification.review` to test
verification decisions. Staff management operations require `staff.manage`;
use a manager token for allowed changes and a staff token without that permission
to verify the `403` path.

### Read-only catalog routes

Each listed route supports `GET` on the collection and `GET /{id}/` for an
existing record. These are read-only; try `POST`, `PUT`, `PATCH`, and `DELETE`
and verify they are not allowed. Collection requests should work without a
token unless noted otherwise.

| Collection route | Access | Useful filter / check |
|---|---|---|
| `/locations/regions/` | Public | List and retrieve a region. |
| `/locations/districts/` | Public | Try `?region_id=<id>`. |
| `/locations/wards/` | Public | Try `?district_id=<id>`. |
| `/locations/streets/` | Public | Try `?ward_id=<id>`. |
| `/universities/` | Public | List and retrieve universities. |
| `/campuses/` | Public | Try `?university_id=<id>`. |
| `/properties/` | Public | Only verified properties are visible; try `region_id`, `district_id`, `ward_id`, `min_price`, `max_price`, and `room_type` filters. |
| `/properties/media/` | Public | Only media for verified properties should be visible. |
| `/rooms/` | Public | Only available rooms for verified properties should be visible; try `?property_id=<id>`. |
| `/rooms/media/` | Public | Only media for available rooms in verified properties should be visible. |
| `/staff/roles/` | Staff | Test with staff and non-staff credentials. |
| `/staff/permissions/` | Staff | Test with staff and non-staff credentials. |
| `/staff/ranks/` | Staff | Test with staff and non-staff credentials. |
| `/staff/departments/` | Staff | Test with staff and non-staff credentials. |
| `/staff/verifications/` | Staff | Verify access is staff-only. |
| `/staff/verification-documents/` | Staff | Verify access is staff-only and records are retrievable by ID. |

For public catalogs, test empty and populated data, a valid detail ID, a missing
detail ID, and each listed filter. For public property/room data, confirm that
unverified properties and unavailable rooms do not appear.

## 4. Common negative and isolation checks

Apply these checks across the routes above:

1. Omit authentication for a protected operation, then retry with a valid token.
2. Use a token for the wrong account type (for example, owner token on a customer
   profile) and expect access to be denied.
3. Use customer A's token to read or mutate customer B's bookings, payments,
   favourites, notifications, or private verification documents.
4. Submit missing required fields, invalid foreign-key IDs, invalid enum values,
   and malformed JSON; expect a validation error, not a successful mutation.
5. Repeat stateful operations (booking cancellation/decision, verification
   review, refresh-token rotation) to confirm invalid state transitions/replays
   are rejected.
6. After create/update/delete, fetch the collection/detail or database-backed
   state to confirm the expected side effect and ownership boundary.

The API's field definitions and validation rules live in the corresponding
serializers under `api/v1/serializers/`; check those when constructing payloads
not shown above.
