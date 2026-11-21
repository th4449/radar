import { useEffect, useState } from "preact/hooks";
import { AlertMap } from "./AlertMap";
import { fetchAlerts, pointOf, recordCount, type PublicAlert } from "../lib/alerts";
import { localDay, problem } from "../lib/format";
import { countyName, whereLine } from "../lib/places";
import { configured } from "../lib/supabase";

interface Props {
  state?: string;
  county?: string;
}

export function AlertLine({ alert, county }: { alert: PublicAlert; county?: boolean }) {
  return (
    <li class="alert">
      <h3>
        <a href={`/alert/?id=${alert.alert_id}`}>{alert.headline}</a>
      </h3>
      <p>
        Confirmed. Published {localDay(alert.published_at)}.{" "}
        {county ? countyName(alert.county_fips) : whereLine(alert.state, alert.county_fips)}.{" "}
        {recordCount(alert.sources.length)}.
      </p>
    </li>
  );
}

/** The confirmed alerts for the whole site, a state or a county: a map, then the list. */
export default function Alerts({ state, county }: Props) {
  const [alerts, setAlerts] = useState<PublicAlert[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!configured) return;
    fetchAlerts({ state, county })
      .then(setAlerts)
      .catch((failed) => setError(problem(failed)));
  }, [state, county]);

  if (!configured) {
    return <p class="warn">This copy of the site was built without a database address.</p>;
  }
  if (error) return <p class="warn">The alerts did not load. {error}</p>;
  if (!alerts) return <p class="note">Loading.</p>;
  if (alerts.length === 0) {
    return (
      <p>
        No confirmed alert has been published{county ? " for this county" : state ? " for this state" : ""}{" "}
        yet. That does not mean nothing is planned. It means no cluster of records has passed
        review.
      </p>
    );
  }

  const located = alerts.filter((a) => pointOf(a) !== null).length;
  return (
    <>
      {located > 0 && <AlertMap alerts={alerts} state={state} close={Boolean(county)} />}
      {located < alerts.length && (
        <p class="note">
          {located === 0
            ? "No alert here has a point on record, so there is no map."
            : `${alerts.length - located} of these ${alerts.length} alerts have no point on record and are not on the map.`}{" "}
          Each one names its county.
        </p>
      )}
      <ol class="alerts">
        {alerts.map((alert) => (
          <AlertLine alert={alert} county={Boolean(county)} />
        ))}
      </ol>
    </>
  );
}
