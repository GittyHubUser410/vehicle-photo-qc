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

## v0.2A.1 evidence contract — implementation target

Status: Work design ready; the following is not yet implemented. See
`architecture/V0.2A.1-REVIEW.md` and `handoffs/work-to-codex/V0.2A.1.md`.

- Preserve existing value, score, approval-intent and legacy check fields; add typed evidence and exportability fields. `eligible` alone no longer establishes verified training readiness.
- Training label requests add explicit `verify_fields` (default empty). Operational shot requests add `verify` (default false) and revision; confirmation requires a matching revision. Old requests never imply new verification.
- Actor/model/time provenance is server-produced. Authenticated request identity takes precedence over client actor text; local declarations are labeled as such.
- Evidence responses distinguish suggested, verified, predicted and legacy-unverified provenance. Unknown values, applicability, execution and check outcomes are separate concepts.
- Add a versioned structured run check envelope rather than changing the legacy string-valued `checks` mapping into objects. Technical score scope and run freshness must be explicit.
- Dataset schema 2 carries verified relevant-label evidence. Schema 1 remains historical/read-only and cannot silently feed new train/evaluate commands as verified ground truth. This is an intentional evidence-safety compatibility boundary authorized by the A.1 handoff; provide actionable errors and migration documentation.
- Update FastAPI request/response schemas, TypeScript types, consumers and contract tests together. Existing historical fields and artifacts remain readable; no old record is silently promoted to stronger evidence.
