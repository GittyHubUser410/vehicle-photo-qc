# A.1 implementation evidence

Status: Codex automated evidence, pending independent Work verification and owner acceptance.

All screenshots use generated solid-color PNG fixtures and disposable data. No pilot photos, credentials, database or model weights are included. Browser tests generate captures under ignored `app/frontend/test-results/`; these selected copies document the implementation.

- [Verified coverage](verified-coverage.png): real CPU analysis after operational confirmation and reanalysis; technical concerns, unavailable detectors and not-applicable rules are separate. Incomplete coverage does not imply failure of every completed check.
- [Legacy evidence](legacy-prediction.png): a read-only browser response fixture demonstrates legacy-unverified label badges and unknown historical coverage. Migration preservation is verified separately by backend fixtures, not inferred from this image.
- [Prediction provenance](prediction-provenance.png): the same UI fixture shows a model suggestion, confidence, model ID and run beside a legacy operational value. It is not model-accuracy evidence.
- [Generated OpenAPI](openapi.json): generated from `create_app` in a temporary directory, documenting the additive request/response contract. No application data is embedded.

Commands/results, migration/rollback evidence, acceptance mapping and the proposed Human Test Packet are in [Codex → Work](../../handoffs/codex-to-work/V0.2A.1.md).

R1 correction evidence is the deterministic `test_classifier_execution_independent_of_resolution_R1` matrix in `tests/test_evidence.py`: low-confidence/at-threshold/no-model/exception cases, each with suggested and verified operational shots. Assertions inspect persisted shoot/run check records and per-photo measurement evidence, exact execution/outcome/reason, call counts, independent resolution/provenance, unchanged technical score and immutable previous runs. Existing screenshots/OpenAPI describe unchanged UI/schema shapes; they are not proof of the corrected classifier status. Exact corrective SHA and commands/results are recorded in the return report.
