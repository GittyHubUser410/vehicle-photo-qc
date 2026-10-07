# ADR-001 — Shot-aware model routing

**Status:** Accepted

## Context
Vehicle QC will use multiple deterministic checks and specialized vision models. Different photo types require different checks, and running every model on every image would waste compute, increase false positives, and make results harder to explain.

## Decision
Classify/identify the shot type first, apply a confidence gate, then route the image only to the deterministic checks and specialized model families that apply to that shot. Ambiguous shot identification should be resolved before downstream routing when practical.

## Alternatives Considered
- Run every model on every photo.
- Use one large general-purpose model for all QC decisions.

## Consequences
- Shot identification becomes an important upstream dependency.
- Each model must declare applicable shot types.
- Training applicability and inference applicability should use the same routing rules.
- The architecture supports cheaper local models with LLM escalation only for ambiguous cases.
