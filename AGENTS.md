# AGENTS.md

Before working on Vehicle QC:

1. Read `docs/CURRENT-STATE.md`.
2. Read the role seed (`docs/CHAT-SEED.md`, `docs/WORK-SEED.md`, or `docs/INDEPENDENT-REVIEW-SEED.md`) when applicable.
3. Read `docs/PROJECT-MANAGEMENT.md`, `docs/AI-WORKFLOW.md`, and the canonical Management Standard 1.5.3.2 in `GittyHubUser410/AI-Project-Control-Center`.
4. Read the handoff named by the user/current state.
5. Read relevant ADRs under `docs/architecture/decisions/`.
6. Read `docs/architecture/C4.md` for architecture-impacting work.
7. Read `docs/API-CONTRACT.md` for API/client-boundary work.
8. Follow the role boundaries in the workflow.
9. Do not silently expand scope or reinterpret product decisions.
10. Preserve existing photos, labels, training data, model artifacts, datasets, dealership rules, review history, and remote-access configuration unless the approved handoff explicitly says otherwise.
11. If an approved Figma/FigJam design is referenced by the handoff, treat it as the visual implementation target together with the written acceptance criteria.
12. Update tests and required durable documentation when implementation changes architecture, APIs, or accepted decisions.

GitHub is the durable project record. Short chat messages should identify the repository, branch, handoff, and requested action rather than repeating the complete project history.

## Standard 1.5.3.2 adoption boundary

- New workflow: Chat → Work → Codex → Independent Review → Human Acceptance → Chat. Independent Review is read-only by default; ordinary engineering defects return to Codex for correction and re-review.
- Preserve prior milestone handoffs and their recorded verification/authority as historical evidence. A.1 at reviewed checkpoint `3bc23ea` remains Work-verified and awaiting owner acceptance; do not retrofit Independent Review into the completed R1 gate or imply acceptance.
- Substantial handoffs use the bottom Model Recommendation with ✅ NO CHANGE NEEDED / 🔁 CHANGE RECOMMENDED, canonical reasoning-strength icons and ready-to-send next-chat notes.
- Owner-facing technical steps use semantic sphere markers, named terminal windows, plain-English explanations and simple Yes/No confirmation when suitable.
- No new merge, deployment, security, data, or orchestration authority is granted by this documentation adoption.
