# Vehicle QC AI Development Workflow

## Standard loop

Chat → Work → Codex → Independent Review → Human Acceptance → Chat.

GitHub is the durable source of truth. Conversation messages should point agents to repository artifacts rather than carrying the full project history.

This project is optimized around the user's limited decision/testing time rather than around simulating a traditional human software team. See `docs/HUMAN-BOTTLENECK-WORKFLOW.md`.

## Roles

### Chat
Owns product behavior, UX, priorities, roadmap decisions, business rules, research, and Chat → Work handoffs.

### Work
Owns repository inspection, feasibility, architecture, migrations/dependencies, technical risk, sequencing, acceptance criteria, and engineering preflight.

### Independent Review

For newly migrated workflows, formally verifies Codex changes in a separate read-only review, comparing the approved scope, PR/diff, tests, evidence and prior checkpoint. Does not make product decisions or implement fixes; sends ordinary defects to Codex for correction and re-review.

### Codex
Owns scoped implementation, tests, debugging, refactors, migrations, and the Codex → Work implementation report. It must not silently expand product scope.

## Required project artifacts

- `docs/CURRENT-STATE.md` — short operational snapshot.
- `docs/V0.2-ROADMAP.md` — approved product direction.
- `docs/handoffs/` — task-specific agent interfaces as the workflow is adopted.
- `docs/architecture/C4.md` — current System Context and Container architecture.
- `docs/architecture/decisions/` — durable Architecture Decision Records.
- `docs/API-CONTRACT.md` — API stability/contract policy.
- `docs/HUMAN-BOTTLENECK-WORKFLOW.md` — queueing, WIP limits, decision packets, human-test packets, and AI parallelism rules.
- Figma/FigJam — used when UI/UX or visual architecture needs approval before implementation.
- GitHub Issues — implementation-sized work, durable technical tasks, and defects.
- GitHub Projects — execution/roadmap view when configured; it does not replace ROADMAP.md.

## Architecture decisions

Create an ADR when a technical choice materially constrains future implementation or would be important for a new developer/agent to understand. Accepted ADRs are historical records; supersede them with new ADRs rather than silently rewriting the decision.

## C4 diagrams

Maintain at least a System Context and Container diagram for substantial architecture changes. The repository version should stay text-readable (Mermaid when practical) even if a richer FigJam diagram is also maintained.

## UI / Figma rule

Use Figma for important UI/UX screens where visual ambiguity could cause implementation rework. Chat decides product intent; Work verifies feasibility; Codex implements from the engineering handoff plus the approved Figma reference. Figma is not required for routine backend changes.

## API contract rule

FastAPI's generated OpenAPI schema is the authoritative machine-readable API contract. Work must consider compatibility for client-facing changes, and Codex must update endpoints, schemas, tests, and contract behavior together.

## Human-attention rule

Only send work to the user after AI verification unless the issue genuinely requires a product decision, physical/device test, subjective UX judgment, or business acceptance. When user input is needed, package it as a compact Decision Packet or Human Test Packet. Keep a small Ready-for-AI queue so implementation can continue without repeatedly interrupting the user.

When the Ready-for-Human-Test queue is full, prioritize automation, tests, fixtures, documentation, research, Figma work, migration rehearsal, and future handoff preparation instead of producing more review debt.

## Escalation

Return to Chat for changes that materially affect user-visible behavior, UX, scope, business rules, cost, privacy/security expectations, retention, milestone priority, or intentional breaking changes.

Work may decide internal APIs, table names, libraries, migration mechanics, service boundaries, test organization, and implementation sequencing when those choices do not materially alter product behavior.

Codex may decide low-level details inside the approved engineering spec.

## Definition of done

A milestone is done only when:
1. product behavior is defined;
2. Work approves the engineering plan;
3. implementation is complete;
4. required automated checks pass;
5. Independent Review formally verifies for newly migrated workflows; prior A.1 Work verification retains its historical authority;
6. required manual acceptance checks pass;
7. a known-good checkpoint is recorded;
8. CURRENT-STATE is updated;
9. roadmap, ADR, C4, API contract, Figma references, and issues are updated when the change materially affects them.


## Model guidance and cross-chat continuation

Follow Management Standard 1.5.3.2. At the bottom of substantial handoffs, put **Model Recommendation** with a top-of-section ✅ NO CHANGE NEEDED or 🔁 CHANGE RECOMMENDED verdict, current/recommended model and reasoning strength (🪶 Light / 💬 Standard / 🧠 Strong / 🧠⚡ Maximum), task difficulty, verification diversity, escalation trigger, and owner-action requirement. Do not use the obsolete terminal `MODEL CHANGE:` line. Blocking pre-task escalation remains immediate.

Every completed handoff must supply a copy/paste **Next-chat handoff note** after its durable report. Codex → Independent Review is mandatory for newly migrated workflows.

## Durable control-plane rules

Maintain accountable human vs executor roles, Project → Workflow → Run → Action identity, human pause/resume gates, deterministic permission boundaries, idempotency/deduplication before autonomous writes, and shadow automation. No new mutation authority is granted.

## Existing A.1 checkpoint boundary

A.1 on `milestone/v0.2a1-evidence` at `3bc23ea` was independently Work-verified under its earlier authorized process; R1 is closed. It remains unaccepted, unmerged and undeployed. Do not reinterpret or rewrite its historical handoffs. A locally reproduced isolated test-port origin error is a setup/implementation finding for bounded correction; do not alter production Cloudflare settings or pilot data.

## Owner-facing technical guidance

Use the canonical 1.5.3.2 semantic markers: 🟢 action, 🔴 replacement only when actually required, 🔵 information, 🟠 purpose, 🟣 expected/actual, 🟡 direct owner instruction and 🛑 stop. Name parallel PowerShell windows by task and purpose, pair technical terms with plain-English meaning, and ask Yes/No when the expected result is unambiguous.

## Owner-facing document style
For substantial owner-facing Google Docs, roadmaps, plans, research reports, or management guides, use the canonical AI Project Control Center `docs/DOCUMENT-STYLE-GUIDE.md`. Apply its professional engineering-document presentation automatically unless the owner requests another style or an external template takes precedence.
