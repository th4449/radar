import assert from "node:assert/strict";
import { test } from "node:test";
import { fieldName, longDate, problem, signalName } from "../src/lib/format.ts";

test("a date is written out and never shifted by a time zone", () => {
  assert.equal(longDate("2026-11-20"), "November 20, 2026");
  assert.equal(longDate("2026-01-01T00:30:00+00:00"), "January 1, 2026");
  assert.equal(longDate("2026-12-31T23:59:59-06:00"), "December 31, 2026");
  assert.equal(longDate(null), "");
  assert.equal(longDate("not a date"), "not a date");
});

test("a record's column name reads as words", () => {
  assert.equal(fieldName("WellReportTrackingNumber"), "Well report tracking number");
  assert.equal(fieldName("permit_number"), "Permit number");
  assert.equal(fieldName("CoordDDLat"), "Coord lat");
  assert.equal(fieldName("WellAddress1"), "Well address1");
});

test("a signal type has a plain name, and an unknown one is shown as it is", () => {
  assert.equal(signalName("air_permit"), "Air permit application");
  assert.equal(signalName("something_new"), "something_new");
});

test("an error from the database is shown in its own words", () => {
  assert.equal(problem({ message: "only an administrator merges sites" }), "only an administrator merges sites");
  assert.equal(problem("plain"), "plain");
});
