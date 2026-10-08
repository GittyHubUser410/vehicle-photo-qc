# Vehicle QC Current State

## Project
Vehicle QC — dealership photography quality-control and training application.

## Current release
v0.1 pilot is the stable/presentable baseline. v0.2 is in planning.

## Planning branch
`docs/v0.2-planning`

## Known-good v0.1 checkpoint
`dc56f77a6105bf9a490e0f2ff07fd7883bb6c1ca`

## Current planning focus
Execute the revised evidence-gated sequence:
1. v0.2A.1 — verified labels, coverage, and QC evidence;
2. v0.2A.2 — small-team production foundation;
3. v0.2B.1 — manager queue, corrections, and operational metrics;
4. v0.2B.2 — pilot measurement and model diagnostics;
5. v0.2C — guided photography training/coaching;
6. v0.2D.1 — reliable delivery/destination verification;
7. v0.2D.2 — first specialized QC model expansion.

Integration research for DigiLot/HomeNet begins immediately, but production integration remains in v0.2D unless pilot evidence explicitly reprioritizes it.

## Required current references
- `docs/V0.2-ROADMAP.md`
- `docs/VEHICLE-QC-STRATEGIC-REVIEW-2026-10-07.md`
- `docs/VEHICLE-QC-VERSION-TIMELINE-REV2.md`
- `docs/V0.2A-CODEX-SPEC.md`
- `docs/V0.2A-ACCEPTANCE-TESTS.md`
- `docs/V0.2A-MIGRATION-NOTES.md`
- `docs/V0.2-HUMAN-TRAINING-MODE.md`
- `docs/architecture/C4.md`
- `docs/architecture/decisions/`
- `docs/API-CONTRACT.md`
- `docs/HUMAN-BOTTLENECK-WORKFLOW.md`

## Architecture direction
- React/Vite web client + FastAPI backend.
- PostgreSQL production path with SQLite transition compatibility where practical.
- Shot-aware ML routing.
- Independent specialized model lifecycles.
- Web-first Human Training with replaceable capture client.
- Native Android only when advanced capture requirements justify it.
- Web remains primary manager/dealer UI.
- Future desktop application, if built, is an operations/ML tool rather than the primary app.

## Workflow
Chat → Work → Codex → Work → Chat.

GitHub Issues should track implementation-sized work. The v0.2 GitHub Project is the execution view. Important UI-heavy work should have an approved Figma/FigJam reference before implementation.

Development is optimized around the user's decision/testing capacity. Maintain a small Ready-for-AI queue, limit concurrent independent implementation work, cap the Ready-for-Human-Test queue, and send the user compact Decision Packets / Human Test Packets rather than repeated low-level interruptions.

## Next approved checkpoint
**v0.2A.1 — Verified labels, coverage, and QC evidence.**

Do not treat suggested/defaulted labels as verified ground truth. Manager-visible QC must distinguish what was checked, what was not checked, applicability, and evidence/provenance state.

After A.1 passes, continue to **v0.2A.2 — Small-team production foundation**.

### A.1 Work review / next action

Architecture/data-model review completed against planning commit
`15cdbb8988433849aeedf1f3e261064888adef91`. **Implemented on `milestone/v0.2a1-evidence`; pending independent Work verification and owner acceptance.**

- Work review: `docs/architecture/V0.2A.1-REVIEW.md`.
- Engineering decision: `docs/architecture/decisions/ADR-004-label-and-check-evidence.md`.
- Bounded implementation handoff: `docs/handoffs/work-to-codex/V0.2A.1.md`.
- Required evidence: `docs/V0.2A.1-ACCEPTANCE-TESTS.md`.
- Implementation base: `e913a1e` on `docs/v0.2-planning`.
- Codex report: `docs/handoffs/codex-to-work/V0.2A.1.md`.
- Implementation PR: https://github.com/GittyHubUser410/vehicle-photo-qc/pull/10 (open; do not merge/deploy under the Codex handoff).
- Next executor: Work, independently verify the implementation PR against the bounded handoff.
- No new owner decision blocks implementation under the locked Chat handoff.
- Work independently verifies the resulting PR before the 15–30 minute owner acceptance session.

## Important preservation requirements
Do not lose existing photos, labels, model artifacts, datasets, dealership rules, review history, or working Cloudflare pilot configuration during migrations.

## AI Project Control Center
A separate cross-project Control Center project is approved. Vehicle QC should eventually register with it using standardized project metadata and human-attention task fields, while GitHub remains the engineering source of truth. Control Center implementation is out of scope for the Vehicle QC repository itself.


## Strategic pilot direction
Vehicle QC should be treated as a focused operational-quality pilot rather than a generic AI-photo product. The business case should be proven through measurable reductions in review labor, reshoots/return visits, false alerts, and delivery uncertainty. Specialized ML expansion is evidence-gated: add one validated high-value check at a time rather than several model families in parallel.
