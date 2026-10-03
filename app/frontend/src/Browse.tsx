import { useEffect, useState } from "react";
import {
  Search,
  SlidersHorizontal,
  ArrowRight,
  AlertTriangle,
  Eye,
  Plus,
  Download,
  Camera,
  CheckCircle2,
} from "lucide-react";
import { api, label, send, thumbnail, useStored, vehicleName } from "./api";
import { Badge, Empty, ErrorBox, Field, VehicleCard } from "./ui";
import type { Config, Notify, OpenDetail, Review, Shoot } from "./types";

export function Browse({
  kind,
  active,
  config,
  refresh,
  open,
  upload,
  notify,
}: {
  kind: "results" | "library" | "training";
  active: boolean;
  config: Config;
  refresh: number;
  open: OpenDetail;
  upload: () => void;
  notify: Notify;
}) {
  const defaults: Record<string, string> = {
    q: "",
    dealership_id: "",
    photographer_id: "",
    inventory_type: "",
    previously_queued: "",
    issue: "",
    shot_type: "",
    date_from: "",
    date_to: "",
    season: "",
    lighting: "",
    color: "",
    max_score: "",
    status: "",
    eligible: "",
    sort: "newest",
  };
  const [filters, setFilters] = useStored(`qc:filters:${kind}`, defaults);
  const [offset, setOffset] = useState(0);
  const [showFilters, setShowFilters] = useState(false);
  const [result, setResult] = useState<{ items: Shoot[]; total: number }>({
    items: [],
    total: 0,
  });
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [exported, setExported] = useState<{
    download_url: string;
    splits: Record<string, number>;
  } | null>(null);
  const [exporting, setExporting] = useState(false);
  const filter = (key: string, value: string) => {
    setFilters({ ...filters, [key]: value });
    setOffset(0);
  };
  useEffect(() => {
    if (!active) return;
    const abort = new AbortController();
    const timer = setTimeout(() => {
      const params = new URLSearchParams({
        ...Object.fromEntries(
          Object.entries(filters).filter(([, v]) => v !== ""),
        ),
        purpose: kind === "training" ? "training" : "evaluation",
        offset: String(offset),
      });
      api<{ items: Shoot[]; total: number }>(`/shoots?${params}`, {
        signal: abort.signal,
      })
        .then((r) => {
          setResult(r);
          setLoaded(true);
          setError("");
        })
        .catch((e) => {
          if (e.name !== "AbortError") setError(e.message);
        });
    }, 180);
    return () => {
      clearTimeout(timer);
      abort.abort();
    };
  }, [active, filters, offset, refresh, kind]);
  const select = (
    title: string,
    key: string,
    options: { value: string; label: string }[],
  ) => (
    <Field title={title}>
      <select
        value={filters[key]}
        onChange={(e) => filter(key, e.target.value)}
      >
        <option value="">All</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </Field>
  );
  const options = (values: string[]) =>
    values.map((value) => ({ value, label: label(value) }));
  async function exportTraining() {
    setExporting(true);
    try {
      const result = await send<{
        download_url: string;
        splits: Record<string, number>;
      }>("/datasets", "POST");
      setExported(result);
      notify(
        "Dataset snapshot saved. Labels and split membership are frozen in this export.",
      );
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setExporting(false);
    }
  }
  return (
    <>
      {kind === "training" && (
        <div className="training-banner">
          <div>
            <Badge tone="teal">HUMAN APPROVED</Badge>
            <h2>Better examples. Better models.</h2>
            <p>
              Collect good, bad, and borderline photos. Label each issue
              separately, then approve the example for training.
            </p>
          </div>
          <div className="button-stack">
            <button className="button primary" onClick={upload}>
              <Plus size={17} /> Upload training data
            </button>
            <button
              className="button secondary"
              disabled={exporting}
              onClick={exportTraining}
            >
              <Download size={16} />
              {exporting ? "Exporting…" : "Export approved dataset"}
            </button>
          </div>
        </div>
      )}
      {exported && (
        <div className="notice">
          <CheckCircle2 size={18} />
          <span>
            Snapshot:{" "}
            {Object.entries(exported.splits)
              .map(([k, v]) => `${v} ${k}`)
              .join(" · ")}
            . Small collections may have empty splits.{" "}
            <a href={exported.download_url} download>
              Download manifest
            </a>
          </span>
        </div>
      )}
      <div className="browse-toolbar">
        <div className="search">
          <Search size={18} />
          <input
            aria-label="Search vehicles"
            placeholder="Search stock #, year, make, model, color…"
            value={filters.q}
            onChange={(e) => filter("q", e.target.value)}
          />
        </div>
        <button
          className={`button secondary ${showFilters ? "active" : ""}`}
          onClick={() => setShowFilters(!showFilters)}
        >
          <SlidersHorizontal size={16} /> Filters{" "}
          {Object.entries(filters).filter(
            ([k, v]) => v && !["q", "sort"].includes(k),
          ).length || ""}
        </button>
        <select
          aria-label="Sort vehicles"
          value={filters.sort}
          onChange={(e) => filter("sort", e.target.value)}
        >
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
          <option value="lowest">Lowest score</option>
          <option value="highest">Highest score</option>
          <option value="stock">Stock number</option>
        </select>
      </div>
      {showFilters && (
        <div className="panel filters">
          <div className="form-grid">
            {select(
              "Dealership",
              "dealership_id",
              config.dealerships.map((d) => ({ value: d.id, label: d.name })),
            )}
            {select(
              "Photographer",
              "photographer_id",
              config.photographers.map((d) => ({ value: d.id, label: d.name })),
            )}
            {select("Inventory", "inventory_type", options(["new", "used"]))}
            {select(
              "Previously in review queue",
              "previously_queued",
              options(["yes", "no"]),
            )}
            {select(
              "Issue",
              "issue",
              options([
                "BLUR",
                "EXPOSURE",
                "SATURATION",
                "PHOTO_COUNT",
                "MISSING_REQUIRED_SHOT",
                "SEQUENCE",
              ]),
            )}
            {select(
              "Manual shot type",
              "shot_type",
              options(config.shot_types),
            )}
            {select(
              "Season",
              "season",
              options(["winter", "spring", "summer", "autumn"]),
            )}
            {select(
              "Lighting",
              "lighting",
              options([
                "sunny",
                "cloudy",
                "shade",
                "indoor",
                "mixed",
                "unknown",
              ]),
            )}
            <Field title="Color (exact)">
              <input
                value={filters.color}
                onChange={(e) => filter("color", e.target.value)}
              />
            </Field>
            <Field title="From date">
              <input
                type="date"
                value={filters.date_from}
                onChange={(e) => filter("date_from", e.target.value)}
              />
            </Field>
            <Field title="Through date">
              <input
                type="date"
                value={filters.date_to}
                onChange={(e) => filter("date_to", e.target.value)}
              />
            </Field>
            <Field title="Maximum technical score">
              <input
                type="number"
                min={0}
                max={100}
                value={filters.max_score}
                onChange={(e) => filter("max_score", e.target.value)}
              />
            </Field>
            {select(
              "Processing state",
              "status",
              options(["queued", "processing", "complete", "failed"]),
            )}
            {kind === "training" &&
              select(
                "Approved for training",
                "eligible",
                options(["yes", "no"]),
              )}
          </div>
          <button
            className="text-button"
            onClick={() => {
              setFilters(defaults);
              setOffset(0);
            }}
          >
            Clear all filters
          </button>
        </div>
      )}
      {error && <ErrorBox message={error} />}
      <div className="list-caption">
        <span>{result.total} vehicle shoots</span>
        <span>
          {kind === "training"
            ? "Labeling never changes the original image"
            : "Scores cover technical checks only"}
        </span>
      </div>
      {!loaded && !error ? (
        <div className="loading">Loading vehicles…</div>
      ) : !result.items.length ? (
        <Empty
          title={
            Object.values(filters).filter(Boolean).length > 1
              ? "No matching vehicles"
              : kind === "training"
                ? "Your training library starts here"
                : "Your first shoot starts here"
          }
          action={
            <button className="button primary" onClick={upload}>
              <Plus size={16} />
              {kind === "training"
                ? "Upload training data"
                : "Evaluate a vehicle"}
            </button>
          }
        >
          Upload a vehicle shoot, or adjust your search and filters.
        </Empty>
      ) : kind === "library" ? (
        <div className="library-grid">
          {result.items.map((s) => (
            <button
              className="library-card"
              key={s.id}
              onClick={() => open(s.id)}
            >
              <div className="library-preview">
                {s.previews[0] ? (
                  <img
                    src={thumbnail(s.previews[0].id)}
                    alt={vehicleName(s)}
                    loading="lazy"
                  />
                ) : (
                  <Camera />
                )}
                <Badge>{s.photo_count} photos</Badge>
              </div>
              <div>
                <span className="eyebrow">
                  {s.stock_number || "No stock number"}
                </span>
                <h3>{vehicleName(s)}</h3>
                <p>
                  {s.dealership_name} · {s.shoot_date}
                </p>
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="vehicle-list">
          {result.items.map((s) => (
            <VehicleCard key={s.id} shoot={s} open={open} />
          ))}
        </div>
      )}
      <Pagination offset={offset} total={result.total} setOffset={setOffset} />
    </>
  );
}

export function Pagination({
  offset,
  total,
  setOffset,
}: {
  offset: number;
  total: number;
  setOffset: (v: number) => void;
}) {
  if (total <= 30) return null;
  return (
    <div className="pagination">
      <button
        className="button secondary"
        disabled={!offset}
        onClick={() => setOffset(Math.max(0, offset - 30))}
      >
        Previous
      </button>
      <span>
        {offset + 1}–{Math.min(offset + 30, total)} of {total}
      </span>
      <button
        className="button secondary"
        disabled={offset + 30 >= total}
        onClick={() => setOffset(offset + 30)}
      >
        Next
      </button>
    </div>
  );
}

export function ReviewQueue({
  active,
  config,
  refresh,
  open,
  severeOnly,
  notify,
}: {
  active: boolean;
  config: Config;
  refresh: number;
  open: OpenDetail;
  severeOnly: number;
  notify: Notify;
}) {
  const [filters, setFilters] = useStored("qc:review-filters", {
    q: "",
    severity: "",
    viewed: "",
    state: "open",
    dealership_id: "",
    sort: "priority",
  });
  const [offset, setOffset] = useState(0);
  const [result, setResult] = useState<{ items: Review[]; total: number }>({
    items: [],
    total: 0,
  });
  const [error, setError] = useState("");
  useEffect(() => {
    if (severeOnly) {
      setFilters((f) => ({ ...f, severity: "severe", state: "open" }));
      setOffset(0);
    }
  }, [severeOnly]);
  const filter = (key: string, value: string) => {
    setFilters({ ...filters, [key]: value });
    setOffset(0);
  };
  useEffect(() => {
    if (!active) return;
    const abort = new AbortController();
    const timer = setTimeout(() => {
      api<{ items: Review[]; total: number }>(
        `/reviews?${new URLSearchParams({ ...filters, offset: String(offset) })}`,
        { signal: abort.signal },
      )
        .then((r) => {
          setResult(r);
          setError("");
        })
        .catch((e) => {
          if (e.name !== "AbortError") setError(e.message);
        });
    }, 150);
    return () => {
      abort.abort();
      clearTimeout(timer);
    };
  }, [active, filters, offset, refresh]);
  async function inspect(r: Review) {
    try {
      await send(`/reviews/${r.id}`, "PATCH", { action: "view" });
      setResult((prev) => ({
        ...prev,
        items: prev.items.map((item) =>
          item.id === r.id
            ? { ...item, viewed_at: new Date().toISOString() }
            : item,
        ),
      }));
      open(r.shoot_id, r.photo_id || undefined, r.id);
    } catch (e) {
      notify((e as Error).message, true);
    }
  }
  return (
    <>
      <div className="notice">
        <Eye size={18} />
        <span>
          Opening an item marks it viewed. It stays here until you explicitly
          resolve it.
        </span>
      </div>
      <div className="browse-toolbar">
        <div className="search">
          <Search size={18} />
          <input
            aria-label="Search reviews"
            placeholder="Search stock #, model, issue, or reviewer note…"
            value={filters.q}
            onChange={(e) => filter("q", e.target.value)}
          />
        </div>
        <select
          aria-label="Review state"
          value={filters.state}
          onChange={(e) => filter("state", e.target.value)}
        >
          <option value="open">Open reviews</option>
          <option value="resolved">Resolved</option>
          <option value="all">All history</option>
        </select>
        <select
          aria-label="Review sort"
          value={filters.sort}
          onChange={(e) => filter("sort", e.target.value)}
        >
          <option value="priority">Priority first</option>
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
        </select>
      </div>
      <div className="filter-row">
        <select
          aria-label="Review severity"
          value={filters.severity}
          onChange={(e) => filter("severity", e.target.value)}
        >
          <option value="">All severities</option>
          {["severe", "moderate", "minor"].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select
          aria-label="Viewed status"
          value={filters.viewed}
          onChange={(e) => filter("viewed", e.target.value)}
        >
          <option value="">Viewed & unviewed</option>
          <option value="no">Unviewed</option>
          <option value="yes">Viewed</option>
        </select>
        <select
          aria-label="Review dealership"
          value={filters.dealership_id}
          onChange={(e) => filter("dealership_id", e.target.value)}
        >
          <option value="">All dealerships</option>
          {config.dealerships.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
        <span>{result.total} items</span>
      </div>
      {error && <ErrorBox message={error} />}
      {!result.items.length ? (
        <Empty title="No reviews in this view">
          New technical concerns appear here after a shoot is processed. Try
          changing the filters to see resolved items.
        </Empty>
      ) : (
        <div className="review-list">
          {result.items.map((r) => (
            <button
              key={r.id}
              className={`review-card ${!r.viewed_at && !r.resolved_at ? "unviewed" : ""}`}
              onClick={() => inspect(r)}
            >
              <div className="review-thumb">
                {r.photo_id ? (
                  <img
                    src={thumbnail(r.photo_id)}
                    alt="Photo needing review"
                    loading="lazy"
                  />
                ) : (
                  <AlertTriangle size={28} />
                )}
              </div>
              <div className="review-copy">
                <div className="eyebrow">
                  {r.shoot?.stock_number || "Vehicle shoot"}{" "}
                  <Badge
                    tone={
                      r.resolved_at
                        ? "teal"
                        : r.severity === "severe"
                          ? "danger"
                          : "warn"
                    }
                  >
                    {r.resolved_at ? "Resolved" : r.severity}
                  </Badge>
                  {!r.viewed_at && !r.resolved_at && (
                    <span className="new-dot">NEW</span>
                  )}
                </div>
                <h3>{r.shoot ? vehicleName(r.shoot) : "Vehicle"}</h3>
                <p>{r.reason}</p>
                <small>
                  {r.shoot?.dealership_name} · {r.created_at.slice(0, 10)}{" "}
                  {r.viewed_at ? "· Viewed" : ""}
                </small>
              </div>
              <ArrowRight size={18} />
            </button>
          ))}
        </div>
      )}
      <Pagination offset={offset} total={result.total} setOffset={setOffset} />
    </>
  );
}
