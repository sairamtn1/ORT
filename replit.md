# ORT

Working implementation of the ORT parking MVP: “Find. Reserve. Park.”

## Run & Operate

See `README.md` for Docker Compose and local setup. The Next.js application is
in `apps/web`; FastAPI and Alembic are in `services/api`.

- `pnpm --filter @parken/web dev` — run the Next.js app on port 3000
- `pnpm --filter @parken/web typecheck` — typecheck the web app
- `pnpm --filter @parken/web build` — build the production web app
- Set `DATABASE_URL`, `JWT_SECRET`, and `CORS_ORIGINS` for the API
- Configure Twilio for production OTP and Mapbox for live maps

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- Frontend: Next.js 15, TypeScript, Tailwind CSS v4, shadcn/ui-compatible components
- API: FastAPI, Pydantic, SQLAlchemy 2, Alembic
- Database: PostgreSQL
- Identity: application-managed JWT with mobile OTP; Twilio sends production codes
- Maps: Mapbox GL JS when a public token is configured
- Deployment: Docker Compose for web, API, database, migrations, and demo seed

## Where things live

- `README.md` — quick start, demo accounts, implemented surfaces, and production checklist
- `docs/park-en-mvp.md` — current schema, API routes, authentication, and run commands
- `docs/park-en-architecture.md` — broader architecture reference
- `docs/park-en-er-diagram.mmd` — standalone Mermaid ER diagram
- `artifacts/api-server` — preserved legacy Express starter artifact
- `artifacts/mockup-sandbox` — existing reusable design/mockup artifact
- `services/api/app` — FastAPI application, models, schemas, repositories, services, controllers, middleware, and error handling
- `services/api/migrations` — Alembic migration environment and initial PostgreSQL schema migration

## Architecture decisions

- PostgreSQL is the source of truth. Booking writes lock slot rows and reject overlapping reservations.
- Mobile OTP is the sign-in path for new accounts; roles are not client-selectable. Staff/admin provisioning is privileged.
- Location operations enforce owner/staff assignment checks.
- Mapbox is optional for local UI development; payment capture and camera QR scanning require provider integrations.

## Product

ORT connects drivers with parking facilities. The current MVP supports search,
reservations, vehicle management, walk-in sessions, owner occupancy analytics,
staff session workflows, incident reports, and a browser-side offline-exit queue.

## User preferences

- Keep the web client and API as separate deployable services; preserve established workspace conventions.

## Gotchas

- Do not expose password hashes, OTP codes outside explicit development mode, or JWT signing secrets.
- Keep transaction validation and authorization in the API, not only in the browser.
- Persist monetary amounts as `Numeric` decimals and timestamps as timezone-aware UTC values.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
