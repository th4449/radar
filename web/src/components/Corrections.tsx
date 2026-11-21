import { useEffect, useState } from "preact/hooks";
import { fetchAlert, type PublicAlert } from "../lib/alerts";
import { idFrom } from "../lib/choices";
import { problem } from "../lib/format";
import { configured, supabase } from "../lib/supabase";

/** Anyone may send a correction. No account is needed. Only administrators read it. */
export default function Corrections() {
  const alertId = idFrom(window.location.search, "alert");
  const [alert, setAlert] = useState<PublicAlert | null>(null);
  const [message, setMessage] = useState("");
  const [contact, setContact] = useState("");
  const [trap, setTrap] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!configured || alertId === null) return;
    fetchAlert(alertId)
      .then(setAlert)
      .catch(() => setAlert(null));
  }, [alertId]);

  async function send(event: Event) {
    event.preventDefault();
    // A field people cannot see. Only a script fills it in.
    if (trap) {
      setSent(true);
      return;
    }
    setBusy(true);
    setError("");
    const { error: failed } = await supabase.rpc("submit_correction", {
      p_message: message.trim(),
      p_alert_id: alert ? alert.alert_id : null,
      p_contact: contact.trim() || null,
    });
    setBusy(false);
    if (failed) setError(problem(failed));
    else setSent(true);
  }

  if (!configured) {
    return <p class="warn">This copy of the site was built without a database address.</p>;
  }
  if (sent) {
    return (
      <p class="good" role="status">
        Your correction was sent. An administrator at Dekleptocracy Alliance will read it.
      </p>
    );
  }
  const short = message.trim().length < 10;
  return (
    <form class="plain" onSubmit={send}>
      {alert && (
        <p>
          About the alert <a href={`/alert/?id=${alert.alert_id}`}>{alert.headline}</a>.
        </p>
      )}
      <label for="message">What is wrong, and what the record says</label>
      <textarea
        id="message"
        required
        maxLength={4000}
        value={message}
        onInput={(e) => setMessage((e.target as HTMLTextAreaElement).value)}
      />
      <p class="note">Link the record if you can. Do not include anyone's private details.</p>
      <label for="contact">How to reach you (optional)</label>
      <input
        id="contact"
        type="text"
        maxLength={200}
        autocomplete="email"
        value={contact}
        onInput={(e) => setContact((e.target as HTMLInputElement).value)}
      />
      <p class="note">Only the organization's administrators see this.</p>
      <div class="trap" aria-hidden="true">
        <label for="website">Leave this empty</label>
        <input
          id="website"
          type="text"
          tabIndex={-1}
          autocomplete="off"
          value={trap}
          onInput={(e) => setTrap((e.target as HTMLInputElement).value)}
        />
      </div>
      <div class="row">
        <button type="submit" disabled={busy || short}>
          Send the correction
        </button>
      </div>
      {error && <p class="warn">{error}</p>}
    </form>
  );
}
