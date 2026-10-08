# ADR-004 — Label provenance and run-scoped QC evidence

**Status:** Accepted for v0.2A.1 engineering design; implementation pending.
**Date:** 2026-10-08
**Authority:** locked decisions in `docs/handoffs/chat-to-work/V0.2A.1.md`.
**Supersedes:** none; refines ADR-001/003 evidence requirements.

## Context

Convenient defaults, training approval and human verification currently share insufficiently distinguished fields. Operational and training shot labels are intentionally separate. Existing runs identify models but mutable shoot summaries cannot fully describe historical check coverage.

## Decision

- Separate stored values, evidence and training-use approval.
- Keep operational shot evidence/revisions separate from per-field training evidence and existing training revisions.
- Explicit confirmation creates verified evidence; defaults, copying, inferred order, and membership never do.
- Resolve authenticated attribution server-side; label local declared identity honestly.
- Preserve legacy values and artifacts without fabricating verification.
- Retain predictions and check applicability/execution/outcomes in immutable analysis-run snapshots.
- Preserve technical score arithmetic and expose its limited scope separately from QC coverage.
- New verified datasets use manifest schema 2; legacy snapshots remain historical artifacts and cannot silently enter new training/evaluation as verified truth.
- One shared evidence-policy helper governs export/readiness and field transitions; no new generic event-sourcing framework.

## Alternatives considered

1. Treat `eligible=True` or nonempty `labeled_by` as verification: rejected because imports/defaults and user-supplied actor text do not establish that fact.
2. Whole-example verification flag: rejected because confirming a shot must not certify unrelated quality defaults.
3. Replace all labels with normalized events: unnecessary migration and query complexity for A.1.
4. Retroactively recompute old results: rejected because it destroys historical meaning.

## Consequences

Some currently approved examples will require explicit verification before new exports; their values and approval intent survive. API responses grow additively, and new confirmation operations require revision checks. Old consumers can read legacy fields but must adopt the evidence contract before interpreting verified readiness. No new detector, role system or external service is introduced.

Detailed schema and transition rules: `docs/architecture/V0.2A.1-REVIEW.md`. Acceptance: `docs/V0.2A.1-ACCEPTANCE-TESTS.md`.
