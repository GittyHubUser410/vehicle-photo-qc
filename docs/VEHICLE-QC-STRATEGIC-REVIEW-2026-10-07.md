# Vehicle QC Strategic Review — 2026-10-07

## Executive conclusion

Continue Vehicle QC, but make the next investment a **measured operational pilot**, not broad AI expansion.

The project has a plausible niche if it proves that dealership-specific standards, photographer correction/coaching, approval evidence, and delivery verification reduce real labor and rework. Generic scoring, upload management, or broad "AI photo checking" alone are not strong enough differentiators.

## Product/business position

Vehicle QC should be evaluated as an operational-quality workflow rather than as a generic image-enhancement or generic photo-scoring product.

Priority value propositions:
- dealer-specific standards and required sequences;
- clear exception/review handling;
- photographer feedback and correction loops;
- verifiable approval/completeness evidence;
- reliable downstream delivery evidence;
- measurable reduction in manager review labor, reshoots, return visits, and avoidable defects.

Adjacent products already cover parts of automated automotive-photo checking/enhancement, so business viability depends on workflow fit and measurable operational value.

## Immediate technical findings

### Evidence state must become explicit
Suggested or defaulted labels must not be indistinguishable from human-verified truth.

For labels/coverage used by QC, training, metrics, or model evaluation, preserve:
- value;
- evidence state such as suggested / verified / predicted;
- actor or model that supplied it;
- timestamp/revision;
- source/context when relevant.

A displayed technical score must make clear which checks actually ran and which checks were not applicable, unavailable, or unverified.

### Training defaults require care
Current flows that default labels to Good / eligible are useful for speed but can pollute model evidence if default acceptance is later treated as verified ground truth.

Defaults may remain as UI suggestions, but training/evaluation pipelines need a deliberate verified-state boundary.

### Production foundation is still necessary
The small-team pilot still needs:
- named identity;
- permission boundaries;
- durable job ownership;
- concurrency safety;
- restart/recovery;
- migration rehearsal;
- backup restoration;
- auditability.

### Integration research should begin early
Investigate the exact DigiLot vendor/workflow and HomeNet/Cox delivery options now, while keeping production integration implementation in v0.2D unless product evidence justifies reprioritization.

The project should avoid becoming a second field workflow that agents must duplicate.

## Pilot evidence to collect

Measure before/after or baseline/trend values for:
- manager review time per vehicle/shoot;
- first-pass acceptance;
- reshoot / return-visit rate;
- recurring defect categories;
- false-alert rate;
- correction rate;
- concurrent-upload reliability;
- analysis/review turnaround;
- restart/recovery behavior;
- backup restoration;
- delivery success/failure evidence;
- willingness to pay / operational value for the customer.

## ML strategy

Do not expand several specialized models at once.

Introduce one validated specialized check at a time:
1. define applicability;
2. collect verified labels;
3. establish a baseline;
4. train/evaluate candidate;
5. compare against deterministic/manual workflow;
6. activate deliberately;
7. preserve rollback;
8. measure pilot value and false alerts.

Broad multimodal/LLM use should remain an escalation path for ambiguous cases, not the default processing path.

## External-customer gate

Do not move from focused pilot to broader external customers until the project demonstrates:
- reliable isolation/permissions;
- recovery/backup behavior;
- supportable deployment;
- repeatable operational benefit;
- clear owner/customer value;
- acceptable false-alert/correction burden.

## Review limitations

This review was based on static project/repository information and planning artifacts. It did not establish:
- production-host configuration correctness;
- live-photo model accuracy;
- penetration-test security;
- real concurrent-user load capacity;
- real backup restoration;
- live DigiLot/HomeNet integration feasibility;
- willingness to pay.

Those items require explicit pilot/engineering evidence.

## Resulting roadmap direction

Preserve v0.2A–v0.2D as release families, but execute them as smaller evidence-gated checkpoints documented in `docs/VEHICLE-QC-VERSION-TIMELINE-REV2.md`.

The next checkpoint is **v0.2A.1 — verified labels, coverage, and QC evidence state**.
