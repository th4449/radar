const MONTHS = [
  "January", "February", "March", "April", "May", "June", "July", "August", "September",
  "October", "November", "December",
];

/** "November 20, 2026" from an ISO date or timestamp. The date is read as written, not shifted. */
export function longDate(value: string | null | undefined): string {
  if (!value) return "";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!m) return value;
  return `${MONTHS[Number(m[2]) - 1]} ${Number(m[3])}, ${m[1]}`;
}

/**
 * The day a moment fell on where the reader is, as "November 20, 2026". For when something was
 * published, read or confirmed. A plain date, such as a record's own date, is shown as written.
 */
export function localDay(value: string | null | undefined, timeZone?: string): string {
  if (!value) return "";
  if (!/^\d{4}-\d{2}-\d{2}T/.test(value)) return longDate(value);
  const when = new Date(value);
  if (Number.isNaN(when.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", { dateStyle: "long", timeZone }).format(when);
}

export const SIGNAL_NAMES: Record<string, string> = {
  abatement_notice: "Tax abatement notice",
  air_permit: "Air permit application",
  transmission_filing: "Transmission planning file",
  commission_docket: "Commission docket",
  well_report: "Well report",
  stormwater_notice: "Stormwater notice",
  entity_land_purchase: "Land purchase",
  agenda_keyword: "Agenda item",
};

export const STATUS_NAMES: Record<string, string> = {
  candidate: "Candidate",
  in_review: "In review",
  confirmed: "Confirmed",
  rejected: "Rejected",
};

export const RULE_NAMES: Record<string, string> = {
  direct_term: "The record uses the words",
  code_word: "The record uses the code word",
  project_code_name: "The record names",
  listed_company: "The company is on the Comptroller's registered data center list",
  listed_company_loose: "The company's name is close to one on the Comptroller's list",
};

export function signalName(kind: string): string {
  return SIGNAL_NAMES[kind] ?? kind;
}

/** A message a person can act on, from whatever the database client threw. */
export function problem(error: unknown): string {
  if (error && typeof error === "object" && "message" in error) {
    return String((error as { message: unknown }).message);
  }
  return String(error);
}

/** "WellReportTrackingNumber" and "permit_number" as words a person reads. */
export function fieldName(key: string): string {
  const words = key
    .replace(/_/g, " ")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2")
    .replace(/\bDD\b/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** What a reviewer is told when the words "data center" sit beside the words of rule making.
 *
 * A moratorium or a zoning ordinance about data centers is a government writing its own rules,
 * not a project. An ordinance can rezone land for a project too, so the note names the words
 * and decides nothing. Empty when there are none. The owner approved this wording on
 * November 24, 2026. */
export function ruleMakingNote(words: unknown): string {
  const said = Array.isArray(words) ? words.filter((w) => typeof w === "string" && w) : [];
  if (said.length === 0) return "";
  const quoted = said.map((w) => `"${w}"`).join(", ");
  return (
    `Also in the item: ${quoted}. ` +
    "These are the words of a government writing its own rules. A project can use them too."
  );
}

/** Where in a file the words are, for a reviewer who opens it.
 *
 * Shown only where the numbers are the file's own. A page with no words adds nothing to the
 * stored text, so for a document stored before such pages were noted the count can run behind
 * the file. Then nothing is said. Empty for a file of one page. */
export function pagesNote(pages: unknown, total: unknown, exact: unknown): string {
  const on = Array.isArray(pages) ? pages.filter((n) => Number.isInteger(n) && n > 0) : [];
  if (exact !== true || on.length === 0 || !Number.isInteger(total) || (total as number) < 2) {
    return "";
  }
  const first = on.slice(0, 3).join(", ");
  let where = `page ${on[0]}`;
  if (on.length === 2) where = `pages ${on[0]} and ${on[1]}`;
  if (on.length === 3) where = `pages ${on[0]}, ${on[1]} and ${on[2]}`;
  if (on.length > 3) where = `pages ${first} and others`;
  return `The words are on ${where}. The file has ${total} pages.`;
}

/** A payer in the QPQ Tracker's data center study whose name a record's company has. */
export interface StudyMatch {
  basis: string;
  study_payers: { name: string; payer_class: string; url: string; states: string[] } | null;
}

const STUDY_PAGE = /^https:\/\/www\.purchasingpolicy\.org\/entity\/[0-9a-f-]{36}$/;

/** The payer's page in the study, or null. No other address is ever made into a link here. */
export function studyUrl(url: unknown): string | null {
  return typeof url === "string" && STUDY_PAGE.test(url) ? url : null;
}

function listOf(items: string[]): string {
  if (items.length < 2) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

/** What a reviewer is told when a record's company has the name of a payer in the study.
 *
 * The match is by name and the note says so. It names the study's own label and class for the
 * payer and decides nothing. Empty when there is no match. The owner approved this wording on
 * November 24, 2026. */
export function studyNote(company: unknown, match: StudyMatch | null | undefined): string {
  const payer = match?.study_payers;
  if (typeof company !== "string" || !company || !payer) return "";
  const states = (payer.states ?? []).filter((s) => typeof s === "string" && s);
  const how =
    match.basis === "same_name"
      ? "The match is by name."
      : "The match is by name, with the legal form set aside.";
  return (
    `${company} has the name of a payer in the QPQ Tracker's data center study: ` +
    `${payer.name}, class "${payer.payer_class}". ` +
    (states.length ? `The study counts its giving in the filings of ${listOf(states)}. ` : "") +
    `${how} It is not proof that the two are one company. It says nothing about this site.`
  );
}

/** What the public is told on an alert, before and after the payers' names.
 *
 * The names are the study's own labels, each linked to its page in the study. The name a
 * record gave is never shown. The owner approved this wording on November 24, 2026. */
export function studyPublicLead(count: number): string {
  return count === 1
    ? "A record behind this alert names a company with the same name as a payer in the QPQ " +
        "Tracker's study of who paid for the data centers:"
    : "Records behind this alert name companies with the same names as payers in the QPQ " +
        "Tracker's study of who paid for the data centers:";
}

export const STUDY_PUBLIC_REST =
  "The study counts companies' political giving as state filings report it. The match is by " +
  "name. It does not show that the two are one company, and it does not show that any giving " +
  "had to do with this site.";

