# ORT FastAPI API

## Configure and run

Set `DATABASE_URL` and a high-entropy `JWT_SECRET` before starting. The
repository-root Docker Compose file starts PostgreSQL, applies the Alembic
migrations, and serves the API on port 8000.

For local API development, from the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e services/api
$env:PYTHONPATH = "services/api"
python -m alembic -c services/api/alembic.ini upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

Use `python -m app.seed` after applying migrations to create the demo inventory.

## Phone authentication

- `POST /api/v1/auth/otp/request`
- `POST /api/v1/auth/otp/verify`
- `GET /api/v1/auth/me`

In local development, set `APP_ENV=development` and `OTP_DEV_MODE=true` to
receive a development-only test code in the request response. Production sends
SMS through Twilio and requires `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and
`TWILIO_FROM_NUMBER`; set `OTP_DEV_MODE=false`.

The older email/password register and login endpoints remain available for
existing clients. New phone-verified accounts receive the customer role.
Staff/admin accounts require administrator provisioning; owner onboarding must
complete the existing owner-verification flow.

Use the returned short-lived JWT on protected endpoints:

```text
Authorization: Bearer <access_token>
```

## Migrations

```powershell
$env:PYTHONPATH = "services/api"
python -m alembic -c services/api/alembic.ini upgrade head
python -m alembic -c services/api/alembic.ini check
```

## API surface

CRUD controllers cover users, owners, admins, parking lots/slots, bookings,
payments, reviews, and notifications. Operational endpoints cover public
search, vehicles, walk-in sessions, staff assignment/lookup/slot assignment,
incidents, and owner occupancy/revenue summaries. Additional workflows cover
normalized parking levels/zones, digital corporate and visitor passes,
pass-holder reservations and staff pass validation, valet handover/retrieval,
and hospital emergency-priority overrides with audited maintenance-slot
restoration.

Interactive Swagger UI is at `/api/docs`; OpenAPI JSON is at `/api/openapi.json`.
