# Vehicle QC — Management Standard 1.8.0 G2 Adoption Review Packet

**Status:** Candidate only; not adopted/merged.  
**Canonical authority:** `GittyHubUser410/AI-Project-Control-Center` `main` at merge `d1560613884c01998ced9cd0405f6c37d98e62ee`, standard blob `80a7eb10bcd31647f6f20e4673caebf0b418986a`.  
**Vehicle QC candidate:** draft PR #11, `docs/management-1532-adoption` → `docs/v0.2-planning`.  
**Classification:** G2 consequential governance/process adoption; documentary review, distinct from runtime verification and owner acceptance.

## Scope of candidate

The candidate updates `AGENTS.md`, `docs/PROJECT-MANAGEMENT.md`, `docs/AI-WORKFLOW.md`, `docs/CHAT-SEED.md`, `docs/WORK-SEED.md`, `docs/INDEPENDENT-REVIEW-SEED.md`, `docs/CURRENT-STATE.md`, `docs/DEVELOPMENT-HANDOFF-PROCESS.md` and `docs/CODEX-HANDOFF-README.md` to apply canonical 1.8.0 to future workflows, including optional WM1–WM6 Work execution envelopes. No application code, data, cloud networking, security credential, review authority, merge or deployment permissions are changed.

The prior PR #11 preflight M1–M4 is documented at `docs/handoffs/work-to-chat/PR11-MANAGEMENT-REVIEW.md` on `fix/a1-local-origin-8001`. Candidate dispositions: M1 — updated Current State to implemented/Work-verified and owner testing still pending; M2 — Codex now returns evidence to Independent Review for new workflows; M3 — corrected stale active Codex task in the handoff README (not merely an appended routing override); M4 — governance migration identified as major/G2, not minor.

## Immutable current project facts

- v0.1 pilot remains baseline; known-good `dc56f77a6105bf9a490e0f2ff07fd7883bb6c1ca`.
- v0.2A.1 implementation PR #10, executable Work-reviewed head `d78dd5b403cf5a3e4077077afb5123992d2a38b7`; later documentation/PR checkpoint `3bc23ea19c5af356b6f380f53ac72a84d9e53f9f`; earlier Work verification passed with R1 closed.
- Port-8001 correction PR #12, formal code Independent Review PASS at `9bee7291360a18012379dd4a9aa51088f1494e93`. Actual isolated Windows owner import retry still pending.
- Human A.1 acceptance is **PENDING**, not completed; no merge/deployment/A.2 authority.
- Pilot photos, training library, model artifacts, dataset manifests, review history, dealership rules, Cloudflare tunnel/access and local-origin policy remain protected.

## WM1–WM6 compatibility

Vehicle QC can use *future optional* cohesive, multi-milestone Work envelopes after explicit suitable scope and capability checks, preserving intermediate immutable GitHub checkpoints, genuine Codex/Review role separation, dependency-local blocking, and finite closure. **No currently approved envelope** authorizes starting A.2 before the A.1 human gate. Planning, bounded research and non-blocked documentary review may continue, but no speculative migration/implementation or expanded external effect is implicit.

## Fresh 2026-10-22 G2 adverse readback and bounded corrections

Independent Governance Review of exact candidate `0eaba0dce3dd69462edce487d196f4486646a973` returned **OPEN** on three issues. The review's source identity and adverse disposition are retained; this author response does not reclassify them as independently resolved.

- **G2-01 / prior M3 OPEN:** `docs/CODEX-HANDOFF-README.md` still gave the original A.1 implementation as the live Codex task. The corrected beginning now states that original assignment is completed/historical, records the current approval gate and requires a new approved handoff for any future Codex run.
- **G2-02 OPEN:** `docs/HUMAN-BOTTLENECK-WORKFLOW.md` routed formal verification to Work. The corrected active stage assigns formal verification of newly migrated work to separate Independent Review, retaining Work preflight, bounded Codex correction and the historical A.1 exception.
- **G2-03 OPEN:** source documents attributed A.1 executed Work review to `3bc23ea`. The corrected live documents now distinguish **executed review** at `d78dd5b403cf5a3e4077077afb5123992d2a38b7` from the **later documentation publication** `3bc23ea19c5af356b6f380f53ac72a84d9e53f9f`. The historical verification report is unchanged.

The same review marked M1, M2, M4 and WM1–WM6 documentary boundaries PASS_SOURCE, while runtime, owner acceptance and exact repository adoption remain PENDING. Request a **focused independent readback** against the new exact candidate rather than restarting broad review or claiming code execution.

## Required review and acceptance

Independent Governance/Documentary Review should:
1. Verify canonical 1.8.0 blob and exact candidate head; inspect changed clauses and adjacent dependencies.
2. Recheck M1–M4 and any inconsistencies with project-local standards, role seeds and historical handoffs.
3. Confirm no A.1 gate or security/merge/deployment authority changed; verify any remaining legacy references are historical rather than live instructions.
4. Report PASS_SOURCE, adverse findings or PENDING gates explicitly, without claiming runtime enforcement from documentation.

Then Lead/owner may consider exact-artifact repository adoption. **Do not merge this PR solely because this packet exists.** After accepted integration, separately reconcile `project-control.yaml` on `main` (currently version 1.3) without changing the project-control schema version; follow its own branch/approval path. Historical handoffs retain their governing versions.

## Next-chat handoff note

Use `GittyHubUser410/vehicle-photo-qc`, draft PR #11 `docs/management-1532-adoption` targeting `docs/v0.2-planning`. Read `docs/handoffs/chat-to-independent-review/MANAGEMENT-1800-G2-REVIEW-PACKET.md`, canonical 1.8.0 at standard blob `80a7eb10bcd31647f6f20e4673caebf0b418986a`, and prior PR11 M1–M4 preflight. Perform fresh bounded G2 documentary review on the exact candidate; preserve A.1 PR #10 and port correction PR #12, pilot/Cloudflare and pending owner acceptance. Report source-anchored findings; do not merge, deploy or begin A.2.

## Model Recommendation

**✅ NO CHANGE NEEDED** — GPT-6 🧠 Strong recommended for G2 documentary review; current model/strength in receiving context unknown. High difficulty. Prefer fresh different-capable-model reviewer/context; escalate on authority/security gate or historical evidence conflict. Owner action: none until review produces exact adoption candidate.
