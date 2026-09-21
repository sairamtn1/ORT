# ParkEn FastAPI API

## Run locally

From the repository root:

```bash
PYTHONPATH=services/api python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The Replit API workflow already supplies the equivalent command and routes the
service under `/api`.

## Database migrations

```bash
PYTHONPATH=services/api alembic -c services/api/alembic.ini upgrade head
PYTHONPATH=services/api alembic -c services/api/alembic.ini check
```

## Authentication

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

Use the returned bearer token for protected endpoints:

```text
Authorization: Bearer <access_token>
```

Public registration can create customer or parking-owner accounts. Admin
accounts must be provisioned by an existing administrator through the protected
admin CRUD endpoint.

## API surface

CRUD controllers are available for:

- users
- owners
- admins
- parking lots
- parking slots
- bookings
- payments
- reviews
- notifications

OpenAPI is available at `/api/openapi.json` in the Replit preview and the
interactive Swagger UI is at `/api/docs`.