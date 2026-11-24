import { supabase } from "./supabase";

/** One source record behind an alert, as the public view gives it. */
export interface SourceRef {
  url: string;
  source: string;
  retrieved_at: string;
  sha256: string;
  signal_type: string;
  event_date: string;
  /** The record's own number, such as a well report's tracking number. Null on older signals. */
  reference: string | null;
}

/** A confirmed, published alert. The only thing the anonymous key can read. */
export interface PublicAlert {
  alert_id: number;
  site_id: number;
  headline: string;
  body: string;
  published_at: string;
  confirmed_by_count: number;
  status: string;
  state: string;
  county_fips: string;
  label: string;
  geometry: { type: string; coordinates: unknown } | null;
  sources: SourceRef[];
  /** Payers in the QPQ Tracker's study whose name a record's company has. Often empty. */
  study_payers: { name: string; url: string }[];
}

const COLUMNS =
  "alert_id, site_id, headline, body, published_at, confirmed_by_count, status, state, " +
  "county_fips, label, geometry, sources, study_payers";

export async function fetchAlerts(where: { state?: string; county?: string }): Promise<PublicAlert[]> {
  let query = supabase.from("public_alerts").select(COLUMNS);
  if (where.state) query = query.eq("state", where.state);
  if (where.county) query = query.eq("county_fips", where.county);
  const { data, error } = await query.order("published_at", { ascending: false }).limit(500);
  if (error) throw error;
  return (data ?? []) as unknown as PublicAlert[];
}

export async function fetchAlert(id: number): Promise<PublicAlert | null> {
  const { data, error } = await supabase
    .from("public_alerts")
    .select(COLUMNS)
    .eq("alert_id", id)
    .maybeSingle();
  if (error) throw error;
  return (data as unknown as PublicAlert | null) ?? null;
}

/** [longitude, latitude] when the alert's site has a point on record. */
export function pointOf(alert: PublicAlert): [number, number] | null {
  const g = alert.geometry;
  if (!g || g.type !== "Point" || !Array.isArray(g.coordinates)) return null;
  const [lng, lat] = g.coordinates as unknown[];
  if (typeof lng !== "number" || typeof lat !== "number") return null;
  if (lng < -180 || lng > 180 || lat < -90 || lat > 90) return null;
  return [lng, lat];
}

export function recordCount(count: number): string {
  return count === 1 ? "1 public record" : `${count} public records`;
}

/** Only a web address is ever made into a link. */
export function safeUrl(url: string): string | null {
  return /^https?:\/\//i.test(url) ? url : null;
}
