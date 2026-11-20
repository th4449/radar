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
