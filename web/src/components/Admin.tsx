import { useEffect, useState } from "preact/hooks";
import { Frame } from "./Frame";
import { longDate, problem } from "../lib/format";
import type { Account } from "../lib/session";
import { supabase } from "../lib/supabase";
import type { ReviewerStatus } from "../lib/types";

interface Person {
  user_id: string;
  display_name: string;
  email: string;
  status: ReviewerStatus;
  role: string;
  applied_at: string;
  approved_at: string | null;
  application_note: string | null;
}

interface ProcessingRun {
  id: number;
  started_at: string;
  status: string;
  documents: number;
  signals_new: number;
  held_back: number;
  errors: number;
  error: string | null;
  detail: {
    held_refs?: string[];
    sites?: { possible_same_site?: { signal_id: number; sites: number[] }[] };
  };
}

interface CollectorRun {
  id: number;
  started_at: string;
  status: string;
  documents_seen: number;
  documents_new: number;
  error: string | null;
  sources: { name: string } | null;
}

interface AuditRow {
  id: number;
  at: string;
  actor_role: string | null;
  action: string;
  target: string;
  detail: Record<string, unknown>;
}

function People({ account }: { account: Account }) {
  const [people, setPeople] = useState<Person[] | null>(null);
  const [error, setError] = useState("");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    supabase.rpc("reviewer_directory").then(({ data, error: failed }) => {
      if (failed) setError(problem(failed));
      else setPeople((data ?? []) as Person[]);
    });
  }, [tick]);

  const [asking, setAsking] = useState<{ person: Person; status: ReviewerStatus } | null>(null);

  async function set(person: Person, status: ReviewerStatus) {
    setAsking(null);
    setError("");
    const { error: failed } = await supabase
      .from("reviewers")
      .update({ status })
      .eq("user_id", person.user_id);
    if (failed) setError(problem(failed));
    setTick((n) => n + 1);
  }

  return (
    <>
      <h2>Applications and reviewers</h2>
      <p class="note">
        Approving a person lets them read every site and signal and record decisions. Check who
        they are first. Every approval and suspension is logged under your name.
      </p>
      {error && <p class="warn">{error}</p>}
      {people === null && !error && <p class="note">Loading.</p>}
      {asking && (
        <div class="row" role="alertdialog" aria-label="Confirm the change">
          <span>
            {asking.status === "approved" ? "Approve" : "Suspend"}{" "}
            <strong>{asking.person.display_name}</strong> ({asking.person.email})?
          </span>
          <button type="button" onClick={() => set(asking.person, asking.status)}>
            Yes, {asking.status === "approved" ? "approve" : "suspend"}
          </button>
          <button type="button" class="quiet" onClick={() => setAsking(null)}>
            Cancel
          </button>
        </div>
      )}
      {people !== null && (
        <div class="scroll">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>What they wrote</th>
                <th>Applied</th>
                <th>Standing</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {people.map((p) => (
                <tr>
                  <td>{p.display_name}</td>
                  <td>{p.email}</td>
                  <td>{p.application_note}</td>
                  <td>{longDate(p.applied_at)}</td>
                  <td>
                    {p.status}
                    {p.role === "admin" ? ", administrator" : ""}
                  </td>
                  <td>
                    {p.user_id === account.userId ? (
                      <span class="note">You</span>
                    ) : p.status === "approved" ? (
                      <button
                        type="button"
                        class="quiet"
                        onClick={() => setAsking({ person: p, status: "suspended" })}
                      >
                        Suspend
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setAsking({ person: p, status: "approved" })}
                      >
                        {p.status === "pending" ? "Approve" : "Approve again"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function Pipeline() {
  const [runs, setRuns] = useState<ProcessingRun[]>([]);
  const [collected, setCollected] = useState<CollectorRun[]>([]);
  const [settings, setSettings] = useState<{ confirmations_required: number; admin_gate_enabled: boolean } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    supabase
      .from("processing_runs")
      .select("id, started_at, status, documents, signals_new, held_back, errors, error, detail")
      .order("id", { ascending: false })
      .limit(10)
      .then(({ data, error: failed }) => {
        if (failed) setError(problem(failed));
        else setRuns((data ?? []) as ProcessingRun[]);
      });
    supabase
      .from("collector_runs")
      .select("id, started_at, status, documents_seen, documents_new, error, sources(name)")
      .order("id", { ascending: false })
      .limit(20)
      .then(({ data }) => setCollected((data ?? []) as unknown as CollectorRun[]));
    supabase
      .from("app_settings")
      .select("confirmations_required, admin_gate_enabled")
      .single()
      .then(({ data }) => setSettings(data));
  }, []);

  const flagged = new Map<string, number[]>();
  const held = new Set<string>();
  for (const run of runs) {
    for (const flag of run.detail?.sites?.possible_same_site ?? []) {
      flagged.set(flag.sites.join(","), flag.sites);
    }
    for (const ref of run.detail?.held_refs ?? []) held.add(ref);
  }

  return (
    <>
      <h2>Sites that may be the same place</h2>
      <p class="note">
        The pipeline never merges sites. When a signal fits two, it flags them here. Open one and
        fold it into the other if they are the same place.
      </p>
      {flagged.size === 0 ? (
        <p>None flagged in the last ten runs.</p>
      ) : (
        <ul>
          {[...flagged.values()].map((sites) => (
            <li>
              {sites.map((id, i) => (
                <>
                  {i > 0 && " and "}
                  <a href={`/review/site/?id=${id}`}>site {id}</a>
                </>
              ))}
            </li>
          ))}
        </ul>
      )}

      <h2>Records held back</h2>
      <p class="note">
        A record gave a reason to be a signal, and the party it names may be a person, so no signal
        was made. They are listed by record number only. If the party is plainly a company, add
        its name to config/entities.yaml.
      </p>
      {held.size === 0 ? (
        <p>None in the last ten runs.</p>
      ) : (
        <ul>
          {[...held].sort().map((ref) => (
            <li>{ref}</li>
          ))}
        </ul>
      )}

      <h2>Settings</h2>
      {settings && (
        <dl class="facts">
          <dt>Confirmations needed to publish</dt>
          <dd>{settings.confirmations_required}</dd>
          <dt>Administrator approves each alert</dt>
          <dd>{settings.admin_gate_enabled ? "Yes" : "No"}</dd>
        </dl>
      )}
      <p class="note">These are changed by the owner, not from this page.</p>

      <h2>Recent runs</h2>
      {error && <p class="warn">{error}</p>}
      <h3>Processing</h3>
      {runs.length === 0 ? (
        <p>No processing run is logged.</p>
      ) : (
        <div class="scroll">
          <table>
            <thead>
              <tr>
                <th>Started</th>
                <th>Result</th>
                <th class="num">Documents</th>
                <th class="num">New signals</th>
                <th class="num">Held back</th>
                <th>Problem</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr>
                  <td>{longDate(r.started_at)}</td>
                  <td class={r.status === "ok" ? "" : "warn"}>{r.status}</td>
                  <td class="num">{r.documents}</td>
                  <td class="num">{r.signals_new}</td>
                  <td class="num">{r.held_back}</td>
                  <td>{r.error}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <h3>Collectors</h3>
      {collected.length === 0 ? (
        <p>No collector run is logged.</p>
      ) : (
        <div class="scroll">
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Started</th>
                <th>Result</th>
                <th class="num">Seen</th>
                <th class="num">New</th>
                <th>Problem</th>
              </tr>
            </thead>
            <tbody>
              {collected.map((r) => (
                <tr>
                  <td>{r.sources?.name}</td>
                  <td>{longDate(r.started_at)}</td>
                  <td class={r.status === "ok" ? "" : "warn"}>{r.status}</td>
                  <td class="num">{r.documents_seen}</td>
                  <td class="num">{r.documents_new}</td>
                  <td>{r.error}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function AuditLog() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    supabase
      .from("audit_log")
      .select("id, at, actor_role, action, target, detail")
      .order("id", { ascending: false })
      .limit(60)
      .then(({ data, error: failed }) => {
        if (failed) setError(problem(failed));
        else setRows((data ?? []) as AuditRow[]);
      });
  }, []);
  return (
    <>
      <h2>Audit log</h2>
      <p class="note">The last 60 actions. The log cannot be edited or erased.</p>
      {error && <p class="warn">{error}</p>}
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Action</th>
              <th>On</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr>
                <td>{longDate(r.at)}</td>
                <td>{r.action}</td>
                <td class="mono">{r.target}</td>
                <td class="mono">{JSON.stringify(r.detail)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default function Admin() {
  return (
    <Frame need="admin">
      {(account) => (
        <>
          <h1>Administrator desk</h1>
          <p class="lede">
            For Dekleptocracy Alliance staff. Approving a reviewer, suspending one and publishing
            an alert are always a person's decision. Nothing here is automated.
          </p>
          <People account={account} />
          <Pipeline />
          <AuditLog />
        </>
      )}
    </Frame>
  );
}
