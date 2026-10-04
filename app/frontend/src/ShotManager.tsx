import { useState } from "react";
import { ArrowUp, ArrowDown } from "lucide-react";
import { send } from "./api";
import { Modal, Field } from "./ui";
import type { Config, Notify } from "./types";
export function ShotManager({
  config,
  reload,
  notify,
}: {
  config: Config;
  reload: () => void;
  notify: Notify;
}) {
  const [editing, setEditing] = useState<{ key: string; name: string } | null>(
    null,
  );
  const [deleting, setDeleting] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function update(path: string, method: string, body: unknown) {
    setBusy(true);
    try {
      await send(path, method, body);
      setEditing(null);
      setDeleting(null);
      reload();
      notify(
        "Shot types updated. Existing labels and model classes are preserved.",
      );
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setBusy(false);
    }
  }
  function move(key: string, delta: number) {
    const keys = [...config.shot_types],
      index = keys.indexOf(key);
    [keys[index], keys[index + delta]] = [keys[index + delta], keys[index]];
    void update("/shot-types/order", "PUT", { keys });
  }
  return (
    <>
      <details>
        <summary>Manage categories ({config.shot_types.length})</summary>
        <p className="form-note">
          Reorder with the arrows. Renaming changes the display name only; keep
          the category’s meaning the same. Delete hides it from new selections
          and preserves historical labels.
        </p>
        {config.shot_types.map((key, index) => (
          <div className="shot-manager-row" key={key}>
            <span>{config.shot_type_labels[key]}</span>
            <button
              className="icon-button"
              aria-label={`Move ${config.shot_type_labels[key]} up`}
              disabled={busy || index === 0}
              onClick={() => move(key, -1)}
            >
              <ArrowUp size={16} />
            </button>
            <button
              className="icon-button"
              aria-label={`Move ${config.shot_type_labels[key]} down`}
              disabled={busy || index === config.shot_types.length - 1}
              onClick={() => move(key, 1)}
            >
              <ArrowDown size={16} />
            </button>
            <button
              className="text-button"
              disabled={busy}
              onClick={() =>
                setEditing({ key, name: config.shot_type_labels[key] })
              }
            >
              Rename
            </button>
            <button
              className="text-button danger-text"
              disabled={busy || ["unknown", "other"].includes(key)}
              onClick={() => setDeleting(key)}
            >
              Delete
            </button>
          </div>
        ))}
      </details>
      {!!config.shot_catalog.filter((c) => c.archived).length && (
        <details>
          <summary>Deleted categories</summary>
          {config.shot_catalog
            .filter((c) => c.archived)
            .map((c) => (
              <div className="shot-manager-row" key={c.key}>
                <span>{c.label}</span>
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() =>
                    update(`/shot-types/${c.key}`, "PATCH", { archived: false })
                  }
                >
                  Restore
                </button>
              </div>
            ))}
        </details>
      )}
      {editing && (
        <Modal title="Rename shot type" onClose={() => setEditing(null)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void update(`/shot-types/${editing.key}`, "PATCH", {
                name: editing.name,
              });
            }}
          >
            <Field title="Shot type name">
              <input
                value={editing.name}
                maxLength={150}
                required
                onChange={(e) =>
                  setEditing({ ...editing, name: e.target.value })
                }
              />
            </Field>
            <button className="button primary" disabled={busy}>
              Save name
            </button>
          </form>
        </Modal>
      )}
      {deleting && (
        <Modal title="Delete shot type?" onClose={() => setDeleting(null)}>
          <p>
            Hide {config.shot_type_labels[deleting]} from new selections?
            Existing photo labels, datasets and models remain unchanged. You can
            restore it later.
          </p>
          <button
            className="button primary"
            disabled={busy}
            onClick={() =>
              update(`/shot-types/${deleting}`, "PATCH", { archived: true })
            }
          >
            Delete category
          </button>
        </Modal>
      )}
    </>
  );
}
