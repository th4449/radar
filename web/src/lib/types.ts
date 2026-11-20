export type ReviewerStatus = "pending" | "approved" | "suspended";
export type SiteStatus = "candidate" | "in_review" | "confirmed" | "rejected";
export type Decision = "confirm" | "reject" | "unsure";

export interface Reviewer {
  user_id: string;
  display_name: string;
  status: ReviewerStatus;
  role: "reviewer" | "admin";
  applied_at: string;
  approved_at: string | null;
}

export interface Contribution {
  signal_type: string;
  signal_id: number | null;
  event_date: string;
  points: number;
  confidence: number;
  age_days: number;
  decay: number;
  value: number;
}

export interface ScoreDetail {
  as_of?: string;
  score?: number;
  placeholder?: boolean;
  signals_total?: number;
  signals_counted?: number;
  contributions?: Contribution[];
  bonus?: { points: number; types: string[] };
}

export interface Site {
  id: number;
  state: string;
  county_fips: string;
  label: string;
  status: SiteStatus;
  score: number;
  score_detail: ScoreDetail;
  scored_at: string | null;
  first_signal_at: string | null;
}

export interface Reason {
  rule: string;
  term?: string;
  field?: string;
  text?: string;
  match?: string;
  listed_as?: { name: string; role: string; data_center: string }[];
}

export interface Signal {
  id: number;
  document_id: number;
  signal_type: string;
  event_date: string;
  summary: string;
  confidence: number | null;
  county_fips: string | null;
  extracted: Record<string, unknown> & { reasons?: Reason[] };
  entities: { name: string; kind: string } | null;
}

export interface DocumentRef {
  id: number;
  source_name: string;
  source_slug: string;
  url: string;
  retrieved_at: string;
  sha256: string;
  restricted: boolean;
}

export interface Review {
  id: number;
  site_id: number;
  reviewer_id: string;
  decision: Decision;
  note: string | null;
  source_checked: boolean;
  created_at: string;
  reversed_at: string | null;
  reversal_note: string | null;
}

export interface Alert {
  id: number;
  site_id: number;
  headline: string;
  body: string;
  published_at: string | null;
  confirmed_by_count: number;
}
