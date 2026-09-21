# ParkEn

Architecture for a production-grade parking marketplace MVP: “Find. Reserve. Park.”

## Run & Operate

The FastAPI backend implementation lives in `services/api`. The original Express starter artifact is preserved, but the managed API workflow now serves FastAPI from the ParkEn service.

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- Target frontend: Next.js 15, TypeScript, Tailwind, shadcn/ui
- Target API: FastAPI, Pydantic, SQLAlchemy 2, Alembic
- Target database: PostgreSQL + PostGIS
- Target identity: Clerk-managed authentication
- Target maps: Mapbox
- Target AI: Gemini through Replit AI Integrations
- Target coordination: Redis for holds, rate limits, and jobs; PostgreSQL remains the reservation source of truth

## Where things live

- `docs/park-en-architecture.md` — complete system architecture, boundaries, API surface, auth, Docker, environment contract, and roadmap
- `docs/park-en-er-diagram.mmd` — standalone Mermaid ER diagram
- `artifacts/api-server` — existing starter API artifact; not yet converted to the ParkEn FastAPI target
- `artifacts/mockup-sandbox` — existing reusable design/mockup artifact
- `services/api/app` — FastAPI application, models, schemas, repositories, services, controllers, middleware, and error handling
- `services/api/migrations` — Alembic migration environment and initial PostgreSQL schema migration

## Architecture decisions

- PostgreSQL/PostGIS is the source of truth for inventory and reservations; Redis only accelerates short-lived coordination.
- The current backend uses application-managed HS256 JWT authentication with Argon2 password hashing; ParkEn owns domain roles and ownership rules.
- Reservation overlap is prevented by a PostgreSQL exclusion constraint in addition to application transaction logic.
- Mapbox and Gemini are isolated behind backend adapters; the browser never receives server credentials.
- The first implementation deliberately excludes payment capture and multi-space inventory to keep reservation correctness shippable.

## Product

ParkEn connects drivers with approved parking-space owners. The planned MVP supports geospatial search, availability-aware quotes, reservations, owner listing management, admin moderation, and a constrained Gemini parking assistant.

## User preferences

- Architecture first; do not start application implementation until the user asks for the next phase.

## Gotchas

- Do not treat the existing Express/Drizzle scaffold as the final ParkEn stack; it is preserved until implementation begins.
- Do not expose password hashes or JWT signing secrets; use the configured JWT secret contract and keep direct client-to-database access prohibited.
- Do not use Redis as booking truth; a Redis outage must not permit duplicate confirmed reservations.
- Store money as integer minor units and all timestamps as timezone-aware UTC values.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
