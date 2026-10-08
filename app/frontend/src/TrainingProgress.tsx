import { useEffect, useState } from "react";
import { api, label } from "./api";
import { ErrorBox } from "./ui";

type Readiness = {
  total: number;
  approved: number;
  unique_labeled: number;
  unassigned: number;
  classes: {
    key: string;
    label: string;
    count: number;
    vehicles: number;
    target: number;
  }[];
  quality: { key: string; count: number; target: number }[];
  dealerships: { name: string; count: number }[];
};
export function TrainingProgress({
  active = true,
  refresh,
  compact = false,
  open,
}: {
  active?: boolean;
  refresh: number;
  compact?: boolean;
  open?: () => void;
}) {
  const [data, setData] = useState<Readiness | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!active) return;
    const abort = new AbortController();
    api<Readiness>("/training/readiness", { signal: abort.signal })
      .then((d) => {
        setData(d);
        setError("");
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => abort.abort();
  }, [active, refresh]);
  if (error) return <ErrorBox message={error} />;
  if (!data) return null;
  const started = data.classes.filter((c) => c.count > 0);
  const needed = started.reduce(
    (n, c) => n + Math.max(0, c.target - c.count),
    0,
  );
  const row = (name: string, count: number, target: number) => (
    <div className="training-progress-row">
      <div>
        <strong>{name}</strong>
        <span>
          {count} / {target} · {Math.max(0, target - count)} more suggested
        </span>
      </div>
      <progress
        value={Math.min(count, target)}
        max={target}
        aria-label={`${name} collection target`}
      />
    </div>
  );
  return (
    <section
      className="panel training-progress"
      aria-label="Training collection guidance"
    >
      <h3>Training collection guide</h3>
      <p>
        {data.unique_labeled} unique approved photos with verified shot labels ·{" "}
        {data.unassigned} approved photos still need a shot type.
      </p>
      <p>
        {started.length
          ? `${needed} more photos suggested across your ${started.length} started shot categories.`
          : "Start with the shot categories your dealerships use most."}
      </p>
      <p className="form-note">
        Planning targets only: about 50 unique photos per shot category, across
        at least 10 different vehicles. These are starting estimates, not
        accuracy guarantees. Exact duplicate images count once.
      </p>
      {compact ? (
        <button className="text-button" onClick={open}>
          See photo types and collection targets →
        </button>
      ) : (
        <>
          <details open>
            <summary>Shot types for the current classifier</summary>
            <div className="training-targets">
              {data.classes.map((c) => (
                <div key={c.key}>
                  {row(c.label, c.count, c.target)}
                  <small>
                    {c.vehicles} distinct vehicle groups · aim for 10+ with
                    varied colors, lighting and cameras
                  </small>
                </div>
              ))}
            </div>
          </details>
          <details>
            <summary>Problem examples for future quality models</summary>
            <p className="form-note">
              The current ML model learns shot types, not quality defects. These
              verified human-labeled examples build a future collection; technical checks
              currently use fixed measurements.
            </p>
            {data.quality.map((q) => (
              <div key={q.key}>{row(label(q.key), q.count, q.target)}</div>
            ))}
          </details>
          <details>
            <summary>Dealership coverage</summary>
            <p className="form-note">
              The shot classifier is shared across dealerships. Collect
              representative vehicles and conditions from each store; there is
              no separate per-dealership minimum.
            </p>
            {data.dealerships.map((d) => (
              <p key={d.name}>
                {d.name}: {d.count} unique approved photos
              </p>
            ))}
          </details>
          <p className="form-note">
            Validate on separate vehicles in training, validation and test
            splits. Collection targets do not replace the training command’s
            coverage checks or real-world model evaluation.
          </p>
        </>
      )}
    </section>
  );
}
