# Development handoff process

## Purpose

Use Chat, Work, and Codex for the tasks each is best suited to.

## Chat

Use Chat for:

- product design,
- UX decisions,
- business reasoning,
- feature prioritization,
- feasibility discussion,
- defining acceptance criteria,
- reviewing pilot feedback,
- deciding what should be built next.

Chat should update planning documents when decisions are finalized.

## Work

Use Work for broad multi-step tasks that mix research and deliverables, such as:

- competitor research,
- infrastructure comparisons,
- business proposals,
- HomeNet/DigiLot capability research,
- architecture alternatives,
- deployment planning,
- documents/reports.

Work should not be the default tool for large uncontrolled repository rewrites once the app is mature enough for Codex-driven implementation.

## Codex

Use Codex for repository-centered engineering:

- implementation,
- refactoring,
- database migrations,
- authentication,
- APIs,
- frontend changes,
- tests,
- debugging,
- reviewing diffs,
- CI fixes,
- code documentation.

## Milestone workflow

For each milestone:

1. Discuss and finalize behavior in Chat.
2. Update GitHub planning/spec files.
3. Start a Codex task on the correct repo/branch.
4. Tell Codex exactly which milestone to implement.
5. Codex reads the handoff docs first.
6. Codex implements only that milestone.
7. Codex runs automated tests.
8. User performs manual acceptance testing.
9. Fix regressions in the same milestone.
10. Commit/tag a known-good checkpoint.
11. Only then plan/implement the next milestone.

## Scope-control rule

Never give Codex a vague instruction like:

> Implement all of v0.2.

Instead:

> Read `docs/CODEX-HANDOFF-README.md` and implement `docs/V0.2A-CODEX-SPEC.md` only. Do not begin v0.2B.

## Preservation rule

Before any major migration:

- back up the complete data directory,
- record the current known-good commit,
- keep migrations additive/reversible by backup,
- never reset user data to simplify implementation.

