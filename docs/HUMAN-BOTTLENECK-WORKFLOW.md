# Human-Bottleneck-Optimized Development Workflow

## Purpose

Vehicle QC should not imitate the staffing pattern of a traditional human software team. AI implementation capacity can exceed the user's available time for product decisions, physical testing, acceptance, and field feedback.

The workflow therefore optimizes for the scarce resource: human attention.

## Core principle

**Humans steer and accept; AI prepares, implements, checks, and packages.**

AI should stay ahead of the human decision/test bottleneck without creating a large pile of unreviewed code.

## Pipeline

1. **Product Intake**
   - Chat captures an idea, defect, or pilot observation.
   - Separate product decisions from engineering details.

2. **Decision Ready**
   - AI turns unresolved product questions into a compact Decision Packet.
   - No implementation begins when a material product choice is unresolved.

3. **Ready for Work**
   - Product behavior is sufficiently decided.
   - Work can inspect the repository and create an engineering handoff.

4. **Ready for AI Implementation**
   - Work handoff is complete.
   - Required Figma/API/ADR decisions are available.
   - Acceptance tests are defined.
   - Task is small enough to implement and verify independently.

5. **AI Implementation**
   - Codex implements in an isolated branch/PR.
   - AI runs tests and performs self-review.
   - Prefer at most 2–3 concurrent implementation branches, and only when they do not touch the same architecture/data surfaces.

6. **AI Verification**
   - Work independently checks implementation, tests, migrations, preservation requirements, and acceptance criteria.
   - Failures return to Codex without consuming user attention when they can be resolved internally.

7. **Ready for Human Test**
   - Only work that has passed AI verification reaches the user.
   - AI provides a Human Test Packet containing exact steps, expected result, screenshots/logs when useful, known limitations, and rollback/recovery notes.

8. **Human Test**
   - The user tests only the highest-value ready items.
   - Failures are recorded as concise observations and routed back through Work/Codex.

9. **Accepted / Done**
   - Human-required acceptance passes.
   - Known-good checkpoint, docs, issue/project state, and architecture artifacts are updated.

## WIP limits

The human stages must be protected from backlog overload.

Recommended initial limits:
- Decision Needed: maximum 5 unresolved product decisions.
- Ready for Human Test: maximum 3 items.
- Human Test in Progress: maximum 1–2 items.
- AI Implementation: maximum 2–3 independent branches.
- AI Verification: no artificial cap, but verification should be prioritized before starting more implementation when the Human Test queue is full.

When the Human Test queue reaches its limit, AI should stop generating additional user-testable features and switch to work that reduces future human effort: automated tests, fixtures, documentation, observability, migration rehearsal, dataset preparation, Figma planning, or future handoff preparation.

## Ready queue

Maintain a small queue of 3–6 tasks that are fully specified and safe for AI to begin.

The Ready queue prevents AI idle time without allowing planning to run so far ahead that pilot feedback becomes irrelevant.

Tasks should be ordered by:
1. unblock current milestone;
2. reduce future human testing/decision load;
3. high product value;
4. low coupling to unresolved features.

## Decision Packets

AI should minimize the time required for a product decision.

A Decision Packet should contain:
- decision required;
- recommended option;
- 1–3 realistic alternatives;
- user-visible impact;
- technical/cost/schedule impact;
- what becomes blocked if no decision is made;
- whether the decision can safely be deferred.

Prefer decisions that can be answered in a few minutes rather than long exploratory conversations.

## Human Test Packets

Every item reaching the user should contain:
- what changed;
- why the user's test is needed;
- setup/prerequisites;
- exact test steps;
- expected behavior;
- what evidence to collect if it fails;
- estimated active user time;
- whether other tests can be performed in the same session;
- safe rollback/recovery instructions when relevant.

Group related tests so one PC/phone session can validate several changes without repeated setup.

## Batch human work

Human decisions and tests should be batched when practical.

Recommended rhythm for a 40-hour workweek:
- one or two short decision/review sessions during the week;
- one larger PC/phone acceptance-testing block on the weekend;
- AI planning/implementation/verification continues between those sessions.

Do not require the user to repeatedly return for small confirmations that Work can safely resolve internally.

## Parallelism rules

AI may work in parallel only when the work is truly independent.

Good parallel work:
- Figma design for a future UI while backend infrastructure is being implemented;
- documentation/ADR/C4 updates;
- test/fixture creation;
- research;
- unrelated frontend/backend issues with stable contracts.

Avoid parallel implementation when tasks:
- modify the same database schema;
- touch the same major UI area;
- depend on unresolved product behavior;
- share a migration;
- change the same API contract;
- would create difficult merges or invalidate testing.

## Reduce human QA through application legibility

Whenever repeated manual checking appears, ask whether the application can expose the evidence directly to AI.

Priorities:
- deterministic automated tests for accepted behavior;
- representative test fixtures and seeded sample data;
- browser/UI automation where reliable;
- screenshots or captured UI states for visual comparisons;
- clear structured logs;
- migration rehearsal on copied representative databases;
- API/schema tests;
- performance/queue diagnostics;
- automated data-integrity checks.

The goal is not to eliminate human acceptance. The goal is to reserve human testing for subjective UX, physical-device behavior, business correctness, and field reality.

## Speculative planning vs speculative coding

AI should plan ahead more aggressively than it codes ahead.

Safe speculation:
- research;
- architecture options;
- Figma alternatives;
- acceptance-test drafts;
- ADR candidates;
- API proposals;
- issue decomposition.

Risky speculation:
- large implementation based on an unresolved user decision;
- multiple dependent features built before the first one is field-tested;
- migrations based on assumptions.

Default rule: **keep 1 milestone implementation-active, 1 milestone design-ready, and later milestones research-ready.**

## AI fallback work when blocked by the user

When waiting on a user decision/test, AI should preferentially:
- prepare the next Work handoff;
- improve tests;
- build fixtures;
- inspect likely migration risks;
- document architecture;
- prepare Figma designs;
- research integration feasibility;
- analyze pilot data;
- prepare datasets and labeling guidance;
- clean low-risk technical debt;
- verify previous work.

AI should not create more human-review debt merely to stay busy.

## Metrics

Track:
- human decision time per issue;
- human test time per issue;
- number of items waiting for human test;
- AI-to-human rework rate;
- first-pass human acceptance rate;
- average time from Ready for AI to Ready for Human Test;
- average time waiting on human;
- manual tests converted to automated tests;
- decisions repeatedly asked because context was missing.

The main optimization target is **value delivered per hour of user attention**, not lines of code, issue count, or AI utilization.
