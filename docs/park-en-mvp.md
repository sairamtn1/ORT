# ORT MVP implementation

## Runtime components

| Component | Implementation |
| --- | --- |
| Web | Next.js 15 App Router, TypeScript, Tailwind CSS v4, shadcn/ui-compatible primitives |
| API | FastAPI, Pydantic, async SQLAlchemy 2 |
| Database | PostgreSQL 16, Alembic-managed schema |
| Identity | Short-lived HS256 JWT access tokens; mobile OTP challenges; Argon2 remains for legacy login |
| SMS | Twilio Messages REST API; explicit development-only OTP response |
| Maps | Mapbox GL JS when `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN` is configured |
| Containers | Docker Compose for web, API, PostgreSQL, migration-on-start, and optional demo seed |

## Data model

The original marketplace schema remains in place (`users`, `owners`, `admins`,
`parking_lots`, `parking_slots`, `bookings`, `payments`, `reviews`, and
`notifications`). The operations migration adds:

- `otp_challenges`: HMAC-protected, expiring, attempt-limited, one-time mobile
  verification codes.
- `vehicles`: user-owned vehicles with normalized unique plate numbers.
- `staff_assignments`: staff-to-location authorization.
- `parking_sessions`: unique public session identifier, one-time QR token hash,
  vehicle/customer/location, optional slot, check-in/out times, and sync state.
- `incidents`: location/session-linked issue reports.

Parking locations persist type, mode, identification method, and closure state.
Slots persist category and level/zone labels. Reservations lock the slot row and
reject overlapping time intervals; the API checks that the associated lot is
active and open. Starting a session locks an optional slot and PostgreSQL
enforces that an occupied slot is not attached to two active sessions.

The migration also introduces normalized parking levels/zones and links slots
to them. Corporate passes support permanent, employee, executive, and visitor
types, expiry/revocation, holder-owned reservations, and staff validation.
Bookings created against a pass retain the originating pass ID. Valet sessions
enforce handover → retrieval request → retrieval completion → session close.
Hospital staff can grant emergency priority and use a maintenance slot only
with an auditable reason; closing the session restores the slot to maintenance.

## API routes

All routes below are rooted at `/api/v1`.

| Route | Purpose |
| --- | --- |
| `POST /auth/otp/request`, `POST /auth/otp/verify` | Request and verify a phone OTP; receive a bearer JWT |
| `GET /auth/me` | Resolve the token to the active account and role |
| `GET /parking/search` | Public discovery filters, optional coordinates/radius, availability and price |
| `/parking-lots`, `/parking-slots`, `/bookings` | Existing secured CRUD and booking lifecycle |
| `/vehicles` | List/add a user's vehicles; delete checks active session references |
| `/parking-sessions` | Start a customer walk-in, list sessions by role, assign a slot, close a session |
| `GET /parking-sessions/lookup` | Staff/owner lookup by QR token, public session ID, or vehicle plate |
| `/parking-sessions/{id}/valet/*` | Record valet handover and retrieval lifecycle |
| `PATCH /parking-sessions/{id}/priority` | Set/clear hospital emergency priority with reason validation |
| `GET /parking-lots/{id}/levels` | Read normalized levels/zones for a location |
| `/corporate/passes` | List, create, and revoke visitor/corporate passes |
| `GET /corporate/passes/lookup` | Validate a currently active pass at an assigned location |
| `POST /corporate/passes/{id}/reservations` | Create a holder-owned booking linked to its corporate pass |
| `GET /parking/managed-lots` | List locations available to a signed-in operator |
| `POST /staff-assignments` | Owner/admin assignment of staff to a location |
| `GET /owner/analytics` | Capacity, occupancy, location, booking, and revenue totals |
| `POST /incidents` | Report safety, facility, payment, vehicle, staff, or other issue |
| `/api/docs`, `/api/openapi.json` | Interactive API docs and machine-readable OpenAPI |

## Authentication and authorization

OTP request throttling serializes requests per phone in PostgreSQL, enforces a
60-second resend interval and a five-per-hour cap, and expires codes after five
minutes. Only five verification attempts are allowed. Only an HMAC is stored.
Production requests are sent with Twilio; test codes are returned only when
both `APP_ENV=development` and `OTP_DEV_MODE=true`. OTP sign-in never accepts a
role from the client: first-time accounts are customers. Elevating users to
owner/staff/admin requires trusted provisioning. The API checks location
ownership or staff assignment before operational writes.

## Local verification commands

```powershell
pnpm --filter @parken/web typecheck
pnpm --filter @parken/web build
$env:PYTHONPATH = "services/api"
python -m compileall services/api/app services/api/migrations/versions
python -m alembic -c services/api/alembic.ini upgrade head
python -m alembic -c services/api/alembic.ini check
```

Schema migrations are additive. The `staff` enum value is intentionally not
removed on downgrade, because PostgreSQL does not support a safe transactional
enum-value removal.
