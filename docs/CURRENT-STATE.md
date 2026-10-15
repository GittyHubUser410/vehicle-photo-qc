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
The historical A.1 workflow was Chat → Work → Codex → Work → Chat. The explicitly authorized port-8001 correction uses Standard 1.5.3.2: Chat → Work → Codex → Independent Review → Human Acceptance → Chat. Repository-wide adoption remains draft PR #11; this does not merge that proposal or expand authority.

GitHub Issues should track implementation-sized work. The v0.2 GitHub Project is the execution view. Important UI-heavy work should have an approved Figma/FigJam reference before implementation.

Development is optimized around the user's decision/testing capacity. Maintain a small Ready-for-AI queue, limit concurrent independent implementation work, cap the Ready-for-Human-Test queue, and send the user compact Decision Packets / Human Test Packets rather than repeated low-level interruptions.

## Next approved checkpoint
**v0.2A.1 — Verified labels, coverage, and QC evidence.**

Do not treat suggested/defaulted labels as verified ground truth. Manager-visible QC must distinguish what was checked, what was not checked, applicability, and evidence/provenance state.

After A.1 passes, continue to **v0.2A.2 — Small-team production foundation**.

### A.1 Work review / next action

Architecture/data-model review completed against planning commit
`15cdbb8988433849aeedf1f3e261064888adef91`. **Implemented on `milestone/v0.2a1-evidence`; independent Work recheck of `d78dd5b` passed. R1 is closed; ready for owner acceptance, not yet accepted.**

- Work review: `docs/architecture/V0.2A.1-REVIEW.md`.
- Engineering decision: `docs/architecture/decisions/ADR-004-label-and-check-evidence.md`.
- Bounded implementation handoff: `docs/handoffs/work-to-codex/V0.2A.1.md`.
- Required evidence: `docs/V0.2A.1-ACCEPTANCE-TESTS.md`.
- Implementation base: `e913a1e` on `docs/v0.2-planning`.
- Codex report: `docs/handoffs/codex-to-work/V0.2A.1.md`.
- Implementation PR: https://github.com/GittyHubUser410/vehicle-photo-qc/pull/10 (open; do not merge/deploy under the Codex handoff).
- Independent review/correction handoff: `docs/handoffs/work-to-codex/V0.2A.1-CORRECTIONS.md`.
- Work recheck: 68 backend tests and lint passed; the original independent reproduction confirms R1 fixed. Earlier independent browser/build checks passed; frontend and API shapes are unchanged by R1.
- R1 correction `42c5488`: classifier execution/outcome now comes from inference independently of human operational resolution. Work closed R1; historical snapshots remain unchanged.
- Independent verification and Human Test Packet: `docs/handoffs/work-to-chat/V0.2A.1-VERIFICATION.md`.
- Next executor: Chat, coordinate the 15–30 minute owner acceptance session on the reviewed branch using disposable data. Do not merge/deploy or begin A.2 under this review.
- No new owner decision blocks implementation under the locked Chat handoff.
- Owner acceptance started in the isolated Windows checkout but import was blocked by the local port-8001 origin restriction. The bounded correction below passed Independent Review; actual Windows retry and the remaining A.1 acceptance steps are pending. The pilot website has not been updated.

### Isolated local port-8001 correction

- Draft PR #12: `fix/a1-local-origin-8001`, targeting `milestone/v0.2a1-evidence`; neither PR is merged/deployed.
- Reviewed correction checkpoint: `9bee7291360a18012379dd4a9aa51088f1494e93` (exactly two local origins added; remote authentication and origin checks unchanged).
- Fresh Independent Review PASS, 2026-10-15: 81 backend tests, Ruff, diff checks, and separate baseline/corrected/adversarial HTTP probes. No physical Windows execution or acceptance is inferred from Linux tests.
- Formal report: `docs/handoffs/independent-review-to-chat/V0.2A.1-LOCAL-ORIGIN.md`.
- Pinned restart instructions: `docs/LOCAL-ORIGIN-8001-RESTART.md`. Use only the isolated test checkout and existing disposable test data, port8001, no proxy headers. Preserve pilot/Cloudflare.
- Next action: owner retries isolated Windows training import, then resumes the original A.1 acceptance packet. Failure returns to bounded correction/review; A.2 remains excluded.
- Management PR #11 Work findings: `docs/handoffs/work-to-chat/PR11-MANAGEMENT-REVIEW.md`; M1–M4 remain documentation issues, not an assertion that repository adoption completed.

## Important preservation requirements
Do not lose existing photos, labels, model artifacts, datasets, dealership rules, review history, or working Cloudflare pilot configuration during migrations.

## AI Project Control Center
A separate cross-project Control Center project is approved. Vehicle QC should eventually register with it using standardized project metadata and human-attention task fields, while GitHub remains the engineering source of truth. Control Center implementation is out of scope for the Vehicle QC repository itself.


## Strategic pilot direction
Vehicle QC should be treated as a focused operational-quality pilot rather than a generic AI-photo product. The business case should be proven through measurable reductions in review labor, reshoots/return visits, false alerts, and delivery uncertainty. Specialized ML expansion is evidence-gated: add one validated high-value check at a time rather than several model families in parallel.
