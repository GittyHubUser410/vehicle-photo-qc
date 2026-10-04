import { useEffect, useState } from "react";
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
import { Badge, ErrorBox, Field, Modal, Score } from "./ui";
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
}) {
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
        if (scope === "training") {
          d.photos = d.photos.filter((p) => p.training);
          d.photo_count = d.photos.length;
        }
        setData(d);
        setSelected((s) =>
          d.photos.some((p) => p.id === s) ? s : d.photos[0]?.id || "",
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
  const photo = data?.photos.find((p) => p.id === selected);
  const index = data?.photos.findIndex((p) => p.id === selected) ?? 0;
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
  const photoReviews =
    data?.reviews.filter((r) => r.photo_id === selected || !r.photo_id) || [];
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
              onClick={() => setTargets(data.photos.map((p) => p.id))}
            >
              Select all
            </button>
            <button className="button secondary" onClick={() => setTargets([])}>
              Clear selection
            </button>
          </div>
          <div className="paste-grid">
            {data.photos.map((p) => (
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
                  targets: data.photos
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
                {data.photo_count} photos
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
                ? "Label every shot type to check missing shots and sequence."
                : data.checks.required_shots === "needs_reanalysis"
                  ? "Shot types changed. Reanalyze to update required-shot checks."
                  : ""}
            </span>
          </div>
          <div className="detail-actions">
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
          {photo && (
            <div className="detail-grid">
              <div className="photo-column">
                <div className="photo-stage">
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
                  <span className="photo-position">
                    {index + 1} / {data.photos.length}
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
                      setSelected(data.photos[index - 1].id);
                      setReviewId("");
                    }}
                  >
                    <ChevronLeft />
                  </button>
                  <span title={photo.original_filename}>
                    {photo.original_filename}
                    <small>
                      {photo.width} × {photo.height} ·{" "}
                      {(photo.byte_size / 1024 / 1024).toFixed(1)} MB
                    </small>
                  </span>
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
                    disabled={index === data.photos.length - 1}
                    onClick={() => {
                      setSelected(data.photos[index + 1].id);
                      setReviewId("");
                    }}
                  >
                    <ChevronRight />
                  </button>
                </div>
                <div className="photo-filmstrip">
                  {data.photos.map((p) => (
                    <button
                      key={p.id}
                      aria-label={`View photo ${p.position}`}
                      aria-pressed={p.id === selected}
                      className={p.id === selected ? "selected" : ""}
                      onClick={() => {
                        setSelected(p.id);
                        setReviewId("");
                      }}
                    >
                      <img src={thumbnail(p.id)} alt={`Photo ${p.position}`} />
                      <span>{p.position}</span>
                      {data.issues.some((i) => i.photo_id === p.id) && <i />}
                    </button>
                  ))}
                </div>
                <details className="panel metadata">
                  <summary>Photo & vehicle details</summary>
                  <dl>
                    {Object.entries({
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
                <Field title="Shot type (human label)">
                  <select
                    value={photo.shot_type}
                    disabled={busy || pending}
                    onChange={(e) =>
                      action(`/photos/${photo.id}/shot`, "PUT", {
                        shot_type: e.target.value,
                      })
                    }
                  >
                    {config.shot_types.map((s) => (
                      <option key={s} value={s}>
                        {label(s)}
                      </option>
                    ))}
                  </select>
                </Field>
                {photo.analysis?.predicted_shot && (
                  <p className="form-note">
                    Model suggestion: {label(photo.analysis.predicted_shot)} ·{" "}
                    {Math.round((photo.analysis.confidence || 0) * 100)}%
                    confidence
                  </p>
                )}
                <button
                  className="button secondary danger-text"
                  disabled={pending || busy}
                  onClick={() => setDeleteTarget(photo.id)}
                >
                  Delete photo…
                </button>
                <h4>Detected concerns</h4>
                {data.issues
                  .filter((i) => i.photo_id === photo.id || !i.photo_id)
                  .map((i) => (
                    <div className={`issue ${i.severity}`} key={i.id}>
                      <Badge tone={i.severity === "severe" ? "danger" : "warn"}>
                        {label(i.kind)}
                      </Badge>
                      <p>{i.description}</p>
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
                      if (index < data.photos.length - 1) {
                        setSelected(data.photos[index + 1].id);
                        setReviewId("");
                      }
                    }}
                    hasNext={index < data.photos.length - 1}
                  />
                ) : (
                  <button
                    className="button secondary full"
                    disabled={busy}
                    onClick={() =>
                      action(`/photos/${photo.id}/training`, "POST")
                    }
                  >
                    <FlaskConical size={16} /> Add to Training Library
                  </button>
                )}
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
            <div className="coverage-list">
              {Object.entries(data.checks).map(([k, v]) => (
                <div key={k}>
                  <span>{label(k)}</span>
                  <Badge>{label(v)}</Badge>
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
  async function save(andNext = false) {
    setBusy(true);
    try {
      await send(`/photos/${photo.id}/training`, "PUT", {
        labels,
        eligible,
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
      <Field title="Training shot type">
        <select
          value={labels.shot_type || "unknown"}
          onChange={(e) => setLabels({ ...labels, shot_type: e.target.value })}
        >
          {config.shot_types.map((v) => (
            <option key={v} value={v}>
              {label(v)}
            </option>
          ))}
        </select>
      </Field>
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
        Uncheck to exclude this photo from future datasets. Originals and
        previous snapshots remain unchanged.
      </p>
      <div className="button-row">
        <button
          className="button primary"
          disabled={busy || !actor.trim()}
          onClick={() => save()}
        >
          <Check size={15} /> Save labels
        </button>
        {hasNext && (
          <button
            className="button secondary"
            disabled={busy || !actor.trim()}
            onClick={() => save(true)}
          >
            Save + next
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
