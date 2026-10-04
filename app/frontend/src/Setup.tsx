import { useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  Building2,
  Check,
  Plus,
  Trash2,
  Users,
} from "lucide-react";
import { ShotManager } from "./ShotManager";
import { label, send } from "./api";
import { Badge, Field, Modal } from "./ui";
import type { Config, Dealer, Group, Notify, Rules } from "./types";

export function Setup({
  config,
  reload,
  notify,
}: {
  config: Config;
  reload: () => void;
  notify: Notify;
}) {
  const [shotName, setShotName] = useState("");
  const [dealer, setDealer] = useState<Dealer | "new" | null>(null);
  const [group, setGroup] = useState<Group | "new" | null>(null);
  const [photographer, setPhotographer] = useState<{
    id?: string;
    name: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  async function savePhotographer() {
    if (!photographer) return;
    setBusy(true);
    try {
      await send(
        `/photographers${photographer.id ? `/${photographer.id}` : ""}`,
        photographer.id ? "PUT" : "POST",
        { name: photographer.name },
      );
      setPhotographer(null);
      reload();
      notify("Photographer saved.");
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="notice">
        <Building2 size={18} />
        <span>
          Group rules flow down to each dealership. Dealer overrides take
          priority. Imported shoots keep a snapshot of their original standards.
        </span>
      </div>
      <div className="section-heading">
        <div>
          <span className="eyebrow">ORGANIZATION & STANDARDS</span>
          <h2>Your dealerships</h2>
        </div>
        <button className="button primary" onClick={() => setDealer("new")}>
          <Plus size={16} /> Add dealership
        </button>
      </div>
      <div className="dealer-grid">
        {config.dealerships.map((d) => (
          <button
            className="dealer-card"
            key={d.id}
            onClick={() => setDealer(d)}
          >
            <div className="dealer-icon">
              <Building2 size={23} />
            </div>
            <h3>{d.name}</h3>
            <p>
              {config.groups.find((g) => g.id === d.group_id)?.name ||
                "Independent dealership"}
            </p>
            <div className="dealer-stats">
              <span>
                <b>{d.effective_used.rules.required_shots.length}</b> used
                required shots
              </span>
              <span>
                <b>{d.effective_new.rules.required_shots.length}</b> new
                required shots
              </span>
            </div>
            <div className="inline between">
              <Badge>Version {d.version}</Badge>
              <span className="text-link">Edit standards →</span>
            </div>
          </button>
        ))}
      </div>
      <div className="setup-bottom">
        <section className="panel">
          <div className="section-heading">
            <h2>Conglomerates</h2>
            <button
              className="button secondary"
              onClick={() => setGroup("new")}
            >
              <Plus size={15} /> Add group
            </button>
          </div>
          {config.groups.map((g) => (
            <button
              className="setting-row"
              key={g.id}
              onClick={() => setGroup(g)}
            >
              <Building2 size={17} />
              <span>
                {g.name}
                <small>{Object.keys(g.rules).length} shared rules</small>
              </span>
              <span>Edit →</span>
            </button>
          ))}
        </section>
        <section className="panel">
          <div className="section-heading">
            <h2>Photographers</h2>
            <button
              className="button secondary"
              onClick={() => setPhotographer({ name: "" })}
            >
              <Plus size={15} /> Add person
            </button>
          </div>
          {config.photographers.map((p) => (
            <button
              className="setting-row"
              key={p.id}
              onClick={() => setPhotographer(p)}
            >
              <Users size={17} />
              <span>{p.name}</span>
              <span>Edit →</span>
            </button>
          ))}
        </section>
      </div>
      <section className="panel">
        <h2>Shot types</h2>
        <p>
          Shared across uploads, training, and dealership rules. Existing
          categories remain available for older records and models.
        </p>
        <form
          className="button-row"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            try {
              await send("/shot-types", "POST", { name: shotName });
              setShotName("");
              reload();
              notify("Shot type added.");
            } catch (e) {
              notify((e as Error).message, true);
            } finally {
              setBusy(false);
            }
          }}
        >
          <Field title="New shot type">
            <input
              required
              maxLength={150}
              value={shotName}
              onChange={(e) => setShotName(e.target.value)}
            />
          </Field>
          <button
            className="button secondary"
            disabled={busy || !shotName.trim()}
          >
            Add shot type
          </button>
        </form>
        <ShotManager config={config} reload={reload} notify={notify} />
      </section>
      {dealer && (
        <DealerEditor
          dealer={dealer}
          config={config}
          close={() => setDealer(null)}
          saved={() => {
            setDealer(null);
            reload();
          }}
          notify={notify}
        />
      )}
      {group && (
        <GroupEditor
          group={group}
          config={config}
          close={() => setGroup(null)}
          saved={() => {
            setGroup(null);
            reload();
          }}
          notify={notify}
        />
      )}
      {photographer && (
        <Modal
          title={photographer.id ? "Edit photographer" : "Add photographer"}
          onClose={() => setPhotographer(null)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              savePhotographer();
            }}
          >
            <Field title="Photographer name">
              <input
                autoFocus
                required
                maxLength={150}
                value={photographer.name}
                onChange={(e) =>
                  setPhotographer({ ...photographer, name: e.target.value })
                }
              />
            </Field>
            <button className="button primary" disabled={busy}>
              Save photographer
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}

function DealerEditor({
  dealer,
  config,
  close,
  saved,
  notify,
}: {
  dealer: Dealer | "new";
  config: Config;
  close: () => void;
  saved: () => void;
  notify: Notify;
}) {
  const [name, setName] = useState(dealer === "new" ? "" : dealer.name);
  const [groupId, setGroupId] = useState(
    dealer === "new" ? "" : dealer.group_id || "",
  );
  const [inventory, setInventory] = useState<"new" | "used">("used");
  const [rules, setRules] = useState({
    new: dealer === "new" ? {} : dealer.new_rules,
    used: dealer === "new" ? {} : dealer.used_rules,
  });
  const [busy, setBusy] = useState(false);
  const group = config.groups.find((g) => g.id === groupId);
  const inherited = { ...config.default_rules, ...group?.rules };
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await send(
        `/dealerships${dealer === "new" ? "" : `/${dealer.id}`}`,
        dealer === "new" ? "POST" : "PUT",
        {
          name,
          group_id: groupId || null,
          new_rules: rules.new,
          used_rules: rules.used,
        },
      );
      notify("Dealership standards saved. New uploads will use this version.");
      saved();
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={dealer === "new" ? "Add dealership" : "Dealership standards"}
      onClose={close}
      wide
    >
      <form onSubmit={submit}>
        <div className="form-grid two">
          <Field title="Dealership name">
            <input
              required
              maxLength={150}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </Field>
          <Field title="Conglomerate">
            <select
              value={groupId}
              onChange={(e) => setGroupId(e.target.value)}
            >
              <option value="">Independent dealership</option>
              {config.groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="segmented">
          <button
            type="button"
            className={inventory === "used" ? "selected" : ""}
            onClick={() => setInventory("used")}
          >
            Used vehicle standards
          </button>
          <button
            type="button"
            className={inventory === "new" ? "selected" : ""}
            onClick={() => setInventory("new")}
          >
            New vehicle standards
          </button>
        </div>
        <RulesEditor
          value={rules[inventory]}
          inherited={inherited}
          parentName={group?.name || "Application defaults"}
          groupRules={group?.rules || {}}
          onChange={(v) => setRules({ ...rules, [inventory]: v })}
          shotTypes={config.shot_types}
        />
        <div className="sticky-save">
          <button type="button" className="button secondary" onClick={close}>
            Cancel
          </button>
          <button className="button primary" disabled={busy}>
            <Check size={16} />
            {busy ? "Saving…" : "Save dealership"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function GroupEditor({
  group,
  config,
  close,
  saved,
  notify,
}: {
  group: Group | "new";
  config: Config;
  close: () => void;
  saved: () => void;
  notify: Notify;
}) {
  const [name, setName] = useState(group === "new" ? "" : group.name);
  const [rules, setRules] = useState<Partial<Rules>>(
    group === "new" ? {} : group.rules,
  );
  const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await send(
        `/groups${group === "new" ? "" : `/${group.id}`}`,
        group === "new" ? "POST" : "PUT",
        { name, rules },
      );
      notify("Group standards saved. Dealer overrides remain in place.");
      saved();
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Conglomerate standards" onClose={close} wide>
      <form onSubmit={submit}>
        <Field title="Group name">
          <input
            required
            maxLength={150}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
        <p className="form-note">
          Shared standards apply to both new and used vehicles unless a
          dealership overrides them.
        </p>
        <RulesEditor
          value={rules}
          inherited={config.default_rules}
          parentName="Application defaults"
          groupRules={{}}
          onChange={setRules}
          shotTypes={config.shot_types}
        />
        <button className="button primary" disabled={busy}>
          Save group
        </button>
      </form>
    </Modal>
  );
}

const numericRules: {
  key: keyof Rules;
  title: string;
  hint: string;
  max: number;
  step: number;
  group: string;
}[] = [
  {
    key: "min_photos",
    title: "Minimum photo count",
    hint: "0 means no minimum.",
    max: 200,
    step: 1,
    group: "Required photos",
  },
  {
    key: "blur_min",
    title: "Minimum sharpness",
    hint: "Laplacian variance at up to 1024 px. Low-detail scenes can be flagged even when sharp.",
    max: 10000,
    step: 1,
    group: "Technical quality",
  },
  {
    key: "dark_max",
    title: "Maximum dark-pixel fraction",
    hint: "0.60 = 60% very dark pixels. Whole-image measurement.",
    max: 1,
    step: 0.01,
    group: "Technical quality",
  },
  {
    key: "bright_max",
    title: "Maximum bright-pixel fraction",
    hint: "0.35 = 35% very bright pixels. Whole-image measurement.",
    max: 1,
    step: 0.01,
    group: "Technical quality",
  },
  {
    key: "saturation_max",
    title: "Maximum average saturation",
    hint: "0.85 = 85% average saturation.",
    max: 1,
    step: 0.01,
    group: "Technical quality",
  },
  {
    key: "banner_top_pct",
    title: "Top banner height (%)",
    hint: "Guide preview only. Set 0 to reserve no banner area.",
    max: 40,
    step: 0.5,
    group: "Banner & angle setup",
  },
  {
    key: "banner_clearance_pct",
    title: "Banner clearance (%)",
    hint: "Additional image height below the banner; preview only.",
    max: 30,
    step: 0.5,
    group: "Banner & angle setup",
  },
  {
    key: "angle_tolerance_deg",
    title: "Angle tolerance (degrees)",
    hint: "Saved for future angle analysis. Not enforced in this version.",
    max: 90,
    step: 1,
    group: "Banner & angle setup",
  },
];

function RulesEditor({
  value,
  inherited,
  parentName,
  groupRules,
  onChange,
  shotTypes,
}: {
  value: Partial<Rules>;
  inherited: Rules;
  parentName: string;
  groupRules: Partial<Rules>;
  onChange: (v: Partial<Rules>) => void;
  shotTypes: string[];
}) {
  const effective = { ...inherited, ...value };
  const [addShot, setAddShot] = useState("");
  const set = (key: keyof Rules, v: Rules[keyof Rules]) =>
    onChange({ ...value, [key]: v });
  const toggle = (key: keyof Rules) => {
    if (key in value) {
      const next = { ...value };
      delete next[key];
      onChange(next);
    } else set(key, effective[key]);
  };
  const source = (key: keyof Rules) =>
    key in value
      ? "Custom override"
      : key in groupRules
        ? `Inherited from ${parentName}`
        : "Application default";
  const controls = (key: keyof Rules) => (
    <button type="button" className="text-button" onClick={() => toggle(key)}>
      {key in value ? "Use inherited value" : "Override"}
    </button>
  );
  function move(from: number, to: number) {
    const shots = [...effective.required_shots];
    shots.splice(to, 0, shots.splice(from, 1)[0]);
    set("required_shots", shots);
  }
  return (
    <div className="rules-editor">
      {["Required photos", "Technical quality", "Banner & angle setup"].map(
        (section) => (
          <section key={section} className="rules-section">
            <h3>{section}</h3>
            {section === "Banner & angle setup" && (
              <div className="notice compact">
                Banner guides are previews. Vehicle segmentation, critical-crop
                detection, and angle analysis still need trained components.
              </div>
            )}
            {section === "Banner & angle setup" && (
              <>
                <div className="rule-row">
                  <div>
                    <strong>Banner application</strong>
                    <p>Choose which photos reserve banner space.</p>
                    <small>{source("banner_application")}</small>
                  </div>
                  <select
                    aria-label="Banner application"
                    disabled={!("banner_application" in value)}
                    value={effective.banner_application}
                    onChange={(e) =>
                      set(
                        "banner_application",
                        e.target.value as Rules["banner_application"],
                      )
                    }
                  >
                    <option value="none">None</option>
                    <option value="first">First photo only</option>
                    <option value="all">All applicable photos</option>
                  </select>
                  {controls("banner_application")}
                </div>
                <div className="rule-row">
                  <div>
                    <strong>Applicable banner shot types</strong>
                    <p>
                      Leave all unselected to apply to every shot type. Hold
                      Ctrl or Command to select multiple.
                    </p>
                    <small>{source("banner_shot_types")}</small>
                  </div>
                  <select
                    multiple
                    aria-label="Applicable banner shot types"
                    disabled={!("banner_shot_types" in value)}
                    value={effective.banner_shot_types || []}
                    onChange={(e) =>
                      set(
                        "banner_shot_types",
                        Array.from(e.target.selectedOptions, (o) => o.value),
                      )
                    }
                  >
                    {shotTypes
                      .filter((s) => s !== "unknown")
                      .map((s) => (
                        <option key={s} value={s}>
                          {label(s)}
                        </option>
                      ))}
                  </select>
                  {controls("banner_shot_types")}
                </div>
              </>
            )}
            {numericRules
              .filter((r) => r.group === section)
              .map((r) => (
                <div className="rule-row" key={r.key}>
                  <div>
                    <strong>{r.title}</strong>
                    <p>{r.hint}</p>
                    <small className={r.key in value ? "override-text" : ""}>
                      {source(r.key)}
                    </small>
                  </div>
                  <input
                    aria-label={r.title}
                    type="number"
                    min={0}
                    max={r.max}
                    step={r.step}
                    disabled={!(r.key in value)}
                    value={Number(effective[r.key])}
                    onChange={(e) => set(r.key, Number(e.target.value))}
                  />
                  {controls(r.key)}
                </div>
              ))}
            {section === "Required photos" && (
              <>
                <div className="rule-row">
                  <div>
                    <strong>Required shots & order</strong>
                    <p>
                      Optional shots may appear between required shots. Add the
                      required shot types in their intended order.
                    </p>
                    <small>{source("required_shots")}</small>
                  </div>
                  {controls("required_shots")}
                </div>
                <ol className="required-shots">
                  {effective.required_shots.map((s, i) => (
                    <li key={s}>
                      <span>{label(s)}</span>
                      {"required_shots" in value && (
                        <div>
                          <button
                            type="button"
                            aria-label={`Move ${s} up`}
                            disabled={i === 0}
                            onClick={() => move(i, i - 1)}
                          >
                            <ArrowUp size={14} />
                          </button>
                          <button
                            type="button"
                            aria-label={`Move ${s} down`}
                            disabled={i === effective.required_shots.length - 1}
                            onClick={() => move(i, i + 1)}
                          >
                            <ArrowDown size={14} />
                          </button>
                          <button
                            type="button"
                            aria-label={`Remove ${s}`}
                            onClick={() =>
                              set(
                                "required_shots",
                                effective.required_shots.filter((x) => x !== s),
                              )
                            }
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      )}
                    </li>
                  ))}
                </ol>
                {!effective.required_shots.length && (
                  <p className="form-note">
                    No required shot types configured yet.
                  </p>
                )}
                {"required_shots" in value && (
                  <div className="button-row">
                    <select
                      aria-label="Add required shot"
                      value={addShot}
                      onChange={(e) => setAddShot(e.target.value)}
                    >
                      <option value="">Choose a shot type</option>
                      {shotTypes
                        .filter(
                          (s) =>
                            s !== "unknown" &&
                            !effective.required_shots.includes(s),
                        )
                        .map((s) => (
                          <option key={s} value={s}>
                            {label(s)}
                          </option>
                        ))}
                    </select>
                    <button
                      type="button"
                      className="button secondary"
                      disabled={!addShot}
                      onClick={() => {
                        set("required_shots", [
                          ...effective.required_shots,
                          addShot,
                        ]);
                        setAddShot("");
                      }}
                    >
                      Add shot
                    </button>
                  </div>
                )}
                <div className="rule-row">
                  <div>
                    <strong>Enforce required-shot sequence</strong>
                    <p>
                      Checked only after all photos have a usable shot type.
                    </p>
                    <small>{source("strict_sequence")}</small>
                  </div>
                  <input
                    aria-label="Enforce sequence"
                    type="checkbox"
                    checked={effective.strict_sequence}
                    disabled={!("strict_sequence" in value)}
                    onChange={(e) => set("strict_sequence", e.target.checked)}
                  />
                  {controls("strict_sequence")}
                </div>
              </>
            )}
          </section>
        ),
      )}
    </div>
  );
}
