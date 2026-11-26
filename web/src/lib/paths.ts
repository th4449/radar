// Where the site sits on its domain, and every address inside it.
//
// The site is built to live at the root of a domain or under a path on someone else's, such
// as standuptocorruption.org/radar. The path is set when the site is built, with
// RADAR_BASE_PATH. See astro.config.mjs and the README.
//
// **Every link, redirect and sign-in address goes through `href()`.** An address written by
// hand from the root, like "/tx/", leaves the radar when the site is under a path. A test
// reads the source and fails on one.

/** "" at the root of a domain, "/radar" under a path. Never ends in a slash. */
export function basePrefix(base: string | undefined): string {
  const trimmed = (base ?? "").trim().replace(/^\/+|\/+$/g, "");
  return trimmed ? `/${trimmed}` : "";
}

/** The address of a page of the site, given where the site sits. */
export function joinBase(base: string | undefined, path: string): string {
  if (!path.startsWith("/") || path.startsWith("//")) {
    throw new Error(`a path inside the site must start with one slash: ${JSON.stringify(path)}`);
  }
  return basePrefix(base) + path;
}

// Astro sets BASE_URL when it builds. Outside a build, in a test, there is none.
const BASE: string | undefined = (import.meta as { env?: { BASE_URL?: string } }).env?.BASE_URL;

/** The address of a page of this site: `href("/tx/")`, `href(`/alert/?id=${id}`)`. */
export function href(path: string): string {
  return joinBase(BASE, path);
}

/** The whole address, for the link a sign-in email sends a person back to. */
export function absolute(path: string): string {
  return window.location.origin + href(path);
}
