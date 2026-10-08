# Vehicle QC v0.2 Codex handoff

## Current checkpoint override — v0.2A.1

The active next task is `docs/handoffs/work-to-codex/V0.2A.1.md` on
`docs/v0.2-planning`. Read CURRENT-STATE and that bounded handoff first.
Start implementation from the current planning ref containing that handoff, not
from the older pilot checkpoint below. The older full v0.2A specification is
background for A.2; do not implement PostgreSQL/accounts/worker redesign in A.1.
The remaining overview below describes the original release families and pilot baseline.

This folder is the source of truth for the next development cycle.

## Current code baseline

Start from commit:

`dc56f77a6105bf9a490e0f2ff07fd7883bb6c1ca`

That baseline already includes:

- React + TypeScript frontend.
- FastAPI backend.
- SQLite schema v3 with WAL/foreign keys.
- Remote access through Cloudflare Access and a named tunnel.
- Owner-bound staged remote uploads.
- Android camera capture support.
- Photo/library mobile layout fixes.
- Searchable/manageable shot types.
- Training membership controls.
- Vehicle metadata editing with optimistic revision protection.
- Database-backed shot categories.
- Dealer-specific remembered shot sequences.
- Soft-delete / trash workflows.
- Good-by-default training labels.
- Copy/paste of analysis labels without overwriting shot type.
- Banner scope rules.
- Existing backend/browser regression tests.

Do **not** rebuild the application from scratch. Preserve existing data, photos, labels, models, rule history, datasets, and Cloudflare configuration.

## Development process

Use the milestones in this order:

1. **v0.2A — Production foundation**
2. **v0.2B — Management intelligence**
3. **v0.2C — Human Training Mode**
4. **v0.2D — Integrations and operational polish**

Implement one milestone at a time. Do not begin the next milestone until the current one passes its acceptance criteria and the user has tested it.

## Files in this handoff

- [V0.2-ROADMAP.md](V0.2-ROADMAP.md) — full approved roadmap and deferred ideas.
- [V0.2A-CODEX-SPEC.md](V0.2A-CODEX-SPEC.md) — implementation scope for the first milestone.
- [V0.2A-ACCEPTANCE-TESTS.md](V0.2A-ACCEPTANCE-TESTS.md) — required validation before handoff.
- [V0.2A-MIGRATION-NOTES.md](V0.2A-MIGRATION-NOTES.md) — preservation, SQLite/PostgreSQL, rollback, and upgrade constraints.
- [V0.2-HUMAN-TRAINING-MODE.md](V0.2-HUMAN-TRAINING-MODE.md) — approved v0.2C training-mode design.
- [DEVELOPMENT-HANDOFF-PROCESS.md](DEVELOPMENT-HANDOFF-PROCESS.md) — how Chat, Work, and Codex should divide responsibilities.
- [AI-ARCHITECTURE-COMPARISON.md](AI-ARCHITECTURE-COMPARISON.md) — specialized local vision ML vs multimodal LLM vs hybrid architecture, retention, explainability, and prototype cost scaling.

## Codex instruction

When a Codex task is started, tell Codex:

> Read `docs/CODEX-HANDOFF-README.md` and all files it links before modifying code. Implement only the milestone explicitly requested. Preserve existing architecture and user data. Run the documented tests and report any deviation before expanding scope.

