import assert from "node:assert/strict";
import { test } from "node:test";
import {
  fieldName,
  localDay,
  longDate,
  pagesNote,
  problem,
  ruleMakingNote,
  signalName,
  STUDY_PUBLIC_REST,
  studyNote,
  studyPublicLead,
  studyUrl,
} from "../src/lib/format.ts";

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

test("a moment is shown as the day it was where the reader is", () => {
  const evening = "2026-11-21T02:00:00+00:00";
  assert.equal(localDay(evening, "America/Chicago"), "November 20, 2026");
  assert.equal(localDay(evening, "UTC"), "November 21, 2026");
  assert.equal(localDay("2026-08-21"), "August 21, 2026");
  assert.equal(localDay(null), "");
});

test("a reviewer is told which words of rule making sit beside data center, and no more", () => {
  assert.equal(
    ruleMakingNote(["moratorium", "ordinance"]),
    'Also in the item: "moratorium", "ordinance". These are the words of a government writing ' +
      "its own rules. A project can use them too.",
  );
  assert.equal(ruleMakingNote([]), "");
  assert.equal(ruleMakingNote(undefined), "");
  assert.equal(ruleMakingNote("moratorium"), "");
});

test("a reviewer is told the file's own pages, and nothing where they are not sure", () => {
  assert.equal(pagesNote([28], 31, true), "The words are on page 28. The file has 31 pages.");
  assert.equal(pagesNote([4, 5], 26, true), "The words are on pages 4 and 5. The file has 26 pages.");
  assert.equal(
    pagesNote([4, 5, 24], 26, true),
    "The words are on pages 4, 5 and 24. The file has 26 pages.",
  );
  assert.equal(
    pagesNote([4, 171, 174, 176, 180], 260, true),
    "The words are on pages 4, 171, 174 and others. The file has 260 pages.",
  );
  // Not sure, not counted, or a file of one page: nothing is said.
  assert.equal(pagesNote([3], 5, false), "");
  assert.equal(pagesNote([3], 5, undefined), "");
  assert.equal(pagesNote([1], 1, true), "");
  assert.equal(pagesNote([], 31, true), "");
  assert.equal(pagesNote([3], undefined, true), "");
});

const ONCOR = {
  name: "Oncor",
  payer_class: "Utility",
  url: "https://www.purchasingpolicy.org/entity/139640b7-37f0-4bea-a87a-ab0d38580032",
  states: ["TX"],
};

test("a reviewer is told a company has a payer's name, how the names met, and no more", () => {
  assert.equal(
    studyNote("Oncor Electric Delivery Company LLC", {
      basis: "same_name_legal_form_aside",
      study_payers: ONCOR,
    }),
    "Oncor Electric Delivery Company LLC has the name of a payer in the QPQ Tracker's data " +
      'center study: Oncor, class "Utility". The study counts its giving in the filings of TX. ' +
      "The match is by name, with the legal form set aside. It is not proof that the two are " +
      "one company. It says nothing about this site.",
  );
  assert.equal(
    studyNote("Google", {
      basis: "same_name",
      study_payers: { ...ONCOR, name: "Google", payer_class: "Hyperscaler", states: ["CA", "MI", "TX"] },
    }),
    "Google has the name of a payer in the QPQ Tracker's data center study: Google, class " +
      '"Hyperscaler". The study counts its giving in the filings of CA, MI and TX. The match ' +
      "is by name. It is not proof that the two are one company. It says nothing about this site.",
  );
  // No company, no match or a match whose payer could not be read: nothing is said.
  assert.equal(studyNote("Google", null), "");
  assert.equal(studyNote("Google", { basis: "same_name", study_payers: null }), "");
  assert.equal(studyNote(undefined, { basis: "same_name", study_payers: ONCOR }), "");
});

test("only a payer's page in the study is ever linked", () => {
  assert.equal(studyUrl(ONCOR.url), ONCOR.url);
  assert.equal(studyUrl("https://example.org/entity/139640b7-37f0-4bea-a87a-ab0d38580032"), null);
  assert.equal(studyUrl("https://www.purchasingpolicy.org/entity/oncor"), null);
  assert.equal(studyUrl("javascript:alert(1)"), null);
  assert.equal(studyUrl(undefined), null);
});

test("the public is told the match is by name and proves nothing about the site", () => {
  assert.match(studyPublicLead(1), /^A record behind this alert names a company with the same name/);
  assert.match(studyPublicLead(2), /^Records behind this alert name companies with the same names/);
  assert.match(STUDY_PUBLIC_REST, /The match is by name\./);
  assert.match(STUDY_PUBLIC_REST, /does not show that any giving had to do with this site\.$/);
});

