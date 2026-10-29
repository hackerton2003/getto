# Getto API Postman tests

Use the collection in `collections/Getto Platform - Full Test Suite` with the
`Getto Local API Test` environment in `environments/New Environment.environment.yaml`.
The collection uses `http://127.0.0.1:8000/api/v1` by default. Start Django first:

```powershell
.\getto_env\Scripts\python.exe manage.py migrate
.\getto_env\Scripts\python.exe manage.py runserver
```

## First run

1. Import/select the environment and set `university_id` and `street_id` to
   existing records. `verified_property_id` and `room_id` must identify a
   **verified** property and an **available** room under it for booking tests.
   Location and university endpoints
   are read-only; seed those records through the database/admin first.
2. The customer email is set to `nasrikangaru@gmail.com`. Register that account
   once if it does not already exist; on later runs use `Login - Customer`.
   Registration saves access/refresh tokens. Owner registration remains a
   separate test account; use owner login on later runs if it already exists.
3. Enter an existing staff account in `staff_email` and `staff_password`, then
   run `Login - Staff`. The staff role needs `property.report.review`,
   `property.review.moderate`, and `property.verification.review` for those
   workflows.
4. Run `02-Locations-Universities` to discover IDs, `03-Properties-Rooms` to
   search or create owner listings, and then the customer/owner flows.

New properties are pending verification and new rooms are pending verification;
they will not appear in public search or be bookable until the database/workflow
marks them verified/available. For deterministic booking and review tests, use
an existing verified property with an available room and set
`verified_property_id` and `room_id` to its IDs. A confirmed booking is needed
before submitting a review.

## Useful flow order

- Search: public property/room search requests in `03-Properties-Rooms`.
- Owner: profile and dashboard, then list bookings and confirm/reject a pending
  booking in `10-Owner-Profile-Dashboard-Bookings`.
- Customer: profile/preferences/favourites, create booking, then read/cancel it.
- Reports/reviews: customer creates a report or review; staff reviews it in
  `11-Reports-Reviews`.
- Security: run `09-Security-Edge-Cases` to check missing/invalid credentials
  and cross-account booking access.

Logout is skipped by default because the auth folder runs before the rest of the
collection. Set `run_logout` to `true` only when you want to test logout
separately. Password-reset confirmation is skipped until you paste a valid
`password_reset_token` from the reset email into the environment.

Payment requests are kept in their own optional section. They require an eligible
booking and are not needed for the non-payment API smoke test.

Responses save IDs/tokens into the selected environment where possible. Use a
local test database and test-only accounts; never export real credentials or
tokens with the collection.
