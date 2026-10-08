import { useEffect, useState, useRef, type CSSProperties } from "react";
import {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  FlaskConical,
  RefreshCw,
} from "lucide-react";
import { api, label, send, thumbnail, useStored, vehicleName } from "./api";
import { ShotSelect } from "./ShotSelect";
import { VehicleEditor } from "./VehicleEditor";
import { Badge, EvidenceBadge, ErrorBox, Field, Modal, Score } from "./ui";
import type {
  Config,
  Detail as ShootDetail,
  Notify,
  Photo,
  Review,
} from "./types";

export function Detail({
  id,
  initialPhoto,
  initialReview,
  scope,
  clipboard,
  onCopy,
  config,
  close,
  notify,
  changed,
  openOriginal,
}: {
  id: string;
  initialPhoto?: string;
  initialReview?: string;
  scope: "all" | "training";
  clipboard: Record<string, string> | null;
  onCopy: (labels: Record<string, string>) => void;
  config: Config;
  close: () => void;
  notify: Notify;
  changed: () => void;
  openOriginal: (photo?: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [problemOnly, setProblemOnly] = useState(false);
  const allTraining = useRef<HTMLInputElement>(null);
  const [membershipPending, setMembershipPending] = useState<{
    enabled: boolean;
    ids?: string[];
  } | null>(null);
  const [data, setData] = useState<ShootDetail | null>(null);
  const [selected, setSelected] = useState(initialPhoto || "");
  const [reviewId, setReviewId] = useState(initialReview || "");
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [targets, setTargets] = useState<string[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [banner, setBanner] = useState(false);
  const [busy, setBusy] = useState(false);
  const reload = () => {
    setRefresh((v) => v + 1);
    changed();
  };
  useEffect(() => {
    const abort = new AbortController();
    api<ShootDetail>(`/shoots/${id}`, { signal: abort.signal })
      .then((d) => {
        setData(d);
        setSelected((s) =>
          d.photos.some(
            (p) => p.id === s && (scope !== "training" || p.training),
          )
            ? s
            : d.photos.find((p) => scope !== "training" || p.training)?.id ||
              "",
        );
        setError("");
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => abort.abort();
  }, [id, refresh, scope]);
  useEffect(() => {
    if (!data || !["queued", "processing"].includes(data.status)) return;
    const timer = setTimeout(() => setRefresh((v) => v + 1), 1500);
    return () => clearTimeout(timer);
  }, [data]);
  const scopedPhotos =
    data?.photos.filter((p) => scope !== "training" || p.training) || [];
  const needsReview = (photoId: string) =>
    !!data?.reviews.some(
      (r) => !r.resolved_at && (!r.photo_id || r.photo_id === photoId),
    );
  const photos = scopedPhotos.filter((p) => !problemOnly || needsReview(p.id));
  const photo = photos.find((p) => p.id === selected) || photos[0];
  const index = photo ? photos.findIndex((p) => p.id === photo.id) : -1;
  const included = (p: Photo) =>
    membershipPending &&
    (!membershipPending.ids || membershipPending.ids.includes(p.id))
      ? membershipPending.enabled
      : !!p.training;
  const trainingCount = data?.photos.filter(included).length || 0;
  const allIncluded =
    !!data?.photos.length && trainingCount === data.photos.length;
  useEffect(() => {
    if (allTraining.current)
      allTraining.current.indeterminate = trainingCount > 0 && !allIncluded;
  }, [trainingCount, allIncluded]);
  useEffect(() => {
    const selectedButton = document.querySelector<HTMLElement>(
      ".photo-filmstrip button.selected",
    );
    const strip = selectedButton?.parentElement;
    if (selectedButton && strip) {
      const child = selectedButton.getBoundingClientRect(),
        parent = strip.getBoundingClientRect();
      if (child.left < parent.left || child.right > parent.right)
        strip.scrollLeft += child.left - parent.left;
    }
  }, [photo?.id]);
  const move = (delta: number) => {
    const next = photos[index + delta];
    if (next) {
      setSelected(next.id);
      setReviewId("");
    }
  };
  const pending = !!data && ["queued", "processing"].includes(data.status);
  async function action(path: string, method: string, body?: unknown) {
    setBusy(true);
    try {
      await send(path, method, body);
      reload();
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setBusy(false);
    }
  }
  async function setMembership(enabled: boolean, ids?: string[]) {
    setBusy(true);
    setMembershipPending({ enabled, ids });
    try {
      await send(`/shoots/${id}/training-membership`, "PUT", {
        enabled,
        photo_ids: ids,
      });
      const updated = await api<ShootDetail>(`/shoots/${id}`);
      setData(updated);
      changed();
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setMembershipPending(null);
      setBusy(false);
    }
  }
  const photoReviews =
    data?.reviews.filter((r) => r.photo_id === photo?.id || !r.photo_id) || [];
  const review =
    data?.reviews.find((r) => r.id === reviewId) ||
    photoReviews.find((r) => !r.resolved_at) ||
    photoReviews[0];
  return (
    <Modal
      title={
        data
          ? `${data.stock_number || "Vehicle shoot"} · ${vehicleName(data)}`
          : "Loading vehicle…"
      }
      onClose={close}
      wide
    >
      {editing && data && (
        <VehicleEditor
          shoot={data}
          config={config}
          notify={notify}
          close={() => setEditing(false)}
          saved={() => {
            setEditing(false);
            reload();
          }}
        />
      )}
      {pasteOpen && data && clipboard && (
        <Modal title="Paste settings" onClose={() => setPasteOpen(false)}>
          <p>
            Copy quality labels and note to selected photos. Both shot types
            stay unchanged. Pasted photos must be approved again before
            training.
          </p>
          <div className="button-row">
            <button
              className="button secondary"
              onClick={() => setTargets(scopedPhotos.map((p) => p.id))}
            >
              Select all
            </button>
            <button className="button secondary" onClick={() => setTargets([])}>
              Clear selection
            </button>
          </div>
          <div className="paste-grid">
            {scopedPhotos.map((p) => (
              <label key={p.id} className="paste-photo">
                <input
                  type="checkbox"
                  checked={targets.includes(p.id)}
                  onChange={(e) =>
                    setTargets(
                      e.target.checked
                        ? [...targets, p.id]
                        : targets.filter((id) => id !== p.id),
                    )
                  }
                />
                <img src={thumbnail(p.id)} alt="" />
                <span>
                  Photo {p.position} · {label(p.shot_type)}
                </span>
              </label>
            ))}
          </div>
          <button
            className="button primary"
            disabled={busy || !targets.length}
            onClick={async () => {
              setBusy(true);
              try {
                await send("/training/paste", "POST", {
                  labels: clipboard,
                  targets: scopedPhotos
                    .filter((p) => targets.includes(p.id))
                    .map((p) => ({
                      photo_id: p.id,
                      revision: p.training?.revision ?? null,
                    })),
                  actor: "Local reviewer",
                });
                setPasteOpen(false);
                reload();
                notify(
                  "Settings pasted. Review and approve the updated labels before training.",
                );
              } catch (e) {
                notify((e as Error).message, true);
              } finally {
                setBusy(false);
              }
            }}
          >
            Paste to {targets.length} photos
          </button>
        </Modal>
      )}
      {deleteTarget && (
        <Modal
          title={
            deleteTarget === "vehicle" ? "Delete vehicle?" : "Delete photo?"
          }
          onClose={() => setDeleteTarget(null)}
        >
          <p>
            {scope === "training"
              ? "Remove from Training photo storage. Analysis records remain available."
              : "Remove from the active library and future training."}{" "}
            Files are retained in Trash and can be restored.
          </p>
          <div className="button-row">
            <button
              className="button secondary"
              onClick={() => setDeleteTarget(null)}
            >
              Cancel
            </button>
            <button
              className="button primary"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await send(
                    deleteTarget === "vehicle"
                      ? `/shoots/${id}/trash`
                      : `/photos/${deleteTarget}/trash`,
                    "POST",
                    { scope },
                  );
                  notify("Moved to Trash.");
                  setDeleteTarget(null);
                  if (deleteTarget === "vehicle") {
                    changed();
                    close();
                  } else reload();
                } catch (e) {
                  notify((e as Error).message, true);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Move to Trash
            </button>
          </div>
        </Modal>
      )}
      {error && <ErrorBox message={error} />}
      {!data ? (
        <div className="loading">Loading shoot…</div>
      ) : (
        <>
          <div className="detail-summary">
            <div>
              <div className="eyebrow">
                {data.dealership_name} <Badge>{data.inventory_type}</Badge>
                <Badge tone={pending ? "warn" : "teal"}>
                  {label(data.status)}
                </Badge>
              </div>
              <p>
                {data.shoot_date} · {data.photographer_name} ·{" "}
                {scopedPhotos.length} photos
              </p>
              {data.note && <p className="shoot-note">{data.note}</p>}
            </div>
            <div className="score-label">
              <Score value={data.score} />
              <span>
                Provisional
                <br />
                technical score
              </span>
            </div>
          </div>
          {data.error && <ErrorBox message={data.error} />}
          <div className="notice compact">
            <AlertTriangle size={17} />
            <span>
              Technical checks are estimates. Vehicle crop and angle detection
              are not available yet.{" "}
              {data.checks.required_shots === "needs_shot_labels"
                ? "Confirm operational shot labels to check missing shots and sequence; model predictions can also supply provisional coverage."
                : data.checks.required_shots === "needs_reanalysis"
                  ? "Shot types changed. Reanalyze to update required-shot checks."
                  : ""}
            </span>
          </div>
          <div className="detail-actions">
            <button
              className="button secondary"
              disabled={busy || pending}
              onClick={() => setEditing(true)}
            >
              Edit vehicle
            </button>
            {scope === "training" && (
              <button
                className="button secondary"
                onClick={() => openOriginal(photo?.id)}
              >
                View full vehicle in Photo Library →
              </button>
            )}
            <label className="checkbox">
              <input
                ref={allTraining}
                type="checkbox"
                checked={allIncluded}
                disabled={busy || !data.photos.length}
                onChange={(e) => setMembership(e.target.checked)}
              />
              Use all photos for training
            </label>
            <button
              className="button secondary"
              disabled={pending || busy || !clipboard || !data.photos.length}
              onClick={() => {
                setTargets(photo ? [photo.id] : []);
                setPasteOpen(true);
              }}
            >
              Paste settings…
            </button>
            <button
              className="button secondary danger-text"
              disabled={pending || busy}
              onClick={() => setDeleteTarget("vehicle")}
            >
              Delete vehicle…
            </button>

            <button
              className="button secondary"
              disabled={pending || busy}
              onClick={() => action(`/shoots/${id}/reanalyze`, "POST")}
            >
              <RefreshCw size={15} />
              {pending ? "Processing…" : "Reanalyze shoot"}
            </button>
            <small>Uses the standards saved at import.</small>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={banner}
                onChange={(e) => setBanner(e.target.checked)}
              />{" "}
              Banner guide
            </label>
          </div>
          <div className="batch-tools">
            <label className="checkbox">
              <input
                type="checkbox"
                checked={problemOnly}
                onChange={(e) => {
                  setProblemOnly(e.target.checked);
                  setReviewId("");
                }}
              />
              Show only photos needing review (
              {scopedPhotos.filter((p) => needsReview(p.id)).length})
            </label>
            <span className="form-note">
              {trainingCount} of {data.photos.length} photos in training
            </span>
          </div>
          {!photos.length && (
            <p className="panel">
              {problemOnly
                ? "No photos need review in this view. Clear the filter to see all photos."
                : "No training photos selected. Use the checkbox above or open the full vehicle."}
            </p>
          )}
          {photo && (
            <div className="detail-grid">
              <div className="photo-column">
                <div
                  className="photo-stage"
                  style={
                    {
                      "--photo-ratio": photo.width / photo.height,
                    } as CSSProperties
                  }
                >
                  <img
                    src={`/api/photos/${photo.id}/original`}
                    alt={`Photo ${photo.position}: ${photo.original_filename}`}
                  />
                  {banner && photo.banner.applicable === true && (
                    <div
                      className="banner-guide"
                      style={{ height: `${photo.banner.top_fraction * 100}%` }}
                    >
                      Reserved banner area
                      <div
                        className="clearance-guide"
                        style={{
                          height: `${(photo.banner.clearance_fraction / photo.banner.top_fraction) * 100}%`,
                        }}
                      />
                    </div>
                  )}
                  <button
                    className="stage-nav previous"
                    aria-label="Previous photo on image"
                    disabled={index <= 0}
                    onClick={() => move(-1)}
                  >
                    <ChevronLeft />
                  </button>
                  <button
                    className="stage-nav next"
                    aria-label="Next photo on image"
                    disabled={index >= photos.length - 1}
                    onClick={() => move(1)}
                  >
                    <ChevronRight />
                  </button>
                  <span className="photo-position">
                    Photo {photo.position} · {index + 1} / {photos.length}
                  </span>
                </div>
                {banner && (
                  <p className="form-note">
                    {photo.banner.applicable === true
                      ? "Banner area applies to this photo."
                      : photo.banner.applicable === null
                        ? "Select a shot type to determine banner applicability."
                        : "No reserved banner area applies to this photo."}{" "}
                    Preview only; automatic vehicle-overlap detection is not
                    available yet.
                  </p>
                )}
                <div className="photo-navigation">
                  <button
                    className="icon-button"
                    aria-label="Previous photo"
                    disabled={index === 0}
                    onClick={() => {
                      move(-1);
                    }}
                  >
                    <ChevronLeft />
                  </button>
                  <span title={photo.original_filename}>
                    {photo.display_filename}
                    <small>
                      {photo.width} × {photo.height} ·{" "}
                      {(photo.byte_size / 1024 / 1024).toFixed(1)} MB
                    </small>
                  </span>
                  <a
                    className="text-button"
                    href={`/api/photos/${photo.id}/original?download=true`}
                    download
                  >
                    Download
                  </a>
                  <a
                    className="icon-button"
                    href={`/api/photos/${photo.id}/original`}
                    target="_blank"
                    rel="noreferrer"
                    aria-label="Open original photo"
                  >
                    <ExternalLink size={19} />
                  </a>
                  <button
                    className="icon-button"
                    aria-label="Next photo"
                    disabled={index >= photos.length - 1}
                    onClick={() => {
                      move(1);
                    }}
                  >
                    <ChevronRight />
                  </button>
                </div>
                <div
                  className="photo-filmstrip"
                  aria-label="Photo carousel with technical scores"
                >
                  {photos.map((p) => (
                    <button
                      key={p.id}
                      aria-label={`View photo ${p.position}`}
                      aria-pressed={p.id === photo.id}
                      className={`${p.id === photo.id ? "selected" : ""} ${needsReview(p.id) ? "needs-review" : ""}`}
                      onClick={() => {
                        setSelected(p.id);
                        setReviewId("");
                      }}
                    >
                      <b className="film-score">
                        Tech{" "}
                        {p.analysis?.score == null
                          ? "—"
                          : Math.round(p.analysis.score)}
                      </b>
                      <img src={thumbnail(p.id)} alt={`Photo ${p.position}`} />
                      <span>{p.position}</span>
                      {needsReview(p.id) && <i title="Needs review" />}
                    </button>
                  ))}
                </div>
                <details className="panel metadata">
                  <summary>Photo & vehicle details</summary>
                  <dl>
                    {Object.entries({
                      "Original filename": photo.original_filename,
                      Color: data.color || "Not entered",
                      Season: data.season,
                      Lighting: data.lighting,
                      Ground: data.ground,
                      Location: data.location,
                      ...photo.exif,
                    }).map(([k, v]) => (
                      <div key={k}>
                        <dt>{label(k)}</dt>
                        <dd>{v}</dd>
                      </div>
                    ))}
                  </dl>
                </details>
              </div>
              <aside className="photo-inspector">
                <div className="inspector-heading">
                  <h3>Photo {photo.position}</h3>
                  <Score value={photo.analysis?.score ?? null} small />
                </div>
                <ShotSelect
                  title="Shot type (human label)"
                  value={photo.shot_type}
                  options={config.shot_types}
                  disabled={busy || pending}
                  onChange={(value) =>
                    action(`/photos/${photo.id}/shot`, "PUT", {
                      shot_type: value,
                      revision: photo.shot_revision,
                    })
                  }
                />
                <EvidenceBadge evidence={photo.shot_evidence} />
                <button
                  className="button secondary"
                  disabled={busy || pending}
                  onClick={() =>
                    action(`/photos/${photo.id}/shot`, "PUT", {
                      shot_type: photo.shot_type,
                      revision: photo.shot_revision,
                      verify: true,
                    })
                  }
                >
                  Confirm operational shot
                </button>
                {photo.analysis?.predicted_shot && (
                  <p className="form-note">
                    Model suggestion: {label(photo.analysis.predicted_shot)} ·{" "}
                    {Math.round((photo.analysis.confidence || 0) * 100)}%
                    confidence · model{" "}
                    {photo.analysis.context.evidence?.prediction?.model_id ||
                      "legacy / unknown"}
                    · run {photo.analysis.run_id}
                  </p>
                )}
                <button
                  className="button secondary danger-text"
                  disabled={pending || busy}
                  onClick={() => setDeleteTarget(photo.id)}
                >
                  Delete photo…
                </button>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={included(photo)}
                    disabled={busy}
                    onChange={(e) =>
                      setMembership(e.target.checked, [photo.id])
                    }
                  />
                  Add to Training Library
                </label>
                {photo.training?.eligible && (
                  <p className="training-approved">
                    ✓ Approved for training. Detected concerns are retained
                    below; review status is separate.
                  </p>
                )}
                <h4>Detected concerns</h4>
                {data.issues
                  .filter((i) => i.photo_id === photo.id || !i.photo_id)
                  .map((i) => (
                    <div
                      className={`issue ${i.severity} ${data.reviews.some((r) => r.resolved_at && r.run_id === data.current_run_id && (r.photo_id === photo.id || !r.photo_id)) && !needsReview(photo.id) ? "resolved" : ""}`}
                      key={i.id}
                    >
                      <Badge tone={i.severity === "severe" ? "danger" : "warn"}>
                        {label(i.kind)}
                      </Badge>
                      <p>{i.description}</p>
                      {!needsReview(photo.id) &&
                        data.reviews.some(
                          (r) =>
                            r.run_id === data.current_run_id &&
                            r.resolved_at &&
                            (r.photo_id === photo.id || !r.photo_id),
                        ) && (
                          <small>
                            Review resolved ·{" "}
                            {label(
                              data.reviews.find(
                                (r) =>
                                  r.run_id === data.current_run_id &&
                                  r.resolved_at &&
                                  (r.photo_id === photo.id || !r.photo_id),
                              )?.resolution || "reviewed",
                            )}
                          </small>
                        )}
                    </div>
                  ))}
                {!data.issues.some(
                  (i) => i.photo_id === photo.id || !i.photo_id,
                ) && (
                  <p className="muted">
                    {pending
                      ? "Analysis is still processing."
                      : "No concerns from the completed checks."}
                  </p>
                )}
                {photo.analysis && (
                  <details className="metrics">
                    <summary>Technical measurements</summary>
                    <dl>
                      {Object.entries(photo.analysis.metrics).map(
                        ([key, val]) => (
                          <div key={key}>
                            <dt>{label(key)}</dt>
                            <dd>
                              {key === "sharpness"
                                ? val.toFixed(1)
                                : `${(val * 100).toFixed(1)}%`}
                            </dd>
                          </div>
                        ),
                      )}
                    </dl>
                  </details>
                )}
                {photo.training ? (
                  <TrainingEditor
                    key={`${photo.id}:${photo.training.revision}`}
                    photo={photo}
                    config={config}
                    notify={notify}
                    saved={reload}
                    onCopy={onCopy}
                    next={() => {
                      if (index < photos.length - 1) {
                        setSelected(photos[index + 1].id);
                        setReviewId("");
                      }
                    }}
                    hasNext={index < photos.length - 1}
                  />
                ) : null}
              </aside>
            </div>
          )}
          {!!data.reviews.length && (
            <section className="panel review-work">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">REVIEW & FOLLOW-UP</span>
                  <h2>Review history</h2>
                </div>
                <select
                  aria-label="Choose review item"
                  value={review?.id || ""}
                  onChange={(e) => {
                    setReviewId(e.target.value);
                    const r = data.reviews.find((r) => r.id === e.target.value);
                    if (r?.photo_id) setSelected(r.photo_id);
                  }}
                >
                  <option value="">Choose an item</option>
                  {data.reviews.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.photo_id
                        ? `Photo ${data.photos.find((p) => p.id === r.photo_id)?.position}`
                        : "Whole shoot"}{" "}
                      · {r.resolved_at ? "Resolved" : "Open"} ·{" "}
                      {r.created_at.slice(0, 10)}
                    </option>
                  ))}
                </select>
              </div>
              {review && (
                <ReviewEditor
                  key={`${review.id}:${review.resolved_at}`}
                  review={review}
                  notify={notify}
                  saved={reload}
                />
              )}
            </section>
          )}
          <details className="panel history">
            <summary>Analysis coverage & history</summary>
            <p className="form-note">
              Technical baseline score · QC coverage{" "}
              {label(data.qc_evidence.coverage)} ·{" "}
              {label(data.qc_evidence.freshness)}.
              {data.qc_evidence.freshness === "stale" &&
                " Shot evidence changed; reanalyze before using current coverage."}
              {data.qc_evidence.evidence_schema_version === 0 &&
                " Historical evidence is unknown; legacy statuses do not establish coverage."}{" "}
              Complete coverage describes execution, not approval or passing
              outcomes.
            </p>
            <div className="coverage-list">
              {data.qc_evidence.checks.map((c, index) => (
                <div key={index}>
                  <span>
                    {c.photo_id
                      ? `Photo ${data.photos.find((p) => p.id === c.photo_id)?.position} · `
                      : ""}
                    {label(c.check_id)}
                  </span>
                  <span>
                    {label(c.applicability)} · {label(c.execution)} ·{" "}
                    {label(c.outcome)}
                    <br />
                    <small>{label(c.reason_code)}</small>
                  </span>
                </div>
              ))}
            </div>
            <p className="form-note">
              Standards: dealer version{" "}
              {data.policy.dealer_version ?? "General QC"} · group version{" "}
              {data.policy.group_version ?? "none"}. Each run retains its own
              rules and measurements.
            </p>
            {data.runs.map((r) => (
              <p className="form-note" key={r.id}>
                {new Date(r.created_at).toLocaleString()} · {r.pipeline_version}{" "}
                · {r.status}
              </p>
            ))}
          </details>
        </>
      )}
    </Modal>
  );
}

function TrainingEditor({
  photo,
  config,
  notify,
  saved,
  next,
  hasNext,
  onCopy,
}: {
  photo: Photo;
  config: Config;
  notify: Notify;
  saved: () => void;
  next: () => void;
  hasNext: boolean;
  onCopy: (labels: Record<string, string>) => void;
}) {
  const [labels, setLabels] = useState<Record<string, string>>({
    shot_type: photo.shot_type,
    ...photo.training!.labels,
  });
  const [eligible, setEligible] = useState(photo.training!.eligible);
  const [busy, setBusy] = useState(false);
  const [actor, setActor] = useStored("qc:reviewer", "Local reviewer", true);
  const fields = [
    "shot_type",
    "angle",
    "blur",
    "crop",
    "exposure",
    "saturation",
    "framing",
    "overall",
  ];
  const [selectedFields, setSelectedFields] = useState<string[]>(fields);
  async function save(andNext = false, verify = false) {
    setBusy(true);
    try {
      await send(`/photos/${photo.id}/training`, "PUT", {
        labels,
        eligible,
        verify_fields: verify ? selectedFields : [],
        revision: photo.training!.revision,
        actor,
      });
      notify("Training labels saved.");
      saved();
      if (andNext) next();
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="training-editor">
      <div className="inline">
        <FlaskConical size={17} />
        <h4>Training labels</h4>
      </div>
      <button className="button secondary" onClick={() => onCopy(labels)}>
        Copy Settings
      </button>
      <ShotSelect
        title="Training shot type"
        value={labels.shot_type || "unknown"}
        options={config.shot_types}
        onChange={(value) => setLabels({ ...labels, shot_type: value })}
      />
      <div className="label-grid">
        {[
          "angle",
          "blur",
          "crop",
          "exposure",
          "saturation",
          "framing",
          "overall",
        ].map((key) => (
          <Field key={key} title={label(key)}>
            <select
              value={labels[key] || "unknown"}
              onChange={(e) => setLabels({ ...labels, [key]: e.target.value })}
            >
              {(key === "angle"
                ? ["unknown", "good", "too_front", "too_rear", "other_bad"]
                : key === "overall"
                  ? ["unknown", "good", "borderline", "bad"]
                  : ["unknown", "good", "bad"]
              ).map((v) => (
                <option key={v} value={v}>
                  {label(v)}
                </option>
              ))}
            </select>
          </Field>
        ))}
      </div>
      <Field title="Label note">
        <textarea
          rows={2}
          maxLength={2000}
          value={labels.note || ""}
          onChange={(e) => setLabels({ ...labels, note: e.target.value })}
        />
      </Field>
      <Field title="Labeled by">
        <input
          value={actor}
          maxLength={150}
          onChange={(e) => setActor(e.target.value)}
        />
      </Field>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={eligible}
          onChange={(e) => setEligible(e.target.checked)}
        />{" "}
        Approved for training
      </label>
      <p className="form-note">
        {photo.training!.exportable
          ? "Exportable verified shot label."
          : `Not exportable: ${photo.training!.exclusion_reasons.map(label).join(", ")}.`}{" "}
        New training photos start approved. Approval is separate from
        verification. Explicitly verify the reviewed shot label before export.
        Uncheck to exclude this photo from future datasets. Originals and
        previous snapshots remain unchanged.
      </p>
      <fieldset>
        <legend>Fields reviewed for verification</legend>
        {fields.map((key) => (
          <label className="checkbox" key={key}>
            <input
              type="checkbox"
              checked={selectedFields.includes(key)}
              onChange={(e) =>
                setSelectedFields(
                  e.target.checked
                    ? [...selectedFields, key]
                    : selectedFields.filter((k) => k !== key),
                )
              }
            />
            {label(key)}{" "}
            <EvidenceBadge evidence={photo.training!.label_evidence[key]} />
          </label>
        ))}
      </fieldset>
      <div className="button-row">
        <button
          className="button primary"
          disabled={busy || !actor.trim()}
          onClick={() => save()}
        >
          <Check size={15} /> Save labels
        </button>
        <button
          className="button primary"
          disabled={busy || !actor.trim() || !selectedFields.length}
          onClick={() => save(false, true)}
        >
          Verify selected labels
        </button>
        {hasNext && (
          <button
            className="button secondary"
            disabled={busy || !actor.trim() || !selectedFields.length}
            onClick={() => save(true, true)}
          >
            Verify + next
          </button>
        )}
      </div>
    </div>
  );
}

function ReviewEditor({
  review,
  notify,
  saved,
}: {
  review: Review;
  notify: Notify;
  saved: () => void;
}) {
  const [note, setNote] = useState(review.note);
  const [resolution, setResolution] = useState(review.resolution || "accepted");
  const [busy, setBusy] = useState(false);
  const [actor, setActor] = useStored("qc:reviewer", "Local reviewer", true);
  async function act(action: string) {
    setBusy(true);
    try {
      await send(`/reviews/${review.id}`, "PATCH", {
        action,
        note,
        actor,
        resolution,
      });
      notify(
        action === "resolve"
          ? "Review resolved. The photo remains in the library."
          : action === "reopen"
            ? "Review reopened."
            : "Reviewer note saved.",
      );
      saved();
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div>
      <div className="inline">
        <Badge tone={review.resolved_at ? "teal" : "warn"}>
          {review.resolved_at ? "Resolved" : "Open"}
        </Badge>
        <span>{review.reason}</span>
      </div>
      <div className="review-form">
        <Field title="Reviewer note">
          <textarea
            value={note}
            rows={3}
            maxLength={2000}
            onChange={(e) => setNote(e.target.value)}
            placeholder="What did you find? Does the photographer need to follow up?"
          />
        </Field>
        <div>
          <Field title="Reviewer">
            <input
              value={actor}
              maxLength={150}
              onChange={(e) => setActor(e.target.value)}
            />
          </Field>
          <Field title="Resolution">
            <select
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
            >
              {["accepted", "reshoot_requested", "false_positive", "other"].map(
                (v) => (
                  <option key={v} value={v}>
                    {label(v)}
                  </option>
                ),
              )}
            </select>
          </Field>
        </div>
      </div>
      <div className="button-row">
        <button
          className="button secondary"
          disabled={busy || !actor.trim()}
          onClick={() => act("note")}
        >
          Save note
        </button>
        <button
          className="button primary"
          disabled={busy || !actor.trim()}
          onClick={() => act(review.resolved_at ? "reopen" : "resolve")}
        >
          <Check size={16} />
          {review.resolved_at ? "Reopen review" : "Resolve / remove from queue"}
        </button>
      </div>
      {!!review.events?.length && (
        <details className="review-events">
          <summary>Activity history</summary>
          {review.events.map((e) => (
            <p key={e.id}>
              <strong>{label(e.action)}</strong> · {e.actor} ·{" "}
              {new Date(e.created_at).toLocaleString()}
              {e.note && <span> — {e.note}</span>}
            </p>
          ))}
        </details>
      )}
    </div>
  );
}
