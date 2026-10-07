# ADR-003 — Independent specialized model lifecycle

**Status:** Accepted

## Context
Vehicle QC will likely use multiple specialized model families such as Shot Type, Exterior Angle, Interior Alignment, Headrest, Seat Position, Reflection, Framing, and Listing/Color Consistency. These models will accumulate data and change at different rates.

## Decision
Train, version, validate, activate, monitor, and revert each specialized model family independently unless a later deliberate multi-task/shared-backbone architecture proves superior at sufficient scale.

Retraining creates a candidate model. The active model remains unchanged until validation and deliberate activation.

## Alternatives Considered
- Retrain every model whenever any new training data arrives.
- Use a single shared model for all specialized checks from the beginning.

## Consequences
- Model metadata and Advanced Model Center views must be model-family aware.
- One photo may contribute labels to multiple model datasets without coupling their training schedules.
- Previous active versions are retained so a prior known-good model can be restored.
