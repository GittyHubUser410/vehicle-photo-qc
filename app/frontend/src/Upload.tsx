import { useEffect, useRef, useState } from "react";
import {
  UploadCloud,
  Plus,
  X,
  ArrowLeft,
  ArrowRight,
  Camera,
  Check,
  GripVertical,
} from "lucide-react";
import { api, label, localDate, uploadPhotos, useStored } from "./api";
import { ShotSelect } from "./ShotSelect";
import { ErrorBox, Field } from "./ui";
import type { Config, Notify, OpenDetail } from "./types";

type Picked = { id: string; file: File; url: string; shot?: string };
export function Upload({
  config,
  active = true,
  training = false,
  notify,
  done,
}: {
  config: Config;
  active?: boolean;
  training?: boolean;
  notify: Notify;
  done: OpenDetail;
}) {
  const [dealer, setDealer] = useStored("qc:last-dealer", "", true);
  const [photographer, setPhotographer] = useStored(
    "qc:last-photographer",
    "",
    true,
  );
  const [inventory, setInventory] = useStored(
    "qc:last-inventory",
    "used",
    true,
  );
  const [mode, setMode] = useState("dealership");
  const blank = () => ({
    stock_number: "",
    year: "",
    make: "",
    model: "",
    trim: "",
    color: "",
    shoot_date: localDate(),
    note: "",
    source: "",
    season: "",
    lighting: "unknown",
    ground: "unknown",
    location: "unknown",
  });
  const [form, setForm] = useState(blank);
  const [photos, setPhotos] = useState<Picked[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [suggestion, setSuggestion] = useState<{
    sequence: string[];
    source: string;
  }>({ sequence: [], source: "" });
  const [sequenceBusy, setSequenceBusy] = useState(false);
  const [sequenceVersion, setSequenceVersion] = useState(0);
  useEffect(() => {
    if (!active) return;
    const abort = new AbortController();
    setSequenceBusy(true);
    api<{ sequence: string[]; source: string }>(
      `/sequence?${new URLSearchParams({ dealership_id: mode === "dealership" ? dealer : "", inventory_type: inventory || "used" })}`,
      { signal: abort.signal },
    )
      .then(setSuggestion)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => {
        if (!abort.signal.aborted) setSequenceBusy(false);
      });
    return () => abort.abort();
  }, [active, dealer, inventory, mode, config, sequenceVersion]);
  const shotAt = (p: Picked, i: number) =>
    p.shot ?? suggestion.sequence[i] ?? "unknown";
  function removeSelected() {
    photos
      .filter((p) => selectedIds.includes(p.id))
      .forEach((p) => URL.revokeObjectURL(p.url));
    setPhotos((prev) => prev.filter((p) => !selectedIds.includes(p.id)));
    setSelectedIds([]);
  }
  const photosRef = useRef(photos);
  photosRef.current = photos;
  const input = useRef<HTMLInputElement>(null);
  const camera = useRef<HTMLInputElement>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  useEffect(
    () => () => photosRef.current.forEach((p) => URL.revokeObjectURL(p.url)),
    [],
  );
  const update = (key: keyof typeof form, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));
  function pick(files: FileList | File[] | null) {
    if (!files || busy) return;
    const additions = Array.from(files);
    if (photos.length + additions.length > 200)
      return setError("A shoot can contain up to 200 photos.");
    if (additions.some((f) => !/\.(jpe?g|png|webp)$/i.test(f.name)))
      return setError(
        "Use JPEG, PNG, or WebP. Export HEIC photos as JPEG before uploading.",
      );
    if (additions.some((f) => f.size > 25 * 1024 * 1024))
      return setError("Each photo must be 25 MB or smaller.");
    if (
      [...photos.map((p) => p.file), ...additions].reduce(
        (s, f) => s + f.size,
        0,
      ) >
      1024 ** 3
    )
      return setError("A shoot must be 1 GB or smaller.");
    setError("");
    setPhotos((prev) => [
      ...prev,
      ...additions.map((file) => ({
        file,
        id: crypto.randomUUID(),
        url: URL.createObjectURL(file),
      })),
    ]);
  }
  function move(from: number, to: number) {
    if (busy || from === to || from < 0 || to < 0 || to >= photos.length)
      return;
    setPhotos((prev) => {
      const next = [...prev];
      next.splice(to, 0, next.splice(from, 1)[0]);
      return next;
    });
  }
  function remove(id: string) {
    const p = photos.find((p) => p.id === id);
    if (p) URL.revokeObjectURL(p.url);
    setPhotos((prev) => prev.filter((p) => p.id !== id));
    setSelectedIds((prev) => prev.filter((x) => x !== id));
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!photos.length) return setError("Select at least one photo.");
    setBusy(true);
    setError("");
    setProgress(0);
    try {
      const result = await uploadPhotos(
        {
          ...form,
          shot_types: photos.map(shotAt),
          year: form.year ? Number(form.year) : null,
          season: form.season || null,
          dealership_id: mode === "dealership" ? dealer || null : null,
          photographer_id: photographer || null,
          inventory_type: inventory,
          mode,
          purpose: training ? "training" : "evaluation",
          source:
            mode === "general" && training
              ? form.source || "Stage Now"
              : form.source,
        },
        photos.map((p) => p.file),
        setProgress,
      );
      photos.forEach((p) => URL.revokeObjectURL(p.url));
      setPhotos([]);
      setSelectedIds([]);
      setSequenceVersion((v) => v + 1);
      setForm(blank());
      notify(
        training
          ? "Training photos imported. Label and approve them when ready."
          : "Photos imported. Technical analysis is queued.",
      );
      done(result.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const retained = (
    title: string,
    value: string,
    setter: (v: string) => void,
    options: { id: string; name: string }[],
    required = false,
  ) => (
    <Field title={title} hint="Remembers your last selection">
      <div className="clear-field">
        <select
          aria-label={title}
          value={value}
          onChange={(e) => setter(e.target.value)}
          required={required}
        >
          <option value="">Select {title.toLowerCase()}</option>
          {options.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          title={`Clear ${title.toLowerCase()}`}
          aria-label={`Clear ${title.toLowerCase()}`}
          onClick={() => setter("")}
        >
          <X size={15} />
        </button>
      </div>
    </Field>
  );
  return (
    <form onSubmit={submit} className="upload-form">
      <fieldset disabled={busy}>
        <input
          ref={camera}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          aria-label="Take a vehicle photo"
          hidden
          onChange={(e) => {
            pick(e.target.files);
            e.target.value = "";
          }}
        />
        <div className="panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">01 / VEHICLE DETAILS</span>
              <h2>
                {training
                  ? "Build your training library"
                  : "Start a vehicle shoot"}
              </h2>
            </div>
            <span className="subtle-pill">
              <Camera size={14} />{" "}
              {training ? "Training upload" : "Local upload"}
            </span>
          </div>
          <div className="segmented">
            <button
              type="button"
              className={mode === "dealership" ? "selected" : ""}
              onClick={() => setMode("dealership")}
            >
              Dealership standards
            </button>
            <button
              type="button"
              className={mode === "general" ? "selected" : ""}
              onClick={() => setMode("general")}
            >
              {training ? "Stage Now / outside photos" : "General QC"}
            </button>
          </div>
          <p className="form-note">
            {mode === "general"
              ? training
                ? "Training uploads start approved. You can uncheck approval for any photo. Choose a shot type before it can enter a dataset."
                : "Technical checks for any vehicle, without dealership photo-count or sequence rules."
              : "Choose the store and inventory type to apply its saved standards."}
          </p>
          <div className="form-grid">
            {mode === "dealership" ? (
              retained(
                "Dealership",
                dealer,
                setDealer,
                config.dealerships,
                true,
              )
            ) : (
              <Field title="Source (optional)">
                <input
                  value={form.source}
                  maxLength={150}
                  onChange={(e) => update("source", e.target.value)}
                  placeholder={
                    training ? "Stage Now" : "Outside dealership or collection"
                  }
                />
              </Field>
            )}
            {retained(
              "Photographer",
              photographer,
              setPhotographer,
              config.photographers,
            )}
            {retained(
              "New / Used",
              inventory,
              setInventory,
              [
                { id: "new", name: "New" },
                { id: "used", name: "Used" },
              ],
              true,
            )}
            <Field title="Stock number">
              <input
                value={form.stock_number}
                onChange={(e) => update("stock_number", e.target.value)}
                maxLength={100}
                placeholder="e.g. U18342"
              />
            </Field>
            <Field title="Shoot date">
              <input
                type="date"
                value={form.shoot_date}
                onChange={(e) => update("shoot_date", e.target.value)}
                required
              />
            </Field>
            <Field title="Year">
              <input
                type="number"
                min={1900}
                max={2100}
                value={form.year}
                onChange={(e) => update("year", e.target.value)}
                placeholder="2024"
              />
            </Field>
            <Field title="Make">
              <input
                value={form.make}
                onChange={(e) => update("make", e.target.value)}
                maxLength={100}
                placeholder="Ford"
              />
            </Field>
            <Field title="Model">
              <input
                value={form.model}
                onChange={(e) => update("model", e.target.value)}
                maxLength={100}
                placeholder="Explorer"
              />
            </Field>
            <Field title="Exterior color">
              <input
                value={form.color}
                onChange={(e) => update("color", e.target.value)}
                maxLength={100}
                placeholder="Blue"
              />
            </Field>
          </div>
          <details className="extra-fields">
            <summary>Additional details & environment</summary>
            <div className="form-grid">
              <Field title="Trim">
                <input
                  value={form.trim}
                  maxLength={100}
                  onChange={(e) => update("trim", e.target.value)}
                />
              </Field>
              <Field title="Season">
                <select
                  value={form.season}
                  onChange={(e) => update("season", e.target.value)}
                >
                  <option value="">Automatic (Northern Hemisphere)</option>
                  {["spring", "summer", "autumn", "winter"].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </Field>
              {(["lighting", "ground", "location"] as const).map((key) => (
                <Field key={key} title={key}>
                  <select
                    value={form[key]}
                    onChange={(e) => update(key, e.target.value)}
                  >
                    {{
                      lighting: [
                        "unknown",
                        "sunny",
                        "cloudy",
                        "shade",
                        "indoor",
                        "mixed",
                      ],
                      ground: ["unknown", "dry", "wet", "snow"],
                      location: [
                        "unknown",
                        "outdoor_lot",
                        "staging_area",
                        "photo_booth",
                        "indoor_bay",
                        "other",
                      ],
                    }[key].map((v) => (
                      <option key={v} value={v}>
                        {v.replaceAll("_", " ")}
                      </option>
                    ))}
                  </select>
                </Field>
              ))}
            </div>
          </details>
          <Field title="Note (optional)">
            <textarea
              value={form.note}
              onChange={(e) => update("note", e.target.value)}
              maxLength={2000}
              rows={2}
              placeholder="Anything the reviewer should know about this shoot?"
            />
          </Field>
        </div>
        <div className="panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">02 / PHOTOS & ORDER</span>
              <h2>
                Your photo sequence{" "}
                <span className="muted">
                  {photos.length ? `(${photos.length})` : ""}
                </span>
              </h2>
            </div>
            {photos.length > 0 && (
              <button
                type="button"
                className="button secondary"
                onClick={() => input.current?.click()}
              >
                <Plus size={16} /> Add photos
              </button>
            )}
          </div>
          <input
            ref={input}
            type="file"
            multiple
            accept="image/jpeg,image/png,image/webp"
            aria-label="Select photos"
            className="file-input"
            onChange={(e) => {
              pick(e.target.files);
              e.target.value = "";
            }}
          />
          {!photos.length ? (
            <button
              type="button"
              className="dropzone"
              onClick={() => input.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                pick(e.dataTransfer.files);
              }}
            >
              <UploadCloud size={36} />
              <strong>Select photos or drop them here</strong>
              <span>JPEG, PNG, WebP · Up to 200 photos · 25 MB per photo</span>
            </button>
          ) : (
            <>
              <p className="form-note">
                The numbered order below is the saved order. Drag to rearrange,
                or use the arrow buttons on a phone.
              </p>
              <div className="batch-actions">
                <span className="form-note">
                  {sequenceBusy ? "Loading sequence…" : suggestion.source}.
                  Unassigned beyond its length.
                </span>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => setSelectedIds(photos.map((p) => p.id))}
                >
                  Select all
                </button>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => setSelectedIds([])}
                >
                  Clear selection
                </button>
                <button
                  type="button"
                  className="button secondary"
                  disabled={!selectedIds.length}
                  onClick={removeSelected}
                >
                  Remove selected ({selectedIds.length})
                </button>
              </div>
              <div className="import-tray">
                {photos.map((p, i) => (
                  <div
                    className="import-photo"
                    key={p.id}
                    draggable
                    onDragStart={(e) =>
                      e.dataTransfer.setData("text/plain", String(i))
                    }
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault();
                      const from = Number(e.dataTransfer.getData("text/plain"));
                      if (Number.isInteger(from)) move(from, i);
                    }}
                  >
                    <img src={p.url} alt={`Selected photo ${i + 1}`} />
                    <span className="number">{i + 1}</span>
                    <button
                      type="button"
                      className="remove-photo"
                      aria-label={`Remove photo ${i + 1}`}
                      onClick={() => remove(p.id)}
                    >
                      <X size={15} />
                    </button>
                    <div className="reorder">
                      <button
                        type="button"
                        disabled={i === 0}
                        onClick={() => move(i, i - 1)}
                        aria-label={`Move photo ${i + 1} earlier`}
                      >
                        <ArrowLeft size={15} />
                      </button>
                      <GripVertical size={15} />
                      <button
                        type="button"
                        disabled={i === photos.length - 1}
                        onClick={() => move(i, i + 1)}
                        aria-label={`Move photo ${i + 1} later`}
                      >
                        <ArrowRight size={15} />
                      </button>
                    </div>
                    <small title={p.file.name}>{p.file.name}</small>
                    <label className="checkbox">
                      <input
                        type="checkbox"
                        aria-label={`Select pending photo ${i + 1}`}
                        checked={selectedIds.includes(p.id)}
                        onChange={(e) =>
                          setSelectedIds((prev) =>
                            e.target.checked
                              ? [...prev, p.id]
                              : prev.filter((x) => x !== p.id),
                          )
                        }
                      />
                      Select
                    </label>
                    <ShotSelect
                      title={`Shot type for pending photo ${i + 1}`}
                      value={shotAt(p, i)}
                      options={config.shot_types}
                      onChange={(value) =>
                        setPhotos((prev) =>
                          prev.map((x) =>
                            x.id === p.id ? { ...x, shot: value } : x,
                          ),
                        )
                      }
                    />
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </fieldset>
      <button
        type="button"
        className="button secondary"
        disabled={busy}
        onClick={() => camera.current?.click()}
      >
        <Camera size={16} /> Take photo
      </button>
      <p className="form-note">
        On Android, Take photo opens the camera when supported. Keep this page
        open while uploading; if interrupted, submit again to retry. Use JPEG,
        PNG, or WebP.
      </p>
      {error && <ErrorBox message={error} />}
      <div className="upload-footer">
        <p>
          <Check size={16} /> Original photos stay unchanged.
        </p>
        <button
          className="button primary"
          disabled={busy || sequenceBusy || !photos.length}
          type="submit"
        >
          <UploadCloud size={18} />
          {busy
            ? progress < 100
              ? `Uploading ${progress}%`
              : "Saving photos…"
            : training
              ? `Import ${photos.length || ""} training photos`
              : `Evaluate ${photos.length || ""} photos`}
        </button>
      </div>
    </form>
  );
}
