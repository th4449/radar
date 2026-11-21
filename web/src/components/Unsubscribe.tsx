import { useState } from "preact/hooks";
import { tokenFrom } from "../lib/choices";
import { problem } from "../lib/format";
import { configured, supabase } from "../lib/supabase";

/** The link in every email lands here. It needs no sign-in. */
export default function Unsubscribe() {
  const token = tokenFrom(window.location.search);
  const [result, setResult] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function go() {
    setBusy(true);
    setError("");
    const { data, error: failed } = await supabase.rpc("unsubscribe", { p_token: token });
    setBusy(false);
    if (failed) setError(problem(failed));
    else setResult(data === true);
  }

  if (!configured) {
    return <p class="warn">This copy of the site was built without a database address.</p>;
  }
  if (!token) {
    return (
      <p>
        This address is missing its unsubscribe code. Use the link at the foot of any alert
        email, or <a href="/account/">sign in and stop your alerts</a>.
      </p>
    );
  }
  if (result === true) {
    return (
      <p class="good" role="status">
        You are unsubscribed. Your address is off the alert list and you will get no more alerts.
      </p>
    );
  }
  if (result === false) {
    return (
      <p role="status">
        This link no longer works. You are most likely unsubscribed already.{" "}
        <a href="/account/">Sign in to check.</a>
      </p>
    );
  }
  return (
    <>
      <p>Press the button to stop every alert email from the radar to your address.</p>
      <div class="row">
        <button type="button" disabled={busy} onClick={go}>
          Unsubscribe
        </button>
      </div>
      {error && <p class="warn">{error}</p>}
    </>
  );
}
