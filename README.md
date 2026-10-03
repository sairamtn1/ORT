# ORT

**Find. Reserve. Park.**

ORT is a parking discovery and operations MVP. The monorepo includes a
responsive Next.js 15 product site and customer/operations portal plus a
FastAPI service backed by PostgreSQL and SQLAlchemy. Drivers can search live
inventory, sign in with a mobile OTP, reserve a slot, manage vehicles, start
walk-in sessions, use valet retrieval, and view digital parking passes.
Parking teams can assign spaces, validate passes, report incidents, manage
hospital-priority overrides, and view owner analytics.

## Run the demo with Docker

1. Copy `.env.example` to `.env` and replace `JWT_SECRET` with a random secret
   of at least 32 characters. The Compose password shown in the example is for
   local development only.
2. Start PostgreSQL, run migrations, and seed demo inventory:

   ```powershell
   docker compose --profile demo up --build
   ```

3. Open [http://localhost:3000](http://localhost:3000). The API docs are at
   [http://localhost:8000/api/docs](http://localhost:8000/api/docs).

For local development without Docker, start PostgreSQL, set `DATABASE_URL` and
`JWT_SECRET`, apply migrations, and seed the data:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://parken:your-password@localhost:5432/parken"
$env:JWT_SECRET = "replace-with-a-random-secret-at-least-32-characters-long"
$env:OTP_DEV_MODE = "true"
$env:PYTHONPATH = "services/api"
python -m alembic -c services/api/alembic.ini upgrade head
python -m app.seed
python -m uvicorn app.main:app --reload --port 8000
```

In another terminal, run the web app:

```powershell
pnpm install
pnpm --filter @parken/web dev
```

Development OTP mode is deliberately limited to `APP_ENV=development` and
returns a test code in the API response. Production requires Twilio credentials
and `OTP_DEV_MODE=false`. `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN` enables the
interactive Mapbox map; without it, the UI displays a clearly labelled map
preview instead.

## Demo accounts

Demo seed users sign in using OTP (no passwords):

| Role | Phone |
| --- | --- |
| Parking owner | `+919900000001` |
| Parking staff | `+919900000002` |
| Customer | `+919900000003` |

The customer seed includes a vehicle. In development, request an OTP to see the
code in the sign-in dialog. Roles are not selectable during sign-in; new numbers are created as customers.
Staff/admin access must be provisioned by an administrator. Owners can onboard
through the legacy registration flow and complete trusted business verification.

## Repository layout

```text
apps/web/                    Next.js 15, TypeScript, Tailwind, shadcn/ui
services/api/app/api/v1/     FastAPI routers and domain operations
services/api/app/models/     SQLAlchemy models
services/api/app/services/   OTP, booking, and authorization services
services/api/migrations/     Alembic PostgreSQL migrations
services/api/app/seed.py     Idempotent demo inventory and role seed
docs/                        Architecture and implementation notes
docker-compose.yml           PostgreSQL, API, web, and optional seed profile
```

## Implemented MVP surfaces

- Public inventory search by text, parking type, mode, and radius from the
  browser's location; available-slot count and starting price.
- Customer/owner/staff/admin JWT roles, mobile OTP, vehicle garage, slot
  reservations, walk-in parking sessions with a one-time QR pass, session
  lookup by QR token/session ID/vehicle number, and session exit.
- Owner/staff access is checked against owned or assigned locations. Slot
  assignment and active-slot uniqueness are enforced transactionally.
- Parking levels/zones are represented on inventory slots; categories include
  regular, EV, disabled, VIP, and visitor.
- Visitor/corporate pass creation, account-holder reservations, staff QR-code
  validation, and revocation are available. Valet sessions use explicit
  handover, retrieval-request, retrieval-complete, and close transitions.
- Hospital emergency priority is limited to staff at hospital locations;
  assigning a maintenance slot requires an emergency flag and an audited
  reason. Overridden maintenance slots are restored when the session closes.
- Owner analytics for current occupancy, capacity, confirmed/completed booking
  revenue, and reservation counts.
- Incident reporting and a browser-side offline exit queue that retries after
  reconnecting.
- Production containers, health checks, Alembic migrations, OpenAPI docs, and
  seeded Bangalore demo locations.

Payment processing, camera-based QR scanning, actual Mapbox turn-by-turn
directions, predictive occupancy forecasting, full employee account
provisioning, and provider-managed durable offline sync are not enabled by
this MVP. The API retains booking/payment/review surfaces; the deployer must
connect a payment provider and configure OTP and Mapbox credentials before
production use. Offline exits are held in browser storage and should not be
treated as a durable multi-device sync queue.

## Production checklist

- Set a high-entropy `JWT_SECRET`, `APP_ENV=production`, `OTP_DEV_MODE=false`,
  database credentials, `CORS_ORIGINS`, and Twilio credentials.
- Set `NEXT_PUBLIC_API_URL` to the browser-reachable HTTPS API URL and configure
  a Mapbox public token; restrict that token to the deployed domains.
- Terminate TLS at a trusted ingress, use managed PostgreSQL backups, and
  configure centralized logs/alerts and request rate limits at the edge.
- Run database migrations as a release job when deploying replicas rather than
  racing migrations across independently started containers.
- Review retention, consent, incident evidence, and local phone-number
  regulations for each launch market.
