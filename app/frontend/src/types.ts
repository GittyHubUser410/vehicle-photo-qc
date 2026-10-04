export interface Rules {
  banner_application: "none" | "first" | "all";
  banner_shot_types: string[];
  blur_min: number;
  dark_max: number;
  bright_max: number;
  saturation_max: number;
  min_photos: number;
  required_shots: string[];
  strict_sequence: boolean;
  banner_top_pct: number;
  banner_clearance_pct: number;
  angle_tolerance_deg: number;
}
export interface Policy {
  rules: Rules;
  origins: Record<string, string>;
  dealer_version: number | null;
  group_version: number | null;
  group_name?: string;
}
export interface Group {
  id: string;
  name: string;
  rules: Partial<Rules>;
  version: number;
}
export interface Dealer {
  id: string;
  name: string;
  group_id: string | null;
  new_rules: Partial<Rules>;
  used_rules: Partial<Rules>;
  effective_new: Policy;
  effective_used: Policy;
  version: number;
}
export interface Config {
  groups: Group[];
  dealerships: Dealer[];
  photographers: { id: string; name: string }[];
  shot_types: string[];
  shot_catalog: {
    key: string;
    label: string;
    position: number;
    archived: boolean;
  }[];
  shot_type_labels: Record<string, string>;
  default_rules: Rules;
}
export interface Training {
  id: string;
  labels: Record<string, string>;
  eligible: boolean;
  revision: number;
  labeled_by: string;
  updated_at: string;
}
export interface Photo {
  banner: {
    applicable: boolean | null;
    mode: string;
    check: string;
    top_fraction: number;
    clearance_fraction: number;
  };
  id: string;
  shoot_id: string;
  position: number;
  original_filename: string;
  display_filename: string;
  width: number;
  height: number;
  byte_size: number;
  exif: Record<string, string>;
  shot_type: string;
  training: Training | null;
  analysis: {
    score: number;
    metrics: Record<string, number>;
    predicted_shot: string | null;
    confidence: number | null;
  } | null;
}
export interface Issue {
  id: string;
  photo_id: string | null;
  kind: string;
  severity: string;
  description: string;
}
export interface Review {
  id: string;
  shoot_id: string;
  photo_id: string | null;
  run_id: string;
  reason: string;
  severity: string;
  viewed_at: string | null;
  resolved_at: string | null;
  note: string;
  created_at: string;
  resolution: string | null;
  shoot?: Shoot;
  events?: {
    id: string;
    action: string;
    actor: string;
    note: string;
    created_at: string;
  }[];
}
export interface Shoot {
  id: string;
  dealership_id: string | null;
  dealership_name: string;
  photographer_id: string | null;
  source: string;
  metadata_revision: number;
  concerns: string[];
  photographer_name: string;
  stock_number: string;
  inventory_type: string;
  year: number | null;
  make: string;
  model: string;
  trim: string;
  color: string;
  shoot_date: string;
  season: string;
  lighting: string;
  ground: string;
  location: string;
  note: string;
  purpose: string;
  mode: string;
  status: string;
  error: string | null;
  score: number | null;
  photo_count: number;
  review_count: number;
  issue_count: number;
  previously_queued: boolean;
  previews: { id: string; position: number }[];
  policy: Policy;
  checks: Record<string, string>;
  current_run_id: string | null;
}
export interface Detail extends Shoot {
  photos: Photo[];
  issues: Issue[];
  reviews: Review[];
  runs: {
    id: string;
    created_at: string;
    pipeline_version: string;
    status: string;
    model_version_id: string | null;
  }[];
}
export interface DashboardData {
  total_shoots: number;
  photos_today: number;
  shoots_today: number;
  average_score: number | null;
  review_count: number;
  severe_count: number;
  unviewed_count: number;
  training_count: number;
  approved_count: number;
  recent_photos: {
    id: string;
    shoot_id: string;
    stock: string;
    position: number;
  }[];
  recent_shoots: Shoot[];
  trend: { date: string; score: number; count: number }[];
}
export type Page =
  | "dashboard"
  | "evaluate"
  | "results"
  | "review"
  | "library"
  | "training"
  | "dealerships"
  | "models"
  | "trash";
export type OpenDetail = (
  id: string,
  photoId?: string,
  reviewId?: string,
) => void;
export type Notify = (message: string, error?: boolean) => void;
