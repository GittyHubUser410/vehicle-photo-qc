import { useEffect, useState } from "react";
import { api, send } from "./api";
import { ErrorBox } from "./ui";
import type { Notify } from "./types";
type Item = {
  kind: string;
  id: string;
  scope: string;
  title: string;
  deleted_at: string;
};
export function Trash({
  active,
  refresh,
  changed,
  notify,
}: {
  active: boolean;
  refresh: number;
  changed: () => void;
  notify: Notify;
}) {
  const [items, setItems] = useState<Item[]>([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!active) return;
    const abort = new AbortController();
    api<Item[]>("/trash", { signal: abort.signal })
      .then(setItems)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => abort.abort();
  }, [active, refresh]);
  return (
    <section className="panel">
      <h2>Trash</h2>
      <p>
        Deleted files are retained. Restore a vehicle before its photos.
        Restored training photos need approval again.
      </p>
      {error && <ErrorBox message={error} />}{" "}
      {!items.length && <p className="muted">Trash is empty.</p>}
      {items.map((item) => (
        <div
          className="setting-row"
          key={`${item.kind}:${item.id}:${item.scope}`}
        >
          <span>
            {item.title}
            <small>
              {item.scope === "training" ? "Training storage" : "All storage"} ·{" "}
              {new Date(item.deleted_at).toLocaleString()}
            </small>
          </span>
          <button
            className="button secondary"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await send(`/trash/${item.kind}/${item.id}/restore`, "POST", {
                  scope: item.scope,
                });
                changed();
                notify("Restored. Training approval remains off.");
              } catch (e) {
                notify((e as Error).message, true);
              } finally {
                setBusy(false);
              }
            }}
          >
            Restore
          </button>
        </div>
      ))}
    </section>
  );
}
