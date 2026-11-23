// The states, counties and record sources the site names. A copy of config/, written by
// scripts/export_web_data.py and checked by tests/test_web_data.py.
import data from "./places.json" with { type: "json" };

export interface County {
  fips: string;
  name: string;
  slug: string;
}

export interface StateInfo {
  code: string;
  name: string;
  slug: string;
  counties: County[];
}

export interface SourceInfo {
  name: string;
  state: string;
  url: string;
  /** True when the radar holds this source today: a collector reads it, or a person saves it. */
  read: boolean;
  /** True when a person saves the page in a browser and no program asks the site for it. */
  by_hand: boolean;
  use: string;
}

export const STATES: StateInfo[] = data.states;
export const SOURCES: SourceInfo[] = data.sources;

const BY_FIPS = new Map<string, { county: County; state: StateInfo }>();
for (const state of STATES) {
  for (const county of state.counties) BY_FIPS.set(county.fips, { county, state });
}

export function stateByCode(code: string): StateInfo | undefined {
  return STATES.find((s) => s.code === code);
}

export function stateName(code: string): string {
  return stateByCode(code)?.name ?? code;
}

/** "Hood County". A county the site has no page for is shown by its code. */
export function countyName(fips: string): string {
  const found = BY_FIPS.get(fips);
  return found ? `${found.county.name} County` : `County ${fips}`;
}

/** "Hood County, Texas" */
export function whereLine(stateCode: string, fips: string): string {
  return `${countyName(fips)}, ${stateName(stateCode)}`;
}

/** "/tx/hood/", or null for a county with no page. */
export function countyPath(fips: string): string | null {
  const found = BY_FIPS.get(fips);
  return found ? `/${found.state.slug}/${found.county.slug}/` : null;
}

/** True when at least one of the state's record sources is read by a collector today. */
export function stateIsRead(code: string): boolean {
  return SOURCES.some((s) => s.state === code && s.read);
}
