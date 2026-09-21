---
name: ParkEn architecture
description: Durable system decisions for the ParkEn parking marketplace MVP.
---

ParkEn's target architecture uses FastAPI for the business API, application-managed JWT authentication for the current backend, PostgreSQL/PostGIS as the source of truth, Redis only for short-lived coordination and jobs, Mapbox behind an adapter, and Gemini through Replit AI Integrations.

**Why:** The user explicitly requested JWT authentication for the implementation, superseding the earlier Clerk recommendation; reservation integrity and provider isolation remain important because the product must stay correct under concurrent booking attempts and external-service failures.

**How to apply:** Future implementation work should follow `docs/park-en-architecture.md`, especially the JWT secret contract, role/ownership policy layers, and serialized booking creation.