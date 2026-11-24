import { useEffect, useState } from "preact/hooks";
import { Frame } from "./Frame";
import {
  fieldName,
  longDate,
  pagesNote,
  problem,
  ruleMakingNote,
  RULE_NAMES,
  signalName,
  STATUS_NAMES,
} from "../lib/format";
import type { Account } from "../lib/session";
import { supabase } from "../lib/supabase";
import type { Alert, Decision, DocumentRef, Reason, Review, Signal, Site } from "../lib/types";

interface Loaded {
  site: Site;
  signals: Signal[];
  refs: Map<number, DocumentRef>;
  reviews: Review[];
  alert: Alert | null;
  required: number;
}

async function load(id: number): Promise<Loaded> {
  const site = await supabase.from("sites").select("*").eq("id", id).maybeSingle();
  if (site.error) throw site.error;
  if (!site.data) throw new Error("There is no site with that number, or you may not see it.");
  const signals = await supabase
    .from("signals")
    .select(
      "id, document_id, signal_type, event_date, summary, confidence, county_fips, extracted," +
        " entities(name, kind)",
    )
    .eq("site_id", id)
    .order("event_date", { ascending: true })
    .order("id", { ascending: true });
  if (signals.error) throw signals.error;
  const list = (signals.data ?? []) as unknown as Signal[];
  const ids = [...new Set(list.map((s) => s.document_id))];
  const refs = await supabase.from("document_refs").select("*").in("id", ids);
  if (refs.error) throw refs.error;
  const reviews = await supabase
    .from("reviews")
    .select("*")
    .eq("site_id", id)
    .order("created_at", { ascending: true });
  if (reviews.error) throw reviews.error;
  const alert = await supabase.from("alerts").select("*").eq("site_id", id).maybeSingle();
  if (alert.error) throw alert.error;
  const settings = await supabase.from("app_settings").select("confirmations_required").single();
  return {
    site: site.data as Site,
    signals: list,
    refs: new Map(((refs.data ?? []) as DocumentRef[]).map((r) => [r.id, r])),
    reviews: (reviews.data ?? []) as Review[],
    alert: (alert.data as Alert | null) ?? null,
    required: settings.data?.confirmations_required ?? 1,
  };
}

// --- one signal ---------------------------------------------------------------------------------

function reasonText(reason: Reason): string {
  const lead = RULE_NAMES[reason.rule] ?? reason.rule;
  if (reason.rule.startsWith("listed_company")) {
    const listed = (reason.listed_as ?? []).map((l) => `${l.name}, ${l.role} of ${l.data_center}`);
    const how = reason.match ? ` (${reason.match})` : "";
    return `${lead}${how}${listed.length ? `: ${listed.join("; ")}` : ""}.`;
  }
  const where = reason.field && reason.field !== "text" ? ` in the ${reason.field}` : "";
  return `${lead} "${reason.text ?? reason.term ?? ""}"${where}.`;
}

function Facts({ rows }: { rows: [string, unknown][] }) {
  const shown = rows.filter(([, v]) => v !== null && v !== undefined && v !== "");
  if (shown.length === 0) return null;
  return (
    <dl class="facts">
      {shown.map(([k, v]) => (
        <>
          <dt>{k}</dt>
          <dd>{typeof v === "string" && /^https?:\/\//.test(v) ? <a href={v} target="_blank" rel="noreferrer">{v}</a> : String(v)}</dd>
        </>
      ))}
    </dl>
  );
}

function SignalBlock({ signal, source }: { signal: Signal; source: DocumentRef | undefined }) {
  const x = signal.extracted as Record<string, any>;
  const reasons: Reason[] = x.reasons ?? [];
  const snippets: string[] = x.snippets ?? [];
  const freeText: Record<string, string[]> = x.free_text_matches ?? {};
  const quantities: { kind: string; text: string; context: string }[] = x.quantities ?? [];
  const application: Record<string, any> | undefined = x.application;
  return (
    <section class="signal">
      <h3>
        {signalName(signal.signal_type)}, {longDate(signal.event_date)}
      </h3>
      <p>{signal.summary}</p>

      <p>
        <strong>Why it is here.</strong> {reasons.map(reasonText).join(" ") || "No reason is recorded."}{" "}
        {signal.confidence !== null && (
          <span class="note">Confidence {Number(signal.confidence).toFixed(1)} of 1.</span>
        )}
      </p>
      {x.site_link && (
        <p class="note">On this site because: {String(x.site_link)}.</p>
      )}
      {ruleMakingNote(x.rule_making?.words) && (
        <p class="note">{ruleMakingNote(x.rule_making?.words)}</p>
      )}
      {pagesNote(x.pages_with_terms, x.file_pages, x.pages_exact) && (
        <p class="note">{pagesNote(x.pages_with_terms, x.file_pages, x.pages_exact)}</p>
      )}

      {snippets.map((s) => (
        <blockquote>{s}</blockquote>
      ))}
      {Object.entries(freeText).map(([field, pieces]) =>
        pieces.map((piece) => (
          <blockquote>
            {piece} <span class="note">({field})</span>
          </blockquote>
        )),
      )}
      {quantities.length > 0 && (
        <p>
          <strong>Figures in the record.</strong>{" "}
          {quantities.map((q) => `${q.text} (${q.kind})`).join("; ")}. Read each one in context
          before relying on it.
        </p>
      )}
      {x.row && (
        <Facts
          rows={Object.entries(x.row as Record<string, unknown>)
            .map(([k, v]) => [fieldName(k), v] as [string, unknown])
            .sort((a, b) => a[0].localeCompare(b[0]))}
        />
      )}
      {application && application.status === "read" && (
        <>
          <p>
            <strong>From the application file.</strong>
          </p>
          <Facts
            rows={[
              ["County", application.county],
              ["City", application.city],
              ["Street", application.street],
              ["ZIP", application.zip],
              ["NAICS code", application.naics],
              ["Primary business, as stated", application.primary_business],
              ["Lines read", (application.evidence ?? []).join(" · ")],
              ["Application file", application.url],
            ]}
          />
        </>
      )}
      {x.point && (
        <p class="note">
          Coordinates {Number(x.point.lat).toFixed(5)}, {Number(x.point.lon).toFixed(5)}, from{" "}
          {String(x.point.from)}
        </p>
      )}

      <p>
        <strong>Source.</strong>{" "}
        {source ? (
          <>
            {source.source_name}.{" "}
            <a href={source.url} target="_blank" rel="noreferrer">
              Open the source record
            </a>
            . Retrieved {longDate(source.retrieved_at)}. SHA-256 <span class="mono">{source.sha256}</span>.
            {source.restricted && (
              <>
                {" "}
                Our stored copy is a list that names people, so it is restricted. The row above is
                the part this signal was made from. Check it against the public record.
              </>
            )}
          </>
        ) : (
          "The source reference could not be read."
        )}
      </p>
    </section>
  );
}

// --- the reviewer's decision --------------------------------------------------------------------

function ReviewForm({ site, account, done }: { site: Site; account: Account; done: () => void }) {
  const [checked, setChecked] = useState(false);
  const [decision, setDecision] = useState<Decision | "">("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const needsCheck = decision === "confirm" || decision === "reject";

  async function submit(event: Event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const { error: failed } = await supabase.from("reviews").insert({
      site_id: site.id,
      reviewer_id: account.userId,
      decision,
      note: note.trim() || null,
      source_checked: checked,
    });
    setBusy(false);
    if (failed) setError(problem(failed));
    else done();
  }

  return (
    <form class="plain" onSubmit={submit}>
      <label class="inline">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked((e.target as HTMLInputElement).checked)}
        />
        <span>I opened each source record above and checked this site against it.</span>
      </label>
      <fieldset style="border: 0; padding: 0; margin: 0.8rem 0">
        <legend style="font-weight: 600">Your decision</legend>
        {(
          [
            [
              "confirm",
              "Confirm. The records say what the signals say. They point to this place, or to a rule on data centers a government is weighing, such as a moratorium or a zoning change.",
            ],
            ["reject", "Reject. The records do not support this, or it is something else."],
            ["unsure", "Unsure. Leave it for another reviewer."],
          ] as [Decision, string][]
        ).map(([value, text]) => (
          <label class="inline">
            <input
              type="radio"
              name="decision"
              value={value}
              checked={decision === value}
              onChange={() => setDecision(value)}
            />
            <span>{text}</span>
          </label>
        ))}
      </fieldset>
      <label for="note">Note for other reviewers</label>
      <textarea
        id="note"
        value={note}
        onInput={(e) => setNote((e.target as HTMLTextAreaElement).value)}
      />
      <p class="note">
        Do not name private individuals. A decision cannot be changed afterward. An administrator
        can reverse it.
      </p>
      <div class="row">
        <button type="submit" disabled={busy || !decision || (needsCheck && !checked)}>
          Record my decision
        </button>
        {needsCheck && !checked && (
          <span class="note">Tick the box above to confirm or reject.</span>
        )}
      </div>
      {error && <p class="warn">{error}</p>}
    </form>
  );
}

// --- administrator ------------------------------------------------------------------------------

function AlertForm({ data, done }: { data: Loaded; done: () => void }) {
  const [headline, setHeadline] = useState(data.alert?.headline ?? "");
  const [body, setBody] = useState(data.alert?.body ?? "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const published = Boolean(data.alert?.published_at);

  async function save(publish: boolean | null) {
    setBusy(true);
    setError("");
    const fields: Record<string, unknown> = { headline: headline.trim(), body: body.trim() };
    if (publish !== null) fields.published_at = publish ? new Date().toISOString() : null;
    const query = data.alert
      ? supabase.from("alerts").update(fields).eq("id", data.alert.id)
      : supabase.from("alerts").insert({ site_id: data.site.id, ...fields });
    const { error: failed } = await query;
    setBusy(false);
    if (failed) setError(problem(failed));
    else done();
  }

  const ready = headline.trim() && body.trim();
  return (
    <form class="plain" onSubmit={(e) => e.preventDefault()}>
      <p>
        {published
          ? `Published ${longDate(data.alert?.published_at)}.`
          : data.alert
            ? "A draft is saved. It is not public."
            : "No alert is drafted for this site."}
      </p>
      <label for="headline">Headline</label>
      <input
        id="headline"
        type="text"
        value={headline}
        onInput={(e) => setHeadline((e.target as HTMLInputElement).value)}
      />
      <label for="body">Body</label>
      <textarea
        id="body"
        value={body}
        onInput={(e) => setBody((e.target as HTMLTextAreaElement).value)}
      />
      <p class="note">
        Write in the language of signals. Do not say a data center is planned unless a source
        record says so. Do not name private individuals. Every public alert carries its source
        links.
      </p>
      <div class="row">
        <button type="button" class="quiet" disabled={busy || !ready} onClick={() => save(null)}>
          Save the draft
        </button>
        {!published && (
          <button type="button" disabled={busy || !ready} onClick={() => save(true)}>
            Publish
          </button>
        )}
        {published && (
          <button type="button" class="quiet" disabled={busy} onClick={() => save(false)}>
            Take it down
          </button>
        )}
      </div>
      {error && <p class="warn">{error}</p>}
    </form>
  );
}

function MergeForm({ site }: { site: Site }) {
  const [others, setOthers] = useState<Pick<Site, "id" | "label" | "status">[]>([]);
  const [into, setInto] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    supabase
      .from("sites")
      .select("id, label, status")
      .eq("county_fips", site.county_fips)
      .neq("id", site.id)
      .order("label")
      .then(({ data }) => setOthers((data ?? []) as Pick<Site, "id" | "label" | "status">[]));
  }, [site.id]);

  async function merge(event: Event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const { error: failed } = await supabase.rpc("merge_sites", {
      p_from: site.id,
      p_into: Number(into),
      p_note: note.trim() || null,
    });
    setBusy(false);
    if (failed) setError(problem(failed));
    else window.location.assign(`/review/site/?id=${into}`);
  }

  if (others.length === 0) return <p class="note">No other site is in this county.</p>;
  return (
    <form class="plain" onSubmit={merge}>
      <p>
        If this site and another in the county are the same place, fold this one into the other.
        Its signals move there and this site is removed. A site that has been reviewed cannot be
        folded away. The other site's score is worked out again at the next processing run.
      </p>
      <label for="into">Fold this site into</label>
      <select id="into" value={into} onChange={(e) => setInto((e.target as HTMLSelectElement).value)}>
        <option value="">Choose a site</option>
        {others.map((o) => (
          <option value={String(o.id)}>
            {o.label} ({STATUS_NAMES[o.status].toLowerCase()}, site {o.id})
          </option>
        ))}
      </select>
      <label for="why">Why they are the same place</label>
      <input
        id="why"
        type="text"
        value={note}
        onInput={(e) => setNote((e.target as HTMLInputElement).value)}
      />
      <div class="row">
        <button type="submit" class="quiet" disabled={busy || !into || !note.trim()}>
          Fold this site in
        </button>
      </div>
      {error && <p class="warn">{error}</p>}
    </form>
  );
}

// --- the page -----------------------------------------------------------------------------------

function Page({ account }: { account: Account }) {
  const id = Number(new URLSearchParams(window.location.search).get("id"));
  const [data, setData] = useState<Loaded | null>(null);
  const [error, setError] = useState("");
  const [tick, setTick] = useState(0);
  const reload = () => setTick((n) => n + 1);

  useEffect(() => {
    if (!Number.isInteger(id) || id <= 0) {
      setError("This address names no site.");
      return;
    }
    load(id)
      .then(setData)
      .catch((failed) => setError(problem(failed)));
  }, [id, tick]);

  const [reversing, setReversing] = useState<number | null>(null);
  const [why, setWhy] = useState("");
  const [actionError, setActionError] = useState("");

  async function reverse(event: Event) {
    event.preventDefault();
    setActionError("");
    const { error: failed } = await supabase
      .from("reviews")
      .update({ reversed_at: new Date().toISOString(), reversal_note: why.trim() })
      .eq("id", reversing);
    if (failed) {
      setActionError(problem(failed));
      return;
    }
    setReversing(null);
    setWhy("");
    reload();
  }

  if (error) return <p class="warn">{error}</p>;
  if (!data) return <p class="note">Loading.</p>;

  const { site, signals, refs, reviews, required } = data;
  const detail = site.score_detail ?? {};
  const standing = reviews.filter((r) => !r.reversed_at);
  const mine = standing.find((r) => r.reviewer_id === account.userId);
  const confirms = standing.filter((r) => r.decision === "confirm").length;

  return (
    <>
      <p class="note">
        <a href="/review/queue/">Review queue</a>
      </p>
      <h1>{site.label}</h1>
      <p class="lede">
        {STATUS_NAMES[site.status]}. Site {site.id}, county code {site.county_fips}, {site.state}.{" "}
        {signals.length} {signals.length === 1 ? "signal" : "signals"}, the first dated{" "}
        {longDate(site.first_signal_at)}.
      </p>

      <h2>Why it scores {Number(site.score).toFixed(1)}</h2>
      <p class="note">
        A score orders the queue. It is not a finding.
        {detail.placeholder && " Every number below is a placeholder until the backtest."}
        {detail.as_of && ` Worked out for ${longDate(detail.as_of)}.`}
      </p>
      {(detail.contributions ?? []).length > 0 && (
        <div class="scroll">
          <table>
            <thead>
              <tr>
                <th>Signal type</th>
                <th>Strongest signal dated</th>
                <th class="num">Points</th>
                <th class="num">Confidence</th>
                <th class="num">Decay</th>
                <th class="num">Counts for</th>
              </tr>
            </thead>
            <tbody>
              {(detail.contributions ?? []).map((c) => (
                <tr>
                  <td>{signalName(c.signal_type)}</td>
                  <td>{longDate(c.event_date)}</td>
                  <td class="num">{c.points}</td>
                  <td class="num">{c.confidence}</td>
                  <td class="num">{c.decay}</td>
                  <td class="num">{c.value}</td>
                </tr>
              ))}
              <tr>
                <td colSpan={5}>
                  Bonus for different kinds of record within a year of each other
                  {detail.bonus?.types?.length
                    ? `: ${detail.bonus.types.map(signalName).join(" and ").toLowerCase()}`
                    : ": not earned"}
                </td>
                <td class="num">{detail.bonus?.points ?? 0}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
      <p class="note">
        Each signal type counts once, by its strongest signal. {detail.signals_total ?? signals.length}{" "}
        signals, {detail.signals_counted ?? 0} counted.
      </p>

      <h2>The signals</h2>
      {signals.map((signal) => (
        <SignalBlock signal={signal} source={refs.get(signal.document_id)} />
      ))}

      <h2>Decisions so far</h2>
      <p>
        {confirms} of {required} {required === 1 ? "confirmation" : "confirmations"} needed before
        an alert can be published.
      </p>
      {reviews.length === 0 ? (
        <p>Nobody has reviewed this site.</p>
      ) : (
        <div class="scroll">
          <table>
            <thead>
              <tr>
                <th>Decision</th>
                <th>By</th>
                <th>When</th>
                <th>Note</th>
                <th>Standing</th>
              </tr>
            </thead>
            <tbody>
              {reviews.map((r) => (
                <tr>
                  <td>{r.decision}</td>
                  <td>{r.reviewer_id === account.userId ? "You" : "Another reviewer"}</td>
                  <td>{longDate(r.created_at)}</td>
                  <td>{r.note}</td>
                  <td>
                    {r.reversed_at ? (
                      <>Reversed {longDate(r.reversed_at)}: {r.reversal_note}</>
                    ) : account.admin ? (
                      <button type="button" class="quiet" onClick={() => setReversing(r.id)}>
                        Reverse
                      </button>
                    ) : (
                      "Stands"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {reversing !== null && (
        <form class="plain" onSubmit={reverse}>
          <label for="why-reverse">Why is this decision being reversed? The reason is kept.</label>
          <input
            id="why-reverse"
            type="text"
            value={why}
            onInput={(e) => setWhy((e.target as HTMLInputElement).value)}
          />
          <div class="row">
            <button type="submit" disabled={!why.trim()}>
              Reverse the decision
            </button>
            <button type="button" class="quiet" onClick={() => setReversing(null)}>
              Cancel
            </button>
          </div>
        </form>
      )}
      {actionError && <p class="warn">{actionError}</p>}

      <h2>Your review</h2>
      {mine ? (
        <p>
          You recorded <strong>{mine.decision}</strong> on {longDate(mine.created_at)}. Only an
          administrator can reverse it.
        </p>
      ) : (
        <ReviewForm site={site} account={account} done={reload} />
      )}

      {account.admin && (
        <>
          <h2>Administrator: the alert</h2>
          <AlertForm data={data} done={reload} />
          <h2>Administrator: same place as another site</h2>
          <MergeForm site={site} />
        </>
      )}
    </>
  );
}

export default function SitePage() {
  return <Frame need="reviewer">{(account) => <Page account={account} />}</Frame>;
}
