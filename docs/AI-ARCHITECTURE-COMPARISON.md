# Vehicle QC AI architecture comparison: local vision ML vs multimodal LLM vs hybrid

## Executive recommendation

For Vehicle QC, the best long-term direction is **hybrid**:

1. deterministic image checks for objective measurements,
2. specialized local vision models for high-volume repeatable classification,
3. dealership/business rules,
4. embeddings/uncertainty to identify unusual cases,
5. multimodal LLM escalation only for ambiguous cases, semantic explanation, or manager assistance,
6. human manager review for the remaining exceptions.

This keeps routine cost and latency low while preserving the flexibility of a multimodal LLM where it adds real value.

## Current specialized local model

The current learned model is a transfer-learned **ResNet18 shot-type classifier**. The pretrained backbone is frozen and a new classification head is trained on approved Vehicle QC examples.

Current learned responsibility:
- shot-type classification.

Current non-ML / deterministic checks:
- sharpness/blur measurements,
- exposure/clipping,
- saturation,
- rule-based required-shot and sequence checks.

Current model does not yet learn:
- crop/framing quality,
- angle acceptability,
- plastic/interior-preparation defects,
- complete dealership quality.

Torchvision's standard ResNet18 has about 11.7 million parameters, about 1.81 GFLOPS per standard inference, and a roughly 44.7 MB pretrained weight file. Source: https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.resnet18.html

## Architecture A — specialized locally trained vision model

### How it works

Vehicle QC keeps labeled examples, exports a frozen dataset, trains a model for one defined task, validates it, and activates a known model version.

Examples of future specialized models:
- shot type,
- crop/framing,
- exterior angle,
- plastic left inside,
- dashboard/interior preparation,
- banner/overlay issues.

### Strengths

- Very low marginal cost per photo after training.
- Can run locally and continue working without external AI API availability.
- Fast and consistent for repetitive tasks.
- Strong privacy/control over dealership photos.
- Model version, dataset and labels are under Vehicle QC control.
- Easy to batch thousands of photos.
- Predictable output schema.
- Well suited to high-volume production.

### Weaknesses

- Needs labeled examples.
- Each new task may require new data/model work.
- Can perform poorly when the real-world data differs from training.
- Does not naturally explain itself in human language.
- Bad labels can become embedded in model weights until retraining.
- Model confidence is not automatically a calibrated probability of correctness.

### Ongoing upkeep

Main costs are not per-photo API fees. They are:
- labeling/manager review time,
- retaining useful training/reference data,
- occasional retraining,
- model validation,
- local electricity/storage,
- engineering/maintenance.

For the existing pilot PC, the marginal compute cost of ResNet18-style inference is expected to remain very small relative to labor and storage. The app currently performs runtime classification on CPU; GPU time is mainly useful for training.

## Architecture B — multimodal LLM vision for every photo

### How it works

Each photo is sent to a general-purpose multimodal model together with a prompt, dealership standards and desired output format. The model returns classifications and/or natural-language reasoning.

Possible requests:
- "Is the whole vehicle framed correctly?"
- "What is wrong with this interior photo?"
- "Compare this photo to this dealership's standard."
- "Explain why this should be reviewed."

### Strengths

- Can handle new semantic questions without collecting a dedicated dataset first.
- Excellent natural-language explanations.
- Can reason across an image plus written dealership rules.
- Faster to prototype new quality concepts.
- Useful for unusual cases that a narrow classifier has not learned.
- Can compare multiple pieces of context in one request.

### Weaknesses

- Every analyzed photo has a recurring API cost.
- Usually higher latency than a small local classifier.
- Requires network/API availability.
- Results can vary more than a purpose-built classifier.
- High-volume costs grow approximately linearly with photo count.
- Requires careful output validation and monitoring.
- Exact training provenance is not under the application's control in the same way as a locally trained model.
- Sending every production image to an external service may require additional privacy/vendor review.

## Architecture C — hybrid

### Typical pipeline

Photo
→ deterministic technical checks
→ local specialized models
→ dealership rules
→ confidence / embedding / anomaly check
→ only uncertain or high-value cases sent to multimodal LLM
→ manager review if still unresolved

### Strengths

- Keeps cheap/repetitive work local.
- Uses LLM reasoning only where it adds value.
- Natural-language explanation can be added without paying for every image.
- Can gradually replace LLM escalations with specialized models as training data accumulates.
- Provides graceful prototyping: test a new quality concept with an LLM, then decide whether it deserves a dedicated local model.

### Weaknesses

- More architecture to maintain.
- Requires careful routing logic.
- Managers must know whether a decision came from a rule, local model, LLM, or combination.
- Need versioning for both local models and prompts/model-provider configurations.

## Explain / False Positive feature

The first explanation feature should not claim that one training image caused a precise percentage of a neural-network prediction.

Recommended v1:
- show which subsystem triggered review,
- show model version and confidence,
- generate/query the reviewed image's embedding,
- retrieve the nearest approved training examples,
- show similarity and neighbor rank,
- show labels/provenance/full image,
- let authorized managers correct or exclude examples,
- record false-positive feedback.

Later:
- Grad-CAM / feature attribution,
- approximate influence methods,
- mislabeled/outlier suggestions,
- training-cluster diagnostics.

## Training-image retention

A trained neural network stores learned weights, not recoverable copies of its training images.

Therefore, if an original photo is deleted after an ordinary 60–90 day operational retention period, the active model still works, but the manager can no longer visually inspect that training example unless Vehicle QC retained a separate training/reference copy.

Recommended policy:
- ordinary operational originals: normal retention policy,
- approved training/reference examples: retain a dedicated ML/reference copy while used by active/historical datasets/models,
- optionally downsize training/reference copies instead of retaining full-resolution originals,
- retain labels, image hash, dataset/model provenance and embedding.

## Prototype cost assumptions

The figures below are **planning estimates**, not guaranteed bills.

Assumptions:
- 22 processing days per month.
- Typical LLM analysis image standardized around 1024 × 1024 for cost modeling.
- Image input estimate: about 1,229 billable image tokens for a 1024 × 1024 image on current 1.2×-multiplier GPT vision models.
- Additional prompt: 300 text input tokens/photo.
- Result: 120 output tokens/photo.
- Standard API pricing used for examples:
  - GPT-5.6 Luna: $0.20/M input, $1.20/M output.
  - GPT-5.6 Terra: $2/M input, $12/M output.
  - GPT-5.6 Sol: $4/M input, $20/M output.
- Approximate calculated per-photo cost:
  - Luna: $0.00045/photo.
  - Terra: $0.00450/photo.
  - Sol: $0.00852/photo.
- Hybrid example sends only 5% of photos to Terra.
- These figures exclude extra prompt context, retries, tool calls, storage, networking, taxes, regional uplift, and engineering labor.
- API prices can change; re-check before production budgeting.

Sources:
- https://developers.openai.com/api/docs/guides/image-cost-calculator
- https://developers.openai.com/api/docs/pricing
- https://developers.openai.com/api/docs/guides/images-vision

## Estimated monthly API cost by prototype volume

| Photos/day | Local specialized model | LLM-only Luna | LLM-only Terra | LLM-only Sol | Hybrid: local + 5% Terra |
|---:|---:|---:|---:|---:|---:|
| 100 | ~$0 API | ~$0.99 | ~$9.90 | ~$18.74 | ~$0.49 |
| 500 | ~$0 API | ~$4.95 | ~$49.48 | ~$93.68 | ~$2.47 |
| 1,000 | ~$0 API | ~$9.90 | ~$98.96 | ~$187.35 | ~$4.95 |
| 5,000 | ~$0 API | ~$49.48 | ~$494.78 | ~$936.76 | ~$24.74 |
| 20,000 | ~$0 API | ~$197.91 | ~$1,979.12 | ~$3,747.04 | ~$98.96 |

These are API-only numbers. They are useful for seeing scaling behavior, not for estimating total business operating expense.

## Local-model upkeep cost during prototype

Because the user already owns the prototype PC/GPU, the local model has no meaningful external per-photo fee.

Practical prototype cost categories:
- inference electricity: usually minor for a small model,
- occasional GPU retraining: minor electricity cost but potentially substantial human labeling/review time,
- SSD/HDD storage for retained training examples,
- backup storage,
- engineering/test time.

A reasonable planning treatment during the prototype is:
- API charge: approximately $0/photo,
- marginal compute/electricity: low enough to treat as a small monthly infrastructure overhead,
- labor/data quality: dominant upkeep cost.

If the project later uses dedicated hosted GPUs, those costs should be modeled separately from this prototype comparison.

## Cost interpretation

### Early prototype — tens to hundreds of photos/day
LLM-only analysis may be financially trivial and can be useful for rapid experiments. The major question is accuracy/consistency, not API cost.

### Active pilot — hundreds to a few thousand/day
Local specialized models become increasingly attractive for routine checks. LLM-only remains affordable with low-cost models but may create unnecessary variability and dependency.

### Large pilot / near-production — several thousand to 20,000+/day
A hybrid approach becomes especially compelling. A specialized local model can process every photo, while only uncertain cases incur LLM cost.

## Recommended evolution for Vehicle QC

### Current / v0.1
- deterministic technical checks,
- local ResNet18 shot classifier,
- humans review semantic/ambiguous quality issues.

### v0.2A
- strengthen model/dataset provenance,
- prepare embedding storage/search architecture,
- preserve training-reference retention metadata,
- no major explanation UI yet.

### v0.2B
- implement Explain / False Positive v1,
- nearest training examples,
- false-positive feedback,
- training-example correction/exclusion,
- manager analytics.

### v0.2C
- reuse reference/example infrastructure for Human Training Mode,
- connect trainee outcomes with QC and manager coaching,
- optionally experiment with LLM explanations on difficult training/QC examples.

### v0.3+
- specialized models for framing/angle/interior issues as data supports them,
- feature-attribution heatmaps,
- automatic dataset-cleaning suggestions,
- uncertain-case LLM escalation,
- compare LLM escalations against human outcomes to decide which tasks should become dedicated local models.

### Long term
Default to hybrid:
- deterministic checks where rules are objective,
- local models for repetitive learned tasks,
- LLMs for ambiguity/explanation/novel semantic reasoning,
- human review for high-impact uncertainty.

