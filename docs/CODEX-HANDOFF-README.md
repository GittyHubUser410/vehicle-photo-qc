# Vehicle QC v0.2 Codex handoff

## Current checkpoint — A.1 implemented, human acceptance pending

**This README is background, not an active Codex authorization.** The original implementation assignment at `docs/handoffs/work-to-codex/V0.2A.1.md` was executed on PR #10, `milestone/v0.2a1-evidence`. Work independently reviewed executable head `d78dd5b403cf5a3e4077077afb5123992d2a38b7` under the prior approved workflow; the later `3bc23ea19c5af356b6f380f53ac72a84d9e53f9f` is a documentation/PR publication checkpoint, not a second executed verification. R1 remains closed.

The bounded localhost-8001 correction PR #12 has formal Independent Review PASS at executable checkpoint `9bee7291360a18012379dd4a9aa51088f1494e93`. The isolated Windows owner retry and six-step A.1 acceptance are still **PENDING**. Neither PR #10 nor PR #12 is merged/deployed; A.2 is **not authorized**.

**Codex must not restart the original A.1 assignment.** A new Codex run requires a separate current approved Work → Codex handoff with an exact branch/checkpoint and bounded scope. The remaining overview describes historical release scope and the v0.1 baseline, not a standing executable instruction.

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



## Current workflow override — proposed Management Standard 1.8.0

For newly adopted work, the current role path is **Chat → Work → Codex → Independent Review → Human Acceptance → Chat**; Codex returns evidence to Independent Review, not directly to the owner. Work may coordinate authorized cohesive WM1–WM6 execution envelopes, but has no new direct coding/dispatch authority. Prior A.1 handoffs are immutable historical evidence. The present A.1 test is owner-acceptance pending; no A.2 implementation, merge or deployment is authorized. This section supersedes legacy role routing in this document when PR #11 is accepted.
