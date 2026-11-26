// The site will live under a path on another site's domain: standuptocorruption.org/radar.
// Every link, redirect and sign-in address has to stay under that path. Written first.

import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { strayAddresses } from "./built.ts";
import { basePrefix, joinBase } from "../src/lib/paths.ts";

test("at the root of a domain a path is left as it is", () => {
  for (const base of ["/", "", undefined]) {
    assert.equal(basePrefix(base), "");
    assert.equal(joinBase(base, "/"), "/");
    assert.equal(joinBase(base, "/alert/?id=3"), "/alert/?id=3");
  }
});

test("under a path every address starts with that path", () => {
  assert.equal(joinBase("/radar", "/"), "/radar/");
  assert.equal(joinBase("/radar", "/tx/hood/"), "/radar/tx/hood/");
  assert.equal(joinBase("/radar", "/alert/?id=3"), "/radar/alert/?id=3");
  assert.equal(joinBase("/radar", "/methodology/#sources"), "/radar/methodology/#sources");
});

test("the path may be written with or without its slashes", () => {
  for (const base of ["/radar", "/radar/", "radar", "radar/", " /radar/ "]) {
    assert.equal(basePrefix(base), "/radar");
    assert.equal(joinBase(base, "/account/"), "/radar/account/");
  }
  assert.equal(joinBase("/a/b/", "/review/"), "/a/b/review/");
});

test("a path that does not start at the site's root is a mistake, not a link", () => {
  for (const bad of ["alert/", "", "https://example.org/", "//example.org/x", "../x"]) {
    assert.throws(() => joinBase("/radar", bad), /start with one slash/);
  }
});

// --- the source: no address written by hand ----------------------------------------------------

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.(astro|tsx|ts)$/.test(entry.name) ? [path] : [];
  });
}

test("no page or component writes an address from the root by hand", () => {
  // Each of these would leave the radar's path on the shared domain.
  const byHand = [
    /\b(?:href|src|action)=["'`]\/(?!\/)/, // href="/tx/"
    /\b(?:href|src|action)=\{\s*[`"']\/(?!\/)/, // href={`/alert/?id=${id}`}
    /location\.(?:assign|replace)\(\s*[`"']\//, // window.location.assign(`/alert/…`)
    /location\.href\s*=\s*[`"']\//,
    /location\.origin\}\//, // `${window.location.origin}/account/`
  ];
  const found: string[] = [];
  for (const file of sourceFiles(new URL("../src", import.meta.url).pathname)) {
    readFileSync(file, "utf8")
      .split("\n")
      .forEach((line, i) => {
        if (byHand.some((pattern) => pattern.test(line))) found.push(`${file}:${i + 1}: ${line.trim()}`);
      });
  }
  assert.deepEqual(found, []);
});

// --- a built page: nothing points outside the path ---------------------------------------------

test("a built page under /radar with every address under /radar has none astray", () => {
  const html = `<link rel="stylesheet" href="/radar/_astro/site.css">
    <a href="/radar/">Home</a> <a href="/radar/tx/">Texas</a>
    <a href="https://www.tceq.texas.gov/">An agency</a> <a href="#sources">Below</a>
    <a href="mailto:someone@example.org">Write</a> <script src="/radar/_astro/x.js"></script>`;
  assert.deepEqual(strayAddresses(html, "/radar"), []);
});

test("an address from the root of the domain is found, with what it was", () => {
  const html = `<a href="/tx/">Texas</a> <a href="/radar/mi/">Michigan</a>
    <script src="/_astro/x.js"></script> <form action="/subscribe/"></form>
    <a href="/radarish/">Not ours</a> <a href="/radar">Home with no slash</a>`;
  assert.deepEqual(strayAddresses(html, "/radar"), [
    'href="/tx/"',
    'src="/_astro/x.js"',
    'action="/subscribe/"',
    'href="/radarish/"',
  ]);
});

test("an address a script wrote by hand into a link or a redirect is found", () => {
  const js =
    'h("a",{href:"/review/",children:"Desk"});window.location.assign("/review/site/?id="+e);' +
    "x({emailRedirectTo:`${window.location.origin}/account/`})";
  assert.deepEqual(strayAddresses(js, "/radar", "script"), [
    'href:"/review/"',
    'location.assign("/review/site/?id="',
    "location.origin}/account/`",
  ]);
});

test("an address a script hands to the helper is right, and is left alone", () => {
  const js =
    'h("a",{href:f("/review/"),children:"Desk"});window.location.assign(f(`/alert/?id=${t}`));' +
    'x({emailRedirectTo:g("/account/")});h("a",{href:s.url});h("a",{href:"https://example.gov/"})';
  assert.deepEqual(strayAddresses(js, "/radar", "script"), []);
});

test("at the root of a domain nothing is astray", () => {
  assert.deepEqual(strayAddresses('<a href="/tx/">Texas</a>', "/"), []);
});
