import { useEffect, useState } from "preact/hooks";
import { ChoiceFields } from "./ChoiceFields";
import {
  DEFAULT_CHOICES,
  PENDING_KEY,
  fromRow,
  pendingFor,
  toRow,
  type Choices,
  type Frequency,
} from "../lib/choices";
import { localDay, problem } from "../lib/format";
import { signOut, useUser } from "../lib/session";
import { configured, supabase } from "../lib/supabase";
import { absolute, href } from "../lib/paths";

interface Row {
  email: string;
  states: string[];
  county_fips: string[] | null;
  frequency: Frequency;
  confirmed_at: string | null;
}

function SignIn() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function send(event: Event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const { error: failed } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: { emailRedirectTo: absolute("/account/") },
    });
    setBusy(false);
    if (failed) setError(problem(failed));
    else setSent(true);
  }

  if (sent) {
    return (
      <p>
        A sign-in link is on its way to <strong>{email.trim()}</strong>. Open it on this device.
      </p>
    );
  }
  return (
    <form class="plain" onSubmit={send}>
      <p>
        To change or stop your alerts, sign in with the address they go to. New here?{" "}
        <a href={href("/subscribe/")}>Sign up for alerts.</a>
      </p>
      <label for="email">Your email address</label>
      <input
        id="email"
        type="email"
        required
        autocomplete="email"
        value={email}
        onInput={(e) => setEmail((e.target as HTMLInputElement).value)}
      />
      <p class="note">We send a link that signs you in. There is no password.</p>
      <div class="row">
        <button type="submit" disabled={busy || !email.trim()}>
          Send the sign-in link
        </button>
      </div>
      {error && <p class="warn">{error}</p>}
    </form>
  );
}

function Manage({ userId, email }: { userId: string; email: string }) {
  const [row, setRow] = useState<Row | null | undefined>(undefined);
  const [choices, setChoices] = useState<Choices>(DEFAULT_CHOICES);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [stopping, setStopping] = useState(false);
  const [stopped, setStopped] = useState(false);

  async function load(): Promise<Row | null> {
    const { data, error: failed } = await supabase
      .from("subscribers")
      .select("email, states, county_fips, frequency, confirmed_at")
      .eq("user_id", userId)
      .maybeSingle();
    if (failed) throw failed;
    const found = (data as Row | null) ?? null;
    setRow(found);
    if (found) setChoices(fromRow(found));
    return found;
  }

  async function confirm() {
    const { error: failed } = await supabase.rpc("confirm_subscription");
    if (failed) throw failed;
  }

  // On arrival. If the person came from the signup form through the emailed link, their choices
  // are waiting in this browser: save them and confirm. That link is the second opt in.
  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const found = await load();
        if (found || !live) return;
        let raw: string | null = null;
        try {
          raw = window.localStorage.getItem(PENDING_KEY);
        } catch {
          raw = null;
        }
        const pending = pendingFor(raw, email, Date.now());
        if (!pending) return;
        const { error: failed } = await supabase
          .from("subscribers")
          .insert({ user_id: userId, ...toRow(pending) });
        if (failed) throw failed;
        await confirm();
        try {
          window.localStorage.removeItem(PENDING_KEY);
        } catch {
          // nothing to clear
        }
        if (live) {
          await load();
          setSaved("Your address is confirmed and your alerts are set.");
        }
      } catch (failed) {
        if (live) setError(problem(failed));
      }
    })();
    return () => {
      live = false;
    };
  }, [userId]);

  async function act(work: () => Promise<void>, done: string) {
    setBusy(true);
    setError("");
    setSaved("");
    try {
      await work();
      await load();
      setSaved(done);
    } catch (failed) {
      setError(problem(failed));
    }
    setBusy(false);
  }

  const create = (event: Event) => {
    event.preventDefault();
    return act(async () => {
      const { error: failed } = await supabase
        .from("subscribers")
        .insert({ user_id: userId, ...toRow(choices) });
      if (failed) throw failed;
    }, "Saved. One step is left.");
  };

  const update = (event: Event) => {
    event.preventDefault();
    return act(async () => {
      const { error: failed } = await supabase
        .from("subscribers")
        .update(toRow(choices))
        .eq("user_id", userId);
      if (failed) throw failed;
    }, "Your changes are saved.");
  };

  async function stop() {
    setBusy(true);
    setError("");
    const { error: failed } = await supabase.from("subscribers").delete().eq("user_id", userId);
    setBusy(false);
    if (failed) {
      setError(problem(failed));
      return;
    }
    setStopping(false);
    setStopped(true);
    setRow(null);
    setChoices(DEFAULT_CHOICES);
    setSaved("");
  }

  if (row === undefined) {
    return error ? <p class="warn">{error}</p> : <p class="note">Loading.</p>;
  }

  const who = (
    <p class="note">
      Signed in as {email}.{" "}
      <button class="quiet" type="button" onClick={() => signOut("/")}>
        Sign out
      </button>
    </p>
  );

  if (row === null) {
    return (
      <>
        {stopped && (
          <p class="good" role="status">
            Your alerts are stopped and your choices are removed.
          </p>
        )}
        <form class="plain" onSubmit={create}>
          <h2>Choose your alerts</h2>
          <ChoiceFields value={choices} onChange={setChoices} />
          <div class="row">
            <button type="submit" disabled={busy || choices.states.length === 0}>
              Save my choices
            </button>
          </div>
          {choices.states.length === 0 && <p class="note">Tick at least one state.</p>}
          {error && <p class="warn">{error}</p>}
        </form>
        {who}
      </>
    );
  }

  const current = row.confirmed_at !== null && row.email === email;
  return (
    <>
      {saved && (
        <p class="good" role="status">
          {saved}
        </p>
      )}
      {current ? (
        <p>
          Alerts go to <strong>{email}</strong>. You confirmed on {localDay(row.confirmed_at)}.
        </p>
      ) : (
        <div class="step">
          <h2>One step left</h2>
          <p>
            {row.confirmed_at
              ? "Your account's address changed. "
              : "Your choices are saved, and no alert is sent yet. "}
            Confirm that alerts should go to <strong>{email}</strong>.
          </p>
          <div class="row">
            <button
              type="button"
              disabled={busy}
              onClick={() => act(confirm, "Your address is confirmed.")}
            >
              Confirm and start my alerts
            </button>
          </div>
        </div>
      )}

      <form class="plain" onSubmit={update}>
        <h2>What you get</h2>
        <ChoiceFields value={choices} onChange={setChoices} />
        <div class="row">
          <button type="submit" disabled={busy || choices.states.length === 0}>
            Save changes
          </button>
        </div>
        {choices.states.length === 0 && (
          <p class="note">Tick at least one state, or stop all alerts below.</p>
        )}
        {error && <p class="warn">{error}</p>}
      </form>

      <h2>Stop</h2>
      {stopping ? (
        <div class="row">
          <span>Stop every alert and remove your choices?</span>
          <button type="button" disabled={busy} onClick={stop}>
            Yes, stop them
          </button>
          <button class="quiet" type="button" onClick={() => setStopping(false)}>
            Keep them
          </button>
        </div>
      ) : (
        <p>
          <button class="quiet" type="button" onClick={() => setStopping(true)}>
            Stop all alerts
          </button>
        </p>
      )}
      {who}
    </>
  );
}

/** A subscriber's own page: confirm, change what they get, or stop. */
export default function AccountPage() {
  const user = useUser();
  if (!configured) {
    return <p class="warn">This copy of the site was built without a database address.</p>;
  }
  if (user.loading) return <p class="note">Loading.</p>;
  if (!user.userId || !user.email) return <SignIn />;
  return <Manage userId={user.userId} email={user.email} />;
}
