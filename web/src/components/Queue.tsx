import { useEffect, useState } from "preact/hooks";
import { Frame } from "./Frame";
import { longDate, problem, signalName, STATUS_NAMES } from "../lib/format";
import type { Account } from "../lib/session";
import { supabase } from "../lib/supabase";
import type { Review, Site, SiteStatus } from "../lib/types";

interface Row extends Site {
  signals: { signal_type: string }[];
  reviews: Pick<Review, "reviewer_id" | "decision" | "reversed_at">[];
}

const SHOWN: SiteStatus[] = ["in_review", "candidate", "rejected", "confirmed"];

function List({ account }: { account: Account }) {
  const [status, setStatus] = useState<SiteStatus>("in_review");
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    setRows(null);
    supabase
      .from("sites")
      .select(
        "id, state, county_fips, label, status, score, score_detail, scored_at, first_signal_at," +
          " signals(signal_type), reviews(reviewer_id, decision, reversed_at)",
      )
      .eq("status", status)
      .order("score", { ascending: false })
      .limit(200)
      .then(({ data, error: failed }) => {
        if (!live) return;
        if (failed) setError(problem(failed));
        else setRows((data ?? []) as unknown as Row[]);
      });
    return () => {
      live = false;
    };
  }, [status]);

  return (
    <>
      <h1>Review queue</h1>
      <p class="lede">
        Each row is a place or project where public records cluster. A score orders the queue.
        It is not a finding. The scoring numbers are placeholders until the backtest.
      </p>
      <label for="status">Show sites that are</label>
      <select
        id="status"
        style="max-width: 16rem"
        value={status}
        onChange={(e) => setStatus((e.target as HTMLSelectElement).value as SiteStatus)}
      >
        {SHOWN.map((s) => (
          <option value={s}>{STATUS_NAMES[s].toLowerCase()}</option>
        ))}
      </select>
      {error && <p class="warn">{error}</p>}
      {rows === null && !error && <p class="note">Loading.</p>}
      {rows !== null && rows.length === 0 && (
        <p>
          No site is {STATUS_NAMES[status].toLowerCase()}.
          {status === "in_review" &&
            " A site enters the queue when its score reaches the review threshold, or when a reviewer opens it from the candidates."}
        </p>
      )}
      {rows !== null && rows.length > 0 && (
        <div class="scroll">
          <table>
            <thead>
              <tr>
                <th>Site</th>
                <th class="num">Score</th>
                <th>Signals</th>
                <th>First signal</th>
                <th>Your decision</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const kinds = [...new Set(row.signals.map((s) => signalName(s.signal_type)))];
                const mine = row.reviews.find(
                  (r) => r.reviewer_id === account.userId && !r.reversed_at,
                );
                return (
                  <tr>
                    <td>
                      <a href={`/review/site/?id=${row.id}`}>{row.label}</a>
                    </td>
                    <td class="num">{Number(row.score).toFixed(1)}</td>
                    <td>
                      {row.signals.length}: {kinds.join(", ").toLowerCase()}
                    </td>
                    <td>{longDate(row.first_signal_at)}</td>
                    <td>{mine ? mine.decision : "none yet"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

export default function Queue() {
  return <Frame need="reviewer">{(account) => <List account={account} />}</Frame>;
}
