// What a subscriber chooses, and the rules the forms keep. The database keeps the same rules:
// see db/migrations/20261120000006_public_site.sql.
import { STATES } from "./places.ts";

export type Frequency = "weekly" | "each";

export interface Choices {
  states: string[];
  /** County codes. Empty means every county in the selected states. */
  counties: string[];
  frequency: Frequency;
}

export const DEFAULT_CHOICES: Choices = { states: [], counties: [], frequency: "weekly" };

const PREFIX: Record<string, string> = { TX: "48", MI: "26" };

/** Drop counties whose state is no longer selected. The database refuses them. */
export function fitCounties(choices: Choices): Choices {
  const prefixes = choices.states.map((s) => PREFIX[s]);
  return {
    ...choices,
    counties: choices.counties.filter((fips) => prefixes.includes(fips.slice(0, 2))),
  };
}

/** The columns to write. No county list is stored as null, never as an empty list. */
export function toRow(choices: Choices): {
  states: string[];
  county_fips: string[] | null;
  frequency: Frequency;
} {
  const fitted = fitCounties(choices);
  const order = STATES.map((s) => s.code);
  return {
    states: order.filter((code) => fitted.states.includes(code)),
    county_fips: fitted.counties.length ? [...fitted.counties].sort() : null,
    frequency: fitted.frequency,
  };
}

export function fromRow(row: {
  states: string[];
  county_fips: string[] | null;
  frequency: Frequency;
}): Choices {
  return { states: row.states, counties: row.county_fips ?? [], frequency: row.frequency };
}

/** In plain words, what the person will get. */
export function describe(choices: Choices): string {
  const fitted = fitCounties(choices);
  const parts = STATES.filter((s) => fitted.states.includes(s.code)).map((state) => {
    const picked = state.counties.filter((c) => fitted.counties.includes(c.fips));
    if (picked.length === 0) return `all of ${state.name}`;
    return `${picked.map((c) => c.name).join(", ")} in ${state.name}`;
  });
  if (parts.length === 0) return "";
  const how =
    fitted.frequency === "each" ? "An email for each alert" : "A weekly digest for each state";
  return `${how}: ${parts.join(" and ")}.`;
}

// --- choices kept in the browser between the form and the emailed link -------------------------

export interface Pending {
  email: string;
  choices: Choices;
  at: number;
}

export const PENDING_KEY = "radar.pending-subscription";
const DAY_MS = 24 * 60 * 60 * 1000;

/** The choices made on the form, if they were made for this address within the last day. */
export function pendingFor(raw: string | null, email: string, now: number): Choices | null {
  if (!raw) return null;
  let found: Pending;
  try {
    found = JSON.parse(raw) as Pending;
  } catch {
    return null;
  }
  if (!found || typeof found.email !== "string" || typeof found.at !== "number") return null;
  if (found.email.trim().toLowerCase() !== email.trim().toLowerCase()) return null;
  if (now - found.at > DAY_MS || now < found.at) return null;
  const c = found.choices;
  if (!c || !Array.isArray(c.states) || !Array.isArray(c.counties)) return null;
  const states = c.states.filter((s) => s in PREFIX);
  if (states.length === 0) return null;
  return fitCounties({
    states,
    counties: c.counties.filter((f) => /^\d{5}$/.test(String(f))),
    frequency: c.frequency === "each" ? "each" : "weekly",
  });
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** The token from an unsubscribe link, or null if it is not one. */
export function tokenFrom(search: string): string | null {
  const token = new URLSearchParams(search).get("token");
  return token && UUID.test(token) ? token : null;
}

/** A whole number id from a page address such as ?id=12, or null. */
export function idFrom(search: string, key: string): number | null {
  const value = new URLSearchParams(search).get(key);
  return value && /^\d{1,12}$/.test(value) ? Number(value) : null;
}
