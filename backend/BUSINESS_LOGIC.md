# Backend Business Logic

This document summarizes the backend's implemented business rules. API paths are under `/api/v1/`. The API layer validates and authorizes requests; reusable rules and multi-record operations live primarily in `services/`; Django models and migrations enforce important invariants in the database.

## Accounts and authentication

- The platform has customer, accommodation-owner, and staff accounts. Registration stores passwords using Django's password hashing and validates them against configured password validators.
- Login accepts an account type, email, and password. Authentication is case-insensitive for email and succeeds only for active accounts. Invalid account details produce the same generic authentication error.
- Access tokens expire after 15 minutes. Refresh tokens expire after 30 days, are stored as hashes, and rotate on use. Logout revokes the associated session. Password resets expire after one hour, are one-time use, and revoke active sessions after a successful reset.
- Suspending or deactivating a customer, owner, or staff account revokes their active sessions.

Implementation: [services/authentication.py](services/authentication.py), [apps/authentication/authentication.py](apps/authentication/authentication.py), [services/customers.py](services/customers.py), [services/house_owners.py](services/house_owners.py), and [services/staff.py](services/staff.py).

## Properties, rooms, and verification

- Owners manage only properties and rooms they own. Owner-editable property fields are limited to name, description, street, latitude, and longitude. Editing a property returns its verification state to pending.
- Room prices must be nonnegative, capacity must be positive, property room counts must be nonnegative, and available rooms cannot exceed total rooms. Room counts are synchronized from room records after room and booking changes.
- Property verification requires at least one PDF, JPEG, or PNG document. Files must be 1 byte to 10 MB and pass both extension/content-type and file-signature checks. Only one pending verification may exist per property; verified properties cannot be resubmitted.
- Only active staff with the required verification permission may review a pending verification. Rejections require a reason. Approval or rejection updates both the verification record and the property's verification status.
- Property and room media uploads validate file signatures and size: images up to 15 MB and videos up to 50 MB. Owners are scoped to their own resources; staff may manage media under staff permissions. Verification documents are downloadable only by the owning account or staff.

Implementation: [services/properties.py](services/properties.py), [services/verifications.py](services/verifications.py), [apps/properties/models.py](apps/properties/models.py), and [api/v1/serializers/properties.py](api/v1/serializers/properties.py).

## Booking lifecycle and room availability

- Only active customers can request an available room. Creating a booking locks the property and room, creates a pending booking, reserves the room, synchronizes room counts, and notifies the owner.
- A room may have at most one active booking (pending or confirmed), enforced by a database uniqueness constraint as well as service-level locking and validation.
- Allowed transitions are pending → confirmed, rejected, cancelled, or expired; confirmed → cancelled or expired. Terminal states cannot transition further. Repeating the current status is idempotent.
- When a booking is cancelled, rejected, or expired, the room becomes available if it has no other active booking; otherwise it remains reserved. Pending bookings may be expired by staff or by the stale-booking cleanup command after a configured age.
- Owners can list bookings for their own properties and confirm or reject them. Customers can view or cancel only their own bookings. Staff can make authorized booking decisions and expire stale requests.

Implementation: [services/bookings.py](services/bookings.py), [apps/bookings/models.py](apps/bookings/models.py), and [apps/bookings/management/commands/cleanup_stale_bookings.py](apps/bookings/management/commands/cleanup_stale_bookings.py).

## Payments and receipts

- Payments can be created only for pending or confirmed bookings. The rental amount is captured from the room price; the service fee defaults to the configured percentage (10% when no settings record exists), rounded to cents. The total equals rental amount plus service fee.
- A payment begins pending. A pending payment can become completed or failed; completed payments cannot be failed and failed payments cannot be completed. Completion creates one receipt if one does not already exist.
- The current payment service manages payment records and status transitions; this backend code does not itself connect to a payment gateway.

Implementation: [services/payments.py](services/payments.py), [apps/payments/models.py](apps/payments/models.py), and [apps/system/models.py](apps/system/models.py).

## Customer preferences, favourites, reviews, and reports

- Each customer has a single preference record. Minimum and maximum prices must be nonnegative and minimum cannot exceed maximum. District and ward selections must match their parent region/district.
- Favourites are unique per customer and property; adding an existing favourite is idempotent.
- A customer may review a property only after having a confirmed booking there, may submit one review per property, and must use a rating from 1 to 5. New reviews are pending moderation. Editing a review returns it to pending and clears the previous moderation metadata. Only pending reviews can be moderated; only approved reviews appear in the public review list.
- Customers can report a property with a nonblank reason. Staff with the report-review permission can mark a report reviewed or dismissed and record a resolution note.

Implementation: [services/customers.py](services/customers.py), [apps/customers/models.py](apps/customers/models.py), and [apps/staff/views.py](apps/staff/views.py).

## Staff authorization and auditing

- Staff actions are permission-gated. Staff account creation and role assignment require staff-management permission; verification review, report review, and review moderation have separate permissions.
- A staff member cannot change their own role or status, and cannot assign a role containing permissions they do not hold. Only active staff can review property verification.
- Successful staff account changes and moderation/review actions write audit records.

Implementation: [services/staff.py](services/staff.py), [api/v1/permissions.py](api/v1/permissions.py), [apps/staff/views.py](apps/staff/views.py), and [api/v1/utils.py](api/v1/utils.py).

## Notifications and webhooks

- Booking and verification lifecycle events create in-app notifications for the affected account.
- Webhook subscriptions are scoped to an owner or staff account. Only supported verification events may be subscribed to. Targets must use HTTPS, avoid credentials/fragments and local/private destinations, and are checked again at delivery time to reduce server-side request forgery risk.
- Webhook secrets are returned on creation only. Deliveries are queued and sent by the `deliver_webhooks` management command, signed using HMAC-SHA256, sent without following redirects, and retried with exponential backoff for up to eight attempts.

Implementation: [services/notifications.py](services/notifications.py), [services/webhooks.py](services/webhooks.py), [apps/notifications/models.py](apps/notifications/models.py), and [apps/notifications/management/commands/deliver_webhooks.py](apps/notifications/management/commands/deliver_webhooks.py).

## System settings and reference data

- System settings are a single logical record. Updates are restricted to supported settings fields; service-fee percentage must be between 0 and 100, and theme values must be valid choices.
- Geographic and university reference data are exposed as read-only API resources. Districts, wards, streets, and campuses are associated with their parent region, district, or university.

Implementation: [services/system.py](services/system.py), [apps/system/models.py](apps/system/models.py), [services/locations.py](services/locations.py), and [services/universities.py](services/universities.py).

## Database enforcement and API behavior

Important invariants are enforced both in services and, where appropriate, with database constraints and indexes in model definitions and migrations. Serializer and permission classes define request validation and endpoint access; the service layer should remain the preferred entry point for operations that change several related records. API routing and interactive schema documentation are described in [API_WORKFLOWS.md](API_WORKFLOWS.md) and [API_TESTING_GUIDE.md](API_TESTING_GUIDE.md).
