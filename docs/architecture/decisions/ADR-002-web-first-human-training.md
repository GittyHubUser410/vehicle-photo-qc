# ADR-002 — Web-first Human Training with replaceable capture client

**Status:** Accepted

## Context
Human Training needs a camera interface, but building a native Android application before validating the training workflow would add substantial scope.

## Decision
Implement the first useful Human Training experience in the existing HTTPS web application. Keep training sequences, dealership standards, reference images, annotations, trainee history, QC, accounts, and manager review separate from the capture client.

A native Android client should be introduced when browser limitations materially block advanced needs such as ARCore, real-time positioning guidance, stronger camera controls, on-device ML, automatic capture, robust offline capture, or dependable background synchronization.

## Alternatives Considered
- Build native Android before Human Training validation.
- Keep all training logic embedded in the web camera UI.

## Consequences
- v0.2C can validate Human Training without native-app scope.
- Future Android capture can reuse the same backend/domain model.
- Capture-client APIs and data contracts should be treated as replaceable interfaces.
