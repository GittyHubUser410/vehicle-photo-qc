# Vehicle QC Version Timeline — Revision 2

## Planning principle

Preserve the established v0.2A–v0.2D release families, but split them into smaller checkpoints with explicit evidence gates.

Estimates are rolling and should be revised from actual prerequisites, test results, and owner-test capacity rather than treated as fixed calendar promises.

## v0.2A.1 — Verified labels, coverage, and QC evidence

**Goal:** make the data trustworthy enough that later metrics and ML are meaningful.

Implement/verify:
- explicit suggested / verified / predicted evidence states;
- actor/model/timestamp/revision provenance where relevant;
- distinction between UI defaults and verified training truth;
- QC/check coverage: what ran, what did not run, why, and applicability;
- score/result presentation that does not imply unavailable checks were performed;
- preservation of historical data during migration to the new evidence model;
- tests preventing suggested/default values from silently becoming verified ground truth.

**Gate:** representative existing and new records preserve evidence state correctly, and manager-visible results can explain check coverage.

## v0.2A.2 — Small-team production foundation

**Goal:** safely support the approximately ten-user pilot.

Implement/verify:
- named accounts/identity;
- roles and server-side permissions;
- PostgreSQL transition/migration rehearsal;
- safe multi-user concurrency;
- durable analysis-job ownership/queueing;
- audit trail;
- Windows startup/recovery;
- backup restoration;
- Cloudflare pilot preservation;
- migration/data-integrity checks;
- operational logs/evidence.

**Gate:** concurrent-use, restart/recovery, backup-restore, and permission tests pass with preserved pilot data.

## v0.2B.1 — Manager queue, corrections, and operational metrics

**Goal:** prove management labor savings and create clean correction evidence.

Implement/verify:
- manager-focused queue;
- correction/false-alert tracking;
- first-pass acceptance and reshoot measures;
- defect trends;
- completeness/duplicate checks where reliable;
- time-to-review / time-to-resolution where measurable;
- drill-down from metrics to affected vehicles/photos;
- concise explanation of deterministic vs ML-triggered review.

**Gate:** pilot metrics are understandable, traceable, and based on verified evidence states.

## v0.2B.2 — Pilot measurement and model diagnostics

**Goal:** determine whether Vehicle QC produces repeatable operational value and whether individual models/checks are ready to expand.

Measure:
- manager review time;
- false alerts;
- corrections;
- first-pass acceptance;
- reshoots/return visits;
- system reliability;
- model/check performance by applicable shot/dealer/context;
- disagreement and confidence behavior;
- candidate/active model comparison and rollback.

**Gate:** a written pilot evidence review decides what to continue, change, pause, or expand.

## v0.2C — Guided photography training and coaching

**Goal:** reduce onboarding/coaching load using dealer-specific visual standards.

Proceed after A/B evidence is trustworthy.

Keep:
- browser-first capture;
- reference sequences;
- guided/assisted/test modes;
- trainee results and history;
- manager coaching/review;
- dealer qualification/readiness;
- structured labels useful to future specialized checks.

**Gate:** real trainee/manager workflow shows reduced coaching effort or faster standards adoption.

## v0.2D.1 — Reliable delivery and destination verification

**Goal:** close the operational loop beyond QC.

Research begins immediately; production implementation remains here unless reprioritized.

Investigate/implement as feasible:
- exact DigiLot integration/vendor boundary;
- HomeNet/Cox delivery path;
- approved-media delivery;
- delivery acknowledgement/status;
- failure/retry evidence;
- reconciliation between approved Vehicle QC set and delivered destination.

**Gate:** a repeatable delivery path with observable success/failure, or a documented integration limitation/business decision.

## v0.2D.2 — First specialized QC model expansion

**Goal:** add one high-value specialized model/check with verified labels and measured pilot benefit.

Choose only one first model/check based on:
- available verified data;
- frequency/cost of the defect;
- realistic accuracy;
- applicability clarity;
- manager/photographer value.

Candidate families remain:
- Exterior Angle / Framing;
- Interior Alignment;
- Headrest;
- Seat Position;
- Reflection;
- Listing/Color Consistency.

**Gate:** candidate beats the baseline enough to justify activation, has rollback/provenance, and does not create unacceptable false-alert burden.

## v0.3 — Limited external-customer expansion

Only after:
- customer/dealer isolation is proven;
- permissions/recovery/backups are reliable;
- deployment/support is repeatable;
- pilot benefit is repeatable;
- customer-facing reporting/data boundaries are clear.

Likely scope:
- limited read-only dealer portal;
- dealer-group/location scoping;
- service/quality reporting;
- controlled customer onboarding;
- selected workflow/integration improvements proven in pilot.

## v1.0 — Evidence-dependent productization

Do not define v1.0 by feature count.

A v1.0 decision should require:
- repeatable operational value;
- supportable deployment/operations;
- stable customer/data boundaries;
- credible delivery/integration story;
- acceptable ML/QC error burden;
- business evidence that customers will pay enough to support the product.

## Parallel research while implementation proceeds

Allowed without expanding implementation WIP:
- DigiLot/HomeNet vendor/API/feed research;
- competitor/adjacent-workflow research;
- pilot measurement design;
- dataset/labeling guidance;
- Figma planning for next milestone;
- automated-test/fixture improvements;
- deployment/recovery rehearsal.

Plan ahead more aggressively than code ahead.
