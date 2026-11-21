import assert from "node:assert/strict";
import { test } from "node:test";
import {
  describe,
  fitCounties,
  idFrom,
  pendingFor,
  toRow,
  tokenFrom,
} from "../src/lib/choices.ts";
import { countyName, countyPath, stateIsRead, whereLine } from "../src/lib/places.ts";

const HOOD = "48221";
const WASHTENAW = "26161";

test("a county is named, and one without a page is shown by its code", () => {
  assert.equal(countyName(HOOD), "Hood County");
  assert.equal(whereLine("TX", HOOD), "Hood County, Texas");
  assert.equal(countyPath(HOOD), "/tx/hood/");
  assert.equal(countyPath("48451"), "/tx/tom-green/");
  assert.equal(countyName("99999"), "County 99999");
  assert.equal(countyPath("99999"), null);
});

test("the site says a state is read only when a collector reads one of its sources", () => {
  assert.equal(stateIsRead("TX"), true);
  assert.equal(stateIsRead("MI"), false);
});

test("counties of a state that was unticked are dropped", () => {
  const kept = fitCounties({ states: ["TX"], counties: [HOOD, WASHTENAW], frequency: "weekly" });
  assert.deepEqual(kept.counties, [HOOD]);
});

test("no county list is written as null, never as an empty list", () => {
  assert.deepEqual(toRow({ states: ["MI", "TX"], counties: [], frequency: "weekly" }), {
    states: ["TX", "MI"],
    county_fips: null,
    frequency: "weekly",
  });
  assert.deepEqual(toRow({ states: ["TX"], counties: [HOOD], frequency: "each" }).county_fips, [
    HOOD,
  ]);
});

test("the choices are put in plain words", () => {
  assert.equal(
    describe({ states: ["TX", "MI"], counties: [HOOD], frequency: "weekly" }),
    "A weekly digest for each state: Hood in Texas and all of Michigan.",
  );
  assert.equal(
    describe({ states: ["MI"], counties: [], frequency: "each" }),
    "An email for each alert: all of Michigan.",
  );
  assert.equal(describe({ states: [], counties: [], frequency: "weekly" }), "");
});

test("choices kept in the browser are used only for the same address within a day", () => {
  const now = 1_800_000_000_000;
  const raw = JSON.stringify({
    email: "Reader@Example.org",
    at: now - 60_000,
    choices: { states: ["TX", "OH"], counties: [HOOD, "bad"], frequency: "each" },
  });
  assert.deepEqual(pendingFor(raw, "reader@example.org", now), {
    states: ["TX"],
    counties: [HOOD],
    frequency: "each",
  });
  assert.equal(pendingFor(raw, "someone.else@example.org", now), null);
  assert.equal(pendingFor(raw, "reader@example.org", now + 25 * 60 * 60 * 1000), null);
  assert.equal(pendingFor("{not json", "reader@example.org", now), null);
  assert.equal(pendingFor(null, "reader@example.org", now), null);
});

test("only a well formed token or id is read from a page address", () => {
  assert.equal(
    tokenFrom("?token=00000000-0000-4000-8000-000000000001"),
    "00000000-0000-4000-8000-000000000001",
  );
  assert.equal(tokenFrom("?token=anything"), null);
  assert.equal(tokenFrom(""), null);
  assert.equal(idFrom("?id=12", "id"), 12);
  assert.equal(idFrom("?id=12;drop", "id"), null);
  assert.equal(idFrom("?alert=7", "id"), null);
});
