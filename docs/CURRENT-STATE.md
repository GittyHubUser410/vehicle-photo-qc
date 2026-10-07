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
Prepare v0.2A production foundation, then v0.2B management intelligence, v0.2C Human Training, and v0.2D integrations/specialized model pipelines.

## Required current references
- `docs/V0.2-ROADMAP.md`
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

## Next approved milestone
v0.2A — Production foundation.

## Important preservation requirements
Do not lose existing photos, labels, model artifacts, datasets, dealership rules, review history, or working Cloudflare pilot configuration during migrations.

## AI Project Control Center
A separate cross-project Control Center project is approved. Vehicle QC should eventually register with it using standardized project metadata and human-attention task fields, while GitHub remains the engineering source of truth. Control Center implementation is out of scope for the Vehicle QC repository itself.
