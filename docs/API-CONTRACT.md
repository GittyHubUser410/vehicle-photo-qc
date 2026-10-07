# Vehicle QC API Contract Policy

Vehicle QC uses FastAPI. As the application gains more clients and integrations, the generated OpenAPI schema should be treated as the authoritative machine-readable API contract.

## Policy

- Work reviews API compatibility when planning features that affect frontend/backend boundaries.
- Codex updates endpoints, request/response schemas, tests, and generated OpenAPI behavior together.
- Avoid breaking existing API behavior without an explicit migration/versioning decision.
- Human Training should expose backend/domain behavior that can be consumed by the current web client and a future Android capture client.
- Future dealer portal and PC operations clients should reuse documented APIs rather than creating direct database dependencies.
- Integration work with DigiLot/HomeNet should use explicit adapter/service boundaries.
- API contract changes that materially affect clients should be noted in the relevant handoff and verification report.

## v0.2 priority

During v0.2A–v0.2C, Work should identify and stabilize the API surfaces most likely to be shared by future clients, especially:

- authentication/account scope,
- dealership and photographer metadata,
- uploads and analysis jobs,
- review results,
- shot types/sequences,
- Human Training sessions/references/captures/results,
- model metadata exposed to authorized users.

A later milestone may add explicit schema snapshot/compatibility tests if the number of clients or integrations makes them worthwhile.
