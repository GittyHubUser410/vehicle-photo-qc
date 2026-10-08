import { useEffect, useRef, type ReactNode } from "react";
import {
  Camera,
  X,
  ArrowUpRight,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { label, thumbnail, vehicleName } from "./api";
import type { Shoot, OpenDetail, Evidence } from "./types";

export function Empty({
  title,
  children,
  action,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Camera size={30} />
      </div>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
export function Badge({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function Score({
  value,
  small = false,
}: {
  value: number | null;
  small?: boolean;
}) {
  return (
    <span
      title="Provisional technical score, not a full vehicle-quality score"
      className={`score ${small ? "small" : ""} ${value !== null && value < 70 ? "low" : ""}`}
    >
      {value === null ? "—" : Math.round(value)}
    </span>
  );
}
export function Field({
  title,
  children,
  hint,
}: {
  title: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>{title}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="error-box" role="alert">
      <AlertCircle size={18} />
      <span>{message}</span>
    </div>
  );
}
export function Modal({
  title,
  onClose,
  children,
  wide = false,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current!;
    dialog.showModal();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = overflow;
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal ${wide ? "wide" : ""}`}
      onCancel={(event) => {
        event.stopPropagation();
        onClose();
      }}
      aria-label={title}
    >
      <div className="modal-bar">
        <h2>{title}</h2>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Close details"
        >
          <X />
        </button>
      </div>
      <div className="modal-body">{children}</div>
    </dialog>
  );
}
export function VehicleCard({
  shoot,
  open,
}: {
  shoot: Shoot;
  open: OpenDetail;
}) {
  return (
    <button className="vehicle-card" onClick={() => open(shoot.id)}>
      <div className="vehicle-preview">
        {shoot.previews[0] ? (
          <img
            src={thumbnail(shoot.previews[0].id)}
            alt={vehicleName(shoot)}
            loading="lazy"
          />
        ) : (
          <Camera />
        )}
        <span>{shoot.photo_count} photos</span>
      </div>
      <div className="vehicle-copy">
        <div className="eyebrow">
          {shoot.stock_number || "No stock number"}{" "}
          <Badge>{shoot.inventory_type}</Badge>
        </div>
        <h3>{vehicleName(shoot)}</h3>
        <p>
          {shoot.dealership_name} <span>·</span> {shoot.shoot_date}
        </p>
        <div className="vehicle-meta">
          <span>{shoot.photographer_name}</span>
          {shoot.status !== "complete" ? (
            <Badge tone={shoot.status === "failed" ? "danger" : "warn"}>
              {label(shoot.status)}
            </Badge>
          ) : shoot.review_count ? (
            <Badge tone="warn">{shoot.review_count} to review</Badge>
          ) : (
            <span className="muted inline">
              <CheckCircle2 size={14} /> No open reviews
            </span>
          )}
        </div>
      </div>
      <div className="vehicle-end">
        <Score value={shoot.score} />
        <small>Technical</small>
        <small>
          QC {label(shoot.qc_evidence.coverage)} ·{" "}
          {label(shoot.qc_evidence.freshness)}
        </small>
      </div>
      <ArrowUpRight className="card-arrow" size={18} />
    </button>
  );
}

export function EvidenceBadge({ evidence }: { evidence?: Evidence }) {
  const state = evidence?.state || "legacy_unverified";
  return (
    <span
      title={
        evidence?.state === "verified"
          ? `${evidence.actor_display} (${label(evidence.actor_basis)}) · ${evidence.recorded_at}`
          : "A stored value is separate from human verification."
      }
    >
      <Badge tone={state === "verified" ? "" : "warn"}>{label(state)}</Badge>
    </span>
  );
}
