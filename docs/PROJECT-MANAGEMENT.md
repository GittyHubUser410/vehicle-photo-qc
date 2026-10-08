# Project Management Standard — Vehicle QC

**Management standard:** 1.2  
**Canonical standard:** AI Project Control Center `docs/PROJECT-MANAGEMENT-STANDARD.md`

Vehicle QC uses the human-bottleneck optimized workflow:

`Chat → Work → Codex → Work → Chat`

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


## Model-strength guidance
Use Management Standard 1.2 Execution Guidance for substantial handoffs and next steps:
- Difficulty: Low / Medium / High / Very High.
- Recommended Model Strength: Light / Standard / Strong / Maximum.
- Why that level is appropriate.
- Escalation conditions for using a stronger model.
- Whether owner intervention is required before proceeding.

Routine Light/Standard guidance is informational. Strong/Maximum guidance becomes an owner gate only when model choice materially affects risk, rework, or likelihood of success.

## Management governance
This project consumes the canonical management standard from `GittyHubUser410/AI-Project-Control-Center`. Project Chat/Work/Codex may propose global workflow improvements but must not redefine the canonical cross-project management standard, model-strength policy, or orchestration authority. Route those proposals to the AI Project Control Center normal Chat.


## Standard 1.2 additions
- The owner remains the accountable human; Chat/Work/Codex are executors/delegates.
- Future durable orchestration uses Project → Workflow → Run → Action identity.
- Human gates pause/resume the same run rather than creating a new ambiguous attempt.
- Autonomous external mutations require deterministic policy plus idempotency/deduplication safeguards.
- Shadow automation should precede autonomous transitions.
- Management Standard version and project-control schema version are separate.
- Repository adoption and active-conversation adoption are separate states.

This is a minor / next-handoff migration and grants no new agent authority.
