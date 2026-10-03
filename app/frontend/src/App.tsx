import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  ArrowRight,
  Bell,
  Building2,
  Camera,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  FlaskConical,
  Images,
  LayoutDashboard,
  Menu,
  ScanLine,
  Settings2,
  ShieldCheck,
  UploadCloud,
  X,
  AlertTriangle,
  TrendingUp,
} from "lucide-react";
import { api, localDate, send, thumbnail, useStored } from "./api";
import { Badge, Empty, ErrorBox, Modal, VehicleCard } from "./ui";
import { Upload } from "./Upload";
import { Browse, ReviewQueue } from "./Browse";
import { Detail } from "./Detail";
import { Setup } from "./Setup";
import type { Config, DashboardData, Notify, Page } from "./types";

const pages: {
  id: Page;
  title: string;
  icon: typeof Camera;
  description: string;
}[] = [
  {
    id: "dashboard",
    title: "Dashboard",
    icon: LayoutDashboard,
    description: "A clear view of your photography workflow.",
  },
  {
    id: "evaluate",
    title: "Evaluate Vehicle",
    icon: ScanLine,
    description:
      "Import a shoot, arrange the sequence, and check photo quality.",
  },
  {
    id: "results",
    title: "Vehicle Results",
    icon: Camera,
    description: "Every evaluation, organized and easy to find.",
  },
  {
    id: "review",
    title: "Review Queue",
    icon: ShieldCheck,
    description: "Give the photos that need attention a closer look.",
  },
  {
    id: "library",
    title: "Photo Library",
    icon: Images,
    description: "Browse your original operational photos by vehicle.",
  },
  {
    id: "training",
    title: "Training Library",
    icon: FlaskConical,
    description: "Teach the system what great vehicle photography looks like.",
  },
  {
    id: "dealerships",
    title: "Dealership Setup",
    icon: Building2,
    description: "Manage your stores, people, and photography standards.",
  },
  {
    id: "models",
    title: "Models & Help",
    icon: Settings2,
    description:
      "See what is available, and manage your local model candidates.",
  },
];

export default function App() {
  const [page, setPage] = useStored<Page>("qc:page", "dashboard");
  const [config, setConfig] = useState<Config | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [configVersion, setConfigVersion] = useState(0);
  const [connectionError, setConnectionError] = useState("");
  const [detail, setDetail] = useState<{
    id: string;
    photo?: string;
    review?: string;
  } | null>(null);
  const [trainingUpload, setTrainingUpload] = useState(false);
  const [menu, setMenu] = useState(false);
  const [toast, setToast] = useState<{
    message: string;
    error: boolean;
  } | null>(null);
  const [severeOnly, setSevereOnly] = useState(0);
  const scrolls = useRef<Record<string, number>>({});
  const main = useRef<HTMLElement>(null);
  const notify: Notify = useCallback(
    (message, error = false) => setToast({ message, error }),
    [],
  );
  const changed = () => setRefresh((v) => v + 1);
  const navigate = (next: Page) => {
    if (main.current) scrolls.current[page] = main.current.scrollTop;
    setPage(next);
    setMenu(false);
  };
  const open = (id: string, photo?: string, review?: string) =>
    setDetail({ id, photo, review });
  useEffect(() => {
    api<Config>("/config")
      .then((c) => {
        setConfig(c);
        setConnectionError("");
      })
      .catch((e) => setConnectionError(e.message));
  }, [configVersion]);
  useEffect(() => {
    const controller = new AbortController();
    api<DashboardData>(`/dashboard?today=${localDate()}`, {
      signal: controller.signal,
    })
      .then((d) => {
        setDashboard(d);
        setConnectionError("");
      })
      .catch((e) => {
        if (e.name !== "AbortError")
          setConnectionError(
            "The local server is unavailable. Start the app, then retry.",
          );
      });
    return () => controller.abort();
  }, [refresh]);
  useEffect(() => {
    const timer = setInterval(() => setRefresh((v) => v + 1), 5000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (main.current) main.current.scrollTop = scrolls.current[page] || 0;
  }, [page]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), toast.error ? 10000 : 5000);
    return () => clearTimeout(timer);
  }, [toast]);
  const info = pages.find((p) => p.id === page) || pages[0];
  return (
    <div className="app-shell">
      {menu && (
        <button
          className="menu-scrim"
          aria-label="Close navigation"
          onClick={() => setMenu(false)}
        />
      )}
      <aside className={`sidebar ${menu ? "open" : ""}`}>
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate("dashboard");
          }}
        >
          <span className="brand-mark">
            <ScanLine size={26} />
          </span>
          <span>
            Vehicle<span>PHOTO QC</span>
          </span>
        </a>
        <div className="workspace-label">
          LOCAL WORKSPACE <span>v0.1</span>
        </div>
        <nav aria-label="Main navigation">
          {pages.map((p, i) => (
            <button
              key={p.id}
              className={`${page === p.id ? "active" : ""} ${i === 5 ? "nav-divider" : ""}`}
              onClick={() => navigate(p.id)}
            >
              <p.icon size={19} />
              <span>{p.title}</span>
              {p.id === "review" && !!dashboard?.review_count && (
                <b className="nav-count">{dashboard.review_count}</b>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-status">
            <span /> Runs on your computer
          </div>
          <p>
            Your photos stay local.
            <br />
            Your standards stay in focus.
          </p>
          <button onClick={() => navigate("models")}>
            <CircleHelp size={16} /> Prototype guide <ChevronRight size={15} />
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMenu(true)}
            >
              <Menu />
            </button>
            <span>WORKSPACE</span>
            <ChevronRight size={14} />
            <strong>{info.title}</strong>
          </div>
          <div>
            <span className="desktop-only subtle-pill">Local prototype</span>
            <button
              className="notification-button"
              aria-label={`Review queue, ${dashboard?.review_count || 0} items`}
              onClick={() => navigate("review")}
            >
              <Bell size={20} />
              {!!dashboard?.review_count && (
                <span>{dashboard.review_count}</span>
              )}
            </button>
            <div
              className="avatar"
              title="Local workspace; accounts are not enabled"
            >
              L
            </div>
          </div>
        </header>
        <main ref={main} className="main-content">
          <div className="page-heading">
            <div>
              <span className="eyebrow">
                VEHICLE PHOTOGRAPHY / QUALITY CONTROL
              </span>
              <h1>{info.title}</h1>
              <p>{info.description}</p>
            </div>
            {!["evaluate", "training", "dealerships"].includes(page) && (
              <button
                className="button primary"
                onClick={() => navigate("evaluate")}
              >
                <UploadCloud size={17} /> Evaluate vehicle
              </button>
            )}
          </div>
          {connectionError && (
            <>
              <ErrorBox message={connectionError} />
              <button
                className="button secondary"
                onClick={() => {
                  setConfigVersion((v) => v + 1);
                  changed();
                }}
              >
                Retry connection
              </button>
            </>
          )}
          {!config ? (
            <div className="loading">Connecting to your local workspace…</div>
          ) : (
            <>
              <section hidden={page !== "dashboard"}>
                <Dashboard
                  data={dashboard}
                  navigate={navigate}
                  open={(id, photo) => {
                    navigate("library");
                    open(id, photo);
                  }}
                  serious={() => {
                    setSevereOnly((v) => v + 1);
                    navigate("review");
                  }}
                />
              </section>
              <section hidden={page !== "evaluate"}>
                <Upload
                  config={config}
                  notify={notify}
                  done={(id) => {
                    changed();
                    navigate("results");
                    open(id);
                  }}
                />
              </section>
              {(["results", "library", "training"] as const).map((kind) => (
                <section hidden={page !== kind} key={kind}>
                  <Browse
                    kind={kind}
                    active={page === kind}
                    config={config}
                    refresh={refresh}
                    open={open}
                    upload={() =>
                      kind === "training"
                        ? setTrainingUpload(true)
                        : navigate("evaluate")
                    }
                    notify={notify}
                  />
                </section>
              ))}
              <section hidden={page !== "review"}>
                <ReviewQueue
                  active={page === "review"}
                  config={config}
                  refresh={refresh}
                  open={open}
                  severeOnly={severeOnly}
                  notify={notify}
                />
              </section>
              <section hidden={page !== "dealerships"}>
                <Setup
                  config={config}
                  reload={() => setConfigVersion((v) => v + 1)}
                  notify={notify}
                />
              </section>
              <section hidden={page !== "models"}>
                <Models
                  active={page === "models"}
                  refresh={refresh}
                  notify={notify}
                  changed={changed}
                />
              </section>
            </>
          )}
          <footer className="page-footer">
            Vehicle Photo QC{" "}
            <span>Local prototype · Technical scores are provisional</span>
          </footer>
        </main>
      </div>
      <nav className="bottom-nav" aria-label="Mobile navigation">
        {[
          { id: "dashboard", title: "Home", icon: LayoutDashboard },
          { id: "evaluate", title: "Evaluate", icon: ScanLine },
          { id: "review", title: "Review", icon: ShieldCheck },
          { id: "library", title: "Library", icon: Images },
        ].map((p) => (
          <button
            className={page === p.id ? "active" : ""}
            key={p.id}
            onClick={() => navigate(p.id as Page)}
          >
            <p.icon size={20} />
            <span>
              {p.title}
              {p.id === "review" && !!dashboard?.review_count
                ? ` (${dashboard.review_count})`
                : ""}
            </span>
          </button>
        ))}
        <button onClick={() => setMenu(true)}>
          <Menu size={20} />
          <span>More</span>
        </button>
      </nav>
      {detail && config && (
        <Detail
          key={detail.id}
          id={detail.id}
          initialPhoto={detail.photo}
          initialReview={detail.review}
          config={config}
          close={() => {
            setDetail(null);
            changed();
          }}
          notify={notify}
          changed={changed}
        />
      )}
      {trainingUpload && config && (
        <Modal
          title="Upload training data"
          onClose={() => setTrainingUpload(false)}
          wide
        >
          <Upload
            config={config}
            training
            notify={notify}
            done={(id) => {
              setTrainingUpload(false);
              changed();
              open(id);
            }}
          />
        </Modal>
      )}
      {toast && <Toast toast={toast} dismiss={() => setToast(null)} />}
    </div>
  );
}

function Toast({
  toast,
  dismiss,
}: {
  toast: { message: string; error: boolean };
  dismiss: () => void;
}) {
  const [target, setTarget] = useState<Element>(document.body);
  useEffect(() => {
    const update = () =>
      setTarget(
        Array.from(document.querySelectorAll("dialog[open]")).at(-1) ||
          document.body,
      );
    update();
    const observer = new MutationObserver(update);
    observer.observe(document.body, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["open"],
    });
    return () => observer.disconnect();
  }, []);
  return createPortal(
    <div
      className={`toast ${toast.error ? "error" : ""}`}
      role={toast.error ? "alert" : "status"}
    >
      {toast.error ? <AlertTriangle size={19} /> : <CheckCircle2 size={19} />}
      <span>{toast.message}</span>
      <button onClick={dismiss} aria-label="Dismiss notification">
        <X size={16} />
      </button>
    </div>,
    target,
  );
}

function Dashboard({
  data,
  navigate,
  open,
  serious,
}: {
  data: DashboardData | null;
  navigate: (p: Page) => void;
  open: (id: string, photo?: string) => void;
  serious: () => void;
}) {
  if (!data) return <div className="loading">Loading overview…</div>;
  return (
    <>
      <section className="recent-strip panel">
        <div className="section-heading">
          <h2>Recently uploaded</h2>
          <button className="text-button" onClick={() => navigate("library")}>
            Open library <ArrowRight size={15} />
          </button>
        </div>
        {data.recent_photos.length ? (
          <div className="recent-photos">
            {data.recent_photos.map((p) => (
              <button key={p.id} onClick={() => open(p.shoot_id, p.id)}>
                <img
                  src={thumbnail(p.id)}
                  alt={`${p.stock || "Vehicle"} photo ${p.position}`}
                />
                <span>
                  {p.stock || "Vehicle"} · {p.position}
                </span>
              </button>
            ))}
          </div>
        ) : (
          <div className="recent-empty">
            <Camera size={25} />
            <span>
              Your latest photos will appear here.
              <small>Upload a shoot to start your photo library.</small>
            </span>
            <button
              className="button secondary"
              onClick={() => navigate("evaluate")}
            >
              Upload photos <ArrowRight size={15} />
            </button>
          </div>
        )}
      </section>
      <div className="stat-grid">
        {[
          {
            title: "PHOTOS TODAY",
            value: data.photos_today,
            foot: `${data.shoots_today} vehicle shoots`,
            icon: Images,
          },
          {
            title: "VEHICLES IN LIBRARY",
            value: data.total_shoots,
            foot: "All evaluated shoots",
            icon: Camera,
          },
          {
            title: "AVG. TECHNICAL SCORE",
            value:
              data.average_score === null
                ? "—"
                : Math.round(data.average_score),
            foot: "Provisional · not full vehicle QC",
            icon: TrendingUp,
          },
          {
            title: "AWAITING REVIEW",
            value: data.review_count,
            foot: `${data.unviewed_count} not yet viewed`,
            icon: ShieldCheck,
          },
        ].map((s, i) => (
          <button
            className="stat-card"
            key={s.title}
            onClick={() => navigate(i === 3 ? "review" : "results")}
          >
            <div>
              <span>{s.title}</span>
              <s.icon size={18} />
            </div>
            <strong>{s.value}</strong>
            <small>{s.foot}</small>
          </button>
        ))}
      </div>
      <div className="dashboard-split">
        <button className="serious-card" onClick={serious}>
          <span className="serious-icon">
            <AlertTriangle size={23} />
          </span>
          <div>
            <span className="eyebrow">PRIORITY ATTENTION</span>
            <h2>
              {data.severe_count
                ? `${data.severe_count} serious ${data.severe_count === 1 ? "issue" : "issues"} to review`
                : "Serious issues, clearly in view"}
            </h2>
            <p>
              {data.severe_count
                ? "Check the highlighted photos before they move on."
                : "When serious concerns are detected, they appear here for a closer look."}
            </p>
            <strong>
              Open priority review queue <ArrowRight size={17} />
            </strong>
          </div>
        </button>
        <div className="panel readiness">
          <div className="inline">
            <FlaskConical size={20} />
            <h3>Training foundation</h3>
          </div>
          <strong>
            {data.approved_count}
            <span> / {data.training_count}</span>
          </strong>
          <p>examples approved for training</p>
          <div className="progress-track">
            <div
              style={{
                width: `${data.training_count ? (data.approved_count / data.training_count) * 100 : 0}%`,
              }}
            />
          </div>
          <button className="text-button" onClick={() => navigate("training")}>
            Build your library <ArrowRight size={15} />
          </button>
        </div>
      </div>
      <div className="dashboard-bottom">
        <section>
          <div className="section-heading">
            <h2>Recent vehicle shoots</h2>
            <button className="text-button" onClick={() => navigate("results")}>
              View all <ArrowRight size={15} />
            </button>
          </div>
          {data.recent_shoots.length ? (
            <div className="vehicle-list">
              {data.recent_shoots.map((s) => (
                <VehicleCard key={s.id} shoot={s} open={open} />
              ))}
            </div>
          ) : (
            <div className="panel">
              <Empty
                title="Ready for your first vehicle"
                action={
                  <button
                    className="button primary"
                    onClick={() => navigate("evaluate")}
                  >
                    Evaluate a vehicle <ArrowRight size={16} />
                  </button>
                }
              >
                Select a dealership, add your photos, and arrange them into the
                right sequence.
              </Empty>
            </div>
          )}
        </section>
        <section className="panel trend">
          <div className="section-heading">
            <h3>Technical quality</h3>
            <TrendingUp size={18} />
          </div>
          <p>Average by shoot date</p>
          {data.trend.length ? (
            <div className="trend-bars">
              {data.trend.map((t) => (
                <div key={t.date}>
                  <span>{t.date.slice(5)}</span>
                  <div>
                    <i style={{ width: `${t.score}%` }} />
                  </div>
                  <strong>{Math.round(t.score)}</strong>
                </div>
              ))}
            </div>
          ) : (
            <div className="trend-empty">
              <TrendingUp size={34} />
              <p>Your quality trend will appear after the first analysis.</p>
            </div>
          )}
          <div className="trend-note">
            <Badge tone="teal">BASELINE CHECKS</Badge>
            <p>
              Sharpness, exposure, and saturation are available. Vehicle
              recognition comes after model training.
            </p>
          </div>
        </section>
      </div>
    </>
  );
}

interface Model {
  id: string;
  name: string;
  status: string;
  created_at: string;
  metrics: Record<string, unknown>;
  classes: string[];
}
function Models({
  active,
  refresh,
  notify,
  changed,
}: {
  active: boolean;
  refresh: number;
  notify: Notify;
  changed: () => void;
}) {
  const [models, setModels] = useState<Model[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (active)
      api<Model[]>("/models")
        .then((m) => {
          setModels(m);
          setError("");
        })
        .catch((e) => setError(e.message));
  }, [active, refresh]);
  async function activate(id?: string) {
    setBusy(true);
    try {
      await send(id ? `/models/${id}/activate` : "/models/deactivate", "POST");
      changed();
      notify(
        id
          ? "Model activated for future analyses."
          : "Automatic classification disabled.",
      );
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="panel">
        <span className="eyebrow">WHAT THIS VERSION DOES</span>
        <h2>A working foundation, with honest limits.</h2>
        <div className="capability-grid">
          <div>
            <h3>Available now</h3>
            <ul>
              <li>Original photo storage, EXIF, thumbnails, ordering</li>
              <li>Sharpness, exposure, and saturation estimates</li>
              <li>Human shot labels and required-shot rules</li>
              <li>Review notes, history, and resolution</li>
              <li>Approved datasets and optional shot-classifier training</li>
            </ul>
          </div>
          <div>
            <h3>Still to be validated</h3>
            <ul>
              <li>Vehicle detection and segmentation</li>
              <li>Critical crop and exterior-angle judgments</li>
              <li>Automatic banner overlap checks</li>
              <li>Plastic, floor mats, and steering-wheel checks</li>
              <li>Phone access over a network, accounts, HomeNet</li>
            </ul>
          </div>
        </div>
        <p className="form-note">
          This prototype is bound to your PC. The layout adapts to phone
          screens, but external access is a separate deployment step.
        </p>
        <a
          className="button secondary"
          href="https://github.com/GittyHubUser410/vehicle-photo-qc/blob/main/README.md"
          target="_blank"
          rel="noreferrer"
        >
          Open setup & user guide <ArrowRight size={16} />
        </a>
      </div>
      <div className="section-heading">
        <div>
          <h2>Shot-classification models</h2>
          <p className="form-note">
            Train locally using the documented command. New models remain
            candidates until you activate one.
          </p>
        </div>
        <button
          className="button secondary"
          disabled={busy || !models.some((m) => m.status === "active")}
          onClick={() => activate()}
        >
          Disable classification
        </button>
      </div>
      {error && <ErrorBox message={error} />}
      {!models.length ? (
        <Empty title="No trained models yet">
          Start by labeling real shoots and exporting an approved dataset.
          Technical checks work without a model.
        </Empty>
      ) : (
        models.map((m) => (
          <div className="panel model-card" key={m.id}>
            <div className="section-heading">
              <div>
                <h3>{m.name}</h3>
                <small>{new Date(m.created_at).toLocaleString()}</small>
              </div>
              <Badge tone={m.status === "active" ? "teal" : ""}>
                {m.status}
              </Badge>
            </div>
            <p>{m.classes.length} shot classes</p>
            <details>
              <summary>Validation metrics</summary>
              <pre>{JSON.stringify(m.metrics, null, 2)}</pre>
            </details>
            <p className="form-note">
              Review class-level performance and a fixed holdout set before
              activation. A higher aggregate score can hide weak classes.
            </p>
            {m.status !== "active" && (
              <button
                className="button primary"
                disabled={busy}
                onClick={() => activate(m.id)}
              >
                Activate this model
              </button>
            )}
          </div>
        ))
      )}
    </>
  );
}
