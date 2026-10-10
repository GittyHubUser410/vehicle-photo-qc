# Project Management Standard — Vehicle QC

**Management standard:** 1.5.3.2  
**Canonical standard:** AI Project Control Center `docs/PROJECT-MANAGEMENT-STANDARD.md`

Vehicle QC uses the human-bottleneck optimized workflow:

`Chat → Work → Codex → Independent Review → Human Acceptance → Chat`

This local file is a project-specific snapshot. If it conflicts with a newer explicitly approved Vehicle QC product rule, the product-specific rule wins.

## Owner-attention principle
Optimize useful Vehicle QC progress per hour of owner attention. Do not repeatedly return internal engineering questions that Work can safely resolve.

Use compact Decision Packets for true product decisions and Human Test Packets for owner acceptance.

## Vehicle QC WIP defaults
- Decision Needed: max 5.
- Ready for AI: target 3–6.
- AI Implementation: max 2–3 independent tasks.
- Ready for Human Test: max 3.
- Human Test in Progress: max 1–2.

When human-test WIP is full, redirect AI toward tests, fixtures, migration rehearsal, API checks, Figma, documentation, data preparation, integration research, or future handoffs.

## Current planning horizon
- implementation-active: v0.2A Production Foundation;
- design/specification-ready next: v0.2B Management Intelligence;
- research/design-ready later: v0.2C Human Training and v0.2D integrations/model pipelines.

## Human gates
Owner input is required for:
- dealer/manager/photographer-visible behavior;
- business rules and scope;
- privacy/security expectations;
- retention/cost decisions;
- subjective UX/Figma approval;
- phone/field/real workflow testing;
- intentional milestone changes.

Work may independently resolve internal architecture, migrations, service boundaries, libraries, tests, schema mechanics, and sequencing when product behavior is unchanged.

## Preservation
Do not lose photos, labels, model artifacts, datasets, dealership rules, review history, or working Cloudflare pilot configuration.

## Durable references
Read:
- `docs/CURRENT-STATE.md`
- `docs/AI-WORKFLOW.md`
- `docs/HUMAN-BOTTLENECK-WORKFLOW.md`
- `docs/V0.2-ROADMAP.md`
- current handoff/specification and relevant ADR/C4/API/Figma references.


## Independent Review and migration boundary

For newly migrated implementation work, Independent Review is the separate formal read-only post-Codex verification role. Work remains architecture/feasibility/handoff owner and can conduct technical preflight. Review uses repository evidence, acceptance criteria, Codex report, and an independently inspected PR/checkpoint; ordinary implementation defects return to Codex for re-review.

**Existing A.1 exception:** Under the earlier approved 1.3 workflow, Work independently verified A.1 and closed R1 at `3bc23ea`. Preserve that completed review and its exact evidence; owner acceptance is still pending. The new role separation governs later explicitly migrated workflows and must not retroactively label A.1 unverified or accepted.

## Model-strength guidance

Use canonical Management Standard 1.5.3.2. Substantial handoffs place a Model Recommendation section at the bottom with a prominent **✅ NO CHANGE NEEDED** or **🔁 CHANGE RECOMMENDED** verdict at its top. Include current/recommended model, strength, task difficulty, verification diversity, escalation conditions and owner-action requirements; no legacy terminal MODEL CHANGE line.

Reasoning-strength icons: 🪶 Light, 💬 Standard, 🧠 Strong, 🧠⚡ Maximum. Copy/paste cross-chat messages show the recommended model/strength nearby, and completed handoffs include a concise Next-chat handoff note. A genuinely blocking inadequacy is raised before deep work.

Use canonical owner-facing technical guidance: 🟢 action, 🔴 replace/change only when needed, 🔵 information, 🟠 purpose, 🟣 expected/actual result, 🟡 direct instruction, 🛑 stop; task-specific PowerShell window names and plain-English technical explanations. Prefer Yes/No checks where expected results are clear.

## Management governance
This project consumes the canonical management standard from `GittyHubUser410/AI-Project-Control-Center`. Project Chat/Work/Codex may propose global workflow improvements but must not redefine the canonical cross-project management standard, model-strength policy, or orchestration authority. Route those proposals to the AI Project Control Center normal Chat.


## Preserved Standard 1.3 foundations
- The owner remains the accountable human; Chat/Work/Codex are executors/delegates.
- Future durable orchestration uses Project → Workflow → Run → Action identity.
- Human gates pause/resume the same run rather than creating a new ambiguous attempt.
- Autonomous external mutations require deterministic policy plus idempotency/deduplication safeguards.
- Shadow automation should precede autonomous transitions.
- Management Standard version and project-control schema version are separate.
- Repository adoption and active-conversation adoption are separate states.

This is a minor / next-handoff migration and grants no new agent authority.


## Owner-facing document style
For substantial owner-facing Google Docs, roadmaps, plans, research reports, or management guides, use the canonical AI Project Control Center `docs/DOCUMENT-STYLE-GUIDE.md`. Apply its professional engineering-document presentation automatically unless the owner requests another style or an external template takes precedence.

## Adoption state

This file is the **proposed repository adoption** of 1.5.3.2 until its documentation PR is accepted/merged. The active Chat and Work conversations adopt the newer instructions independently. Historical handoffs and the pilot release retain their original approved standard and authority. The project-control schema version remains independent of the management-standard version.
