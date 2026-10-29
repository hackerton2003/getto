# API Workflow Operations

All API paths are under `/api/v1/`.

For the complete route-by-route manual testing checklist, see
[API_TESTING_GUIDE.md](./API_TESTING_GUIDE.md).

## Token lifecycle

- `POST /auth/login/` returns a 15-minute access token and a 30-day refresh token.
- `POST /auth/refresh/` accepts `{"refresh_token": "..."}` and rotates both tokens. A refresh token can be used only once.
- `POST /auth/logout/` requires a Bearer access token and the matching refresh token in the body; it revokes that session immediately.
- Password resets and account suspension/deactivation revoke active sessions.

Refresh tokens are stored as hashes. Keep the raw refresh token in a secure client-side store and never log it.

## Verification uploads

Owners upload one PDF, JPEG, or PNG per request using `multipart/form-data`:

`POST /owners/me/properties/{property_id}/verifications/`

Form fields: `file` (required) and `description` (optional). Add further files to a pending submission at:

`POST /owners/me/verifications/{verification_id}/documents/`

Uploads are limited to 10 MB, checked against their declared type and file signature, and written using Django's configured default storage. The default backend is local `FileSystemStorage` under `MEDIA_ROOT`. `DEFAULT_STORAGE_BACKEND` can select an installed remote backend; configure that provider's credentials/options outside source control. Downloads use an authenticated endpoint and are scoped to the owning account or staff.

## Property and room media uploads

Owners upload photos and video tours for their houses and rooms via multipart form data (`multipart/form-data`):

- `POST /owners/me/properties/{property_id}/media/`
- `DELETE /owners/me/properties/{property_id}/media/{media_id}/`
- `POST /owners/me/rooms/{room_id}/media/`
- `DELETE /owners/me/rooms/{room_id}/media/{media_id}/`

Owners and staff can also upload or delete media through the standard resource endpoints:
- `POST /properties/media/` (form fields: `property_id`, `file`, optional `type`)
- `DELETE /properties/media/{media_id}/`
- `POST /rooms/media/` (form fields: `room_id`, `file`, optional `type`)
- `DELETE /rooms/media/{media_id}/`

Accepted image formats: JPEG, PNG, WEBP (up to 15 MB).
Accepted video formats: MP4, WEBM, MOV (up to 50 MB).
Files are validated by magic byte headers and written to storage. Media objects return `file_url` along with `file_path`. Media of verified properties and available rooms is publicly queryable via `GET /properties/media/?property_id={id}` and `GET /rooms/media/?room_id={id}`.


## Webhooks

Owners and staff can register HTTPS endpoints at `POST /webhooks/` with `target_url` and `event_types`. The generated signing secret is shown only in the create response. Supported events are:

- `verification.submitted`
- `verification.document.uploaded`
- `verification.approved`
- `verification.rejected`

Callbacks are persisted to a delivery queue; application requests do not call subscribers synchronously. Run `python manage.py deliver_webhooks --limit 100` from a scheduled worker. Failures retry with exponential backoff for up to eight attempts. Redirects and private-network destinations are rejected.

The sender provides `X-Getto-Timestamp` and `X-Getto-Signature`. Verify the HMAC-SHA256 over `timestamp + "." + raw_request_body` with the subscription secret, then compare against `sha256=<hex digest>` using a constant-time comparison. Reject stale timestamps to limit replay.

## Staff permissions

Grant `staff.manage` to staff who may create staff accounts or assign roles. A staff member cannot grant roles containing permissions they do not hold and cannot change their own role. Grant `property.verification.review` to staff allowed to approve/reject property verification. Successful staff changes and reviews create audit records.

Grant `property.report.review` to staff who may list and resolve property reports at `GET /staff/reports/` and `PATCH /staff/reports/{report_id}/`. Reports may be marked `reviewed` or `dismissed`; include a `resolution_note` where useful.

Owners can review booking requests for their properties at `GET /owners/me/bookings/` and decide pending requests with `POST /owners/me/bookings/{booking_id}/confirm/` or `/reject/`. Customers may submit one review per property after a confirmed booking and can edit or delete their review at `/reviews/{review_id}/`. New and edited reviews remain private until staff with `property.review.moderate` approves them through `/staff/reviews/` and `/staff/reviews/{review_id}/`.

Booking creation and status changes, plus verification submission and review, create in-app notifications for the affected owner or customer. Email notifications can be sent through Django's configured email backend by choosing the `email` channel. SMS delivery requires an SMS provider integration; the current project has no provider adapter.
