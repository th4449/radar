import { useEffect, useState } from "preact/hooks";
import { AlertMap } from "./AlertMap";
import { fetchAlert, pointOf, recordCount, safeUrl, type PublicAlert } from "../lib/alerts";
import { idFrom } from "../lib/choices";
import {
  localDay,
  longDate,
  problem,
  signalName,
  STUDY_PUBLIC_REST,
  studyPublicLead,
  studyUrl,
} from "../lib/format";
import { countyPath, stateByCode, whereLine } from "../lib/places";
import { configured } from "../lib/supabase";

function Records({ alert }: { alert: PublicAlert }) {
  return (
    <ol class="records">
      {alert.sources.map((record) => {
        const url = safeUrl(record.url);
        return (
          <li>
            <h3>
              {signalName(record.signal_type)}, dated {longDate(record.event_date)}
            </h3>
            <p>
              {record.reference ? `${record.reference}. ` : ""}
              {record.source}.{" "}
              {url ? (
                <a href={url} rel="noopener noreferrer">
                  Open the record at its source
                </a>
              ) : (
                "This record has no web address."
              )}
            </p>
            <p class="note">
              The radar read it on {localDay(record.retrieved_at)} and kept a copy. The copy's
              fingerprint is <span class="mono">{record.sha256}</span>.
            </p>
          </li>
        );
      })}
    </ol>
  );
}

/** Payers in the QPQ Tracker's study whose name a record's company has. Nothing when none. */
function Study({ alert }: { alert: PublicAlert }) {
  const payers = (alert.study_payers ?? []).filter((p) => p.name && studyUrl(p.url));
  if (payers.length === 0) return null;
  return (
    <>
      <h2>In the QPQ Tracker's study</h2>
      <p>
        {studyPublicLead(payers.length)}{" "}
        {payers.map((payer, i) => (
          <>
            {i > 0 && (i === payers.length - 1 ? " and " : ", ")}
            <a href={studyUrl(payer.url)!} rel="noopener noreferrer">
              {payer.name}
            </a>
          </>
        ))}
        . {STUDY_PUBLIC_REST}
      </p>
    </>
  );
}

/** One confirmed alert: what it says, the records it rests on and where to send a correction. */
export default function AlertPage() {
  const [alert, setAlert] = useState<PublicAlert | null | undefined>(undefined);
  const [error, setError] = useState("");
  const id = idFrom(window.location.search, "id");

  useEffect(() => {
    if (!configured || id === null) return;
    fetchAlert(id)
      .then((found) => {
        setAlert(found);
        if (found) document.title = `${found.headline} · Data Center Early Warning Radar`;
      })
      .catch((failed) => setError(problem(failed)));
  }, [id]);

  if (!configured) {
    return <p class="warn">This copy of the site was built without a database address.</p>;
  }
  if (error) return <p class="warn">The alert did not load. {error}</p>;
  if (id === null || alert === null) {
    return (
      <>
        <h1>No such alert</h1>
        <p>
          There is no public alert at this address. An alert is taken down if a reviewer's
          confirmation is reversed. <a href="/">See every confirmed alert.</a>
        </p>
      </>
    );
  }
  if (alert === undefined) return <p class="note">Loading.</p>;

  const state = stateByCode(alert.state);
  const county = countyPath(alert.county_fips);
  const reviewers =
    alert.confirmed_by_count === 1 ? "1 reviewer" : `${alert.confirmed_by_count} reviewers`;
  return (
    <article>
      <p class="kicker">Confirmed alert</p>
      <h1>{alert.headline}</h1>
      <p class="lede">
        Confirmed by {reviewers}. Published {localDay(alert.published_at)}.{" "}
        {whereLine(alert.state, alert.county_fips)}.
      </p>
      {alert.body
        .split(/\n\s*\n/)
        .filter((part) => part.trim())
        .map((part) => (
          <p class="body">{part.trim()}</p>
        ))}

      <h2>The records</h2>
      <p>
        This alert rests on {recordCount(alert.sources.length)}. Read them yourself. Each link
        goes to the agency that published the record.
      </p>
      <Records alert={alert} />
      <Study alert={alert} />

      <h2>Where</h2>
      {pointOf(alert) ? (
        <>
          <AlertMap alerts={[alert]} state={alert.state} close />
          <p class="note">
            The point comes from the records. It marks where they place the site, not a
            surveyed boundary.
          </p>
        </>
      ) : (
        <p>The records name the county and give no point, so there is no map.</p>
      )}
      <p>
        {county && <a href={county}>Every alert in this county</a>}
        {county && state && ". "}
        {state && <a href={`/${state.slug}/`}>Every alert in {state.name}</a>}.
      </p>

      <h2>What confirmed means</h2>
      <p>
        A reviewer approved by Dekleptocracy Alliance opened each record at its source and
        checked that it says what this alert says. Confirmed does not mean a data center is
        planned. <a href="/methodology/">Read how the radar works.</a>
      </p>
      <p>
        <a href={`/corrections/?alert=${alert.alert_id}`}>Send a correction about this alert</a>
      </p>
    </article>
  );
}
