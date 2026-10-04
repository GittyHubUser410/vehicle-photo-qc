import { useState } from "react";
import { send } from "./api";
import { Field, Modal, ErrorBox } from "./ui";
import type { Config, Notify, Shoot } from "./types";

export function VehicleEditor({
  shoot,
  config,
  close,
  saved,
  notify,
}: {
  shoot: Shoot;
  config: Config;
  close: () => void;
  saved: () => void;
  notify: Notify;
}) {
  const [form, setForm] = useState({
    mode: shoot.mode,
    dealership_id: shoot.dealership_id || "",
    photographer_id: shoot.photographer_id || "",
    inventory_type: shoot.inventory_type,
    source: shoot.source || "",
    stock_number: shoot.stock_number,
    year: shoot.year?.toString() || "",
    make: shoot.make,
    model: shoot.model,
    trim: shoot.trim,
    color: shoot.color,
    shoot_date: shoot.shoot_date,
    season: shoot.season,
    lighting: shoot.lighting,
    ground: shoot.ground,
    location: shoot.location,
    note: shoot.note,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const field = (key: keyof typeof form, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));
  const policyChange =
    form.dealership_id !== (shoot.dealership_id || "") ||
    form.mode !== shoot.mode ||
    form.inventory_type !== shoot.inventory_type;
  return (
    <Modal title="Edit vehicle" onClose={close}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            await send(`/shoots/${shoot.id}`, "PUT", {
              ...form,
              year: form.year ? Number(form.year) : null,
              dealership_id:
                form.mode === "dealership" ? form.dealership_id : null,
              photographer_id: form.photographer_id || null,
              metadata_revision: shoot.metadata_revision,
              purpose: shoot.purpose,
            });
            notify(
              policyChange
                ? "Vehicle saved. Analysis queued with the corrected dealership standards."
                : "Vehicle details saved.",
            );
            saved();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {error && <ErrorBox message={error} />}
        <div className="form-grid">
          <Field title="Dealership / source">
            <select
              value={form.mode === "general" ? "general" : form.dealership_id}
              required
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  mode: e.target.value === "general" ? "general" : "dealership",
                  dealership_id:
                    e.target.value === "general" ? "" : e.target.value,
                }))
              }
            >
              <option value="general">General QC / external source</option>
              {config.dealerships.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </Field>
          <Field title="Photographer">
            <select
              value={form.photographer_id}
              onChange={(e) => field("photographer_id", e.target.value)}
            >
              <option value="">Not specified</option>
              {config.photographers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </Field>
          {(
            [
              ["stock_number", "Stock number"],
              ["year", "Year"],
              ["make", "Make"],
              ["model", "Model"],
              ["trim", "Trim"],
              ["color", "Color"],
              ["source", "Source name"],
              ["shoot_date", "Shoot date"],
            ] as const
          ).map(([key, title]) => (
            <Field key={key} title={title}>
              <input
                value={form[key]}
                type={
                  key === "year"
                    ? "number"
                    : key === "shoot_date"
                      ? "date"
                      : "text"
                }
                min={key === "year" ? 1900 : undefined}
                max={key === "year" ? 2100 : undefined}
                maxLength={key === "source" ? 150 : 100}
                required={key === "shoot_date"}
                onChange={(e) => field(key, e.target.value)}
              />
            </Field>
          ))}
          {(
            [
              ["inventory_type", ["new", "used"]],
              ["season", ["winter", "spring", "summer", "autumn"]],
              [
                "lighting",
                ["unknown", "sunny", "cloudy", "shade", "indoor", "mixed"],
              ],
              ["ground", ["unknown", "dry", "wet", "snow"]],
              [
                "location",
                [
                  "unknown",
                  "outdoor_lot",
                  "staging_area",
                  "photo_booth",
                  "indoor_bay",
                  "other",
                ],
              ],
            ] as const
          ).map(([key, values]) => (
            <Field
              key={key}
              title={key
                .replace("_type", "")
                .replace(/^./, (c) => c.toUpperCase())}
            >
              <select
                value={form[key]}
                onChange={(e) => field(key, e.target.value)}
              >
                {values.map((v) => (
                  <option key={v} value={v}>
                    {v.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </Field>
          ))}
        </div>
        <Field title="Vehicle note">
          <textarea
            value={form.note}
            maxLength={2000}
            onChange={(e) => field("note", e.target.value)}
          />
        </Field>
        <p className="form-note">
          Changing dealership, inventory or QC mode runs a new analysis using
          the corrected standards. Previous analysis history, photo labels and
          files remain available.
        </p>
        <button
          className="button primary"
          disabled={busy || ["queued", "processing"].includes(shoot.status)}
        >
          Save vehicle
        </button>
      </form>
    </Modal>
  );
}
