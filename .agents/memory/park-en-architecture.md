---
name: ParkEn architecture
description: Durable system decisions for the ParkEn parking marketplace MVP.
---

ParkEn's target architecture uses Clerk for identity, FastAPI for the business API, PostgreSQL/PostGIS as the source of truth, Redis only for short-lived coordination and jobs, Mapbox behind an adapter, and Gemini through Replit AI Integrations.

**Why:** Reservation integrity and provider isolation are more important than minimizing initial services; the product must remain correct under concurrent booking attempts and external-service failures.

**How to apply:** Future implementation work should follow `docs/park-en-architecture.md`, especially the reservation exclusion constraint, role/ownership policy layers, and no-local-auth rule.