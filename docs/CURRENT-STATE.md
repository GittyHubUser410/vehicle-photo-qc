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
New milestones: Chat → Work → Codex → Independent Review → Human Acceptance → Chat (canonical 1.8.0). Existing A.1 Work verification remains valid under its previously approved standard.

GitHub Issues should track implementation-sized work. The v0.2 GitHub Project is the execution view. Important UI-heavy work should have an approved Figma/FigJam reference before implementation.

Development is optimized around the user's decision/testing capacity. Maintain a small Ready-for-AI queue, limit concurrent independent implementation work, cap the Ready-for-Human-Test queue, and send the user compact Decision Packets / Human Test Packets rather than repeated low-level interruptions.

## Next approved checkpoint
**v0.2A.1 — Verified labels, coverage, and QC evidence.**

Do not treat suggested/defaulted labels as verified ground truth. Manager-visible QC must distinguish what was checked, what was not checked, applicability, and evidence/provenance state.

After A.1 passes, continue to **v0.2A.2 — Small-team production foundation**.

### A.1 verified engineering state / pending owner action

- A.1 implementation PR #10: `milestone/v0.2a1-evidence` at `3bc23ea19c5af356b6f380f53ac72a84d9e53f9f`, open/unmerged. Earlier Work independent verification closed R1 under the then-governing 1.3 workflow; this historical gate remains valid.
- Isolated localhost:8001 correction PR #12: `fix/a1-local-origin-8001`; executable Independent Review **PASS** at exact code commit `9bee7291360a18012379dd4a9aa51088f1494e93` (2026-10-15). Review report: `docs/handoffs/independent-review-to-chat/V0.2A.1-LOCAL-ORIGIN.md`; restart instructions: `docs/LOCAL-ORIGIN-8001-RESTART.md` on the correction branch.
- Local Windows owner upload retry and remaining six-step A.1 Human Test Packet are **PENDING**, not PASS; no production or physical Windows assertion follows from the Linux/ASGI review.
- A.1 is not accepted, merged, deployed or a newly recorded known-good checkpoint. A.2 remains unauthorized.

## Important preservation requirements
Do not lose existing photos, labels, model artifacts, datasets, dealership rules, review history, or working Cloudflare pilot configuration during migrations.

## AI Project Control Center
A separate cross-project Control Center project is approved. Vehicle QC should eventually register with it using standardized project metadata and human-attention task fields, while GitHub remains the engineering source of truth. Control Center implementation is out of scope for the Vehicle QC repository itself.


## Strategic pilot direction
Vehicle QC should be treated as a focused operational-quality pilot rather than a generic AI-photo product. The business case should be proven through measurable reductions in review labor, reshoots/return visits, false alerts, and delivery uncertainty. Specialized ML expansion is evidence-gated: add one validated high-value check at a time rather than several model families in parallel.



## Management adoption — draft G2 candidate

This branch contains a proposed adoption of canonical Management Standard 1.8.0, verified Git blob `80a7eb10bcd31647f6f20e4673caebf0b418986a`, approved canonical merge `d1560613884c01998ced9cd0405f6c37d98e62ee`. The active Lead conversation adopted 1.8.0 for compatible coordination; repository adoption remains subject to draft PR #11 independent G2 documentary review and exact owner approval. The root `project-control.yaml` on `main` remains version 1.3 until intentional reconciliation. WM1–WM6 are optional execution preferences and do not preauthorize A.2 or a blanket multi-milestone run.

Prior PR #11 Work preflight M1–M4 is documented at `docs/handoffs/work-to-chat/PR11-MANAGEMENT-REVIEW.md` on the correction branch; this candidate addresses the known stale-state, routing, process-reference and migration-severity issues and still requires independent readback.
