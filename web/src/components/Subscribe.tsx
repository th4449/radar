import { useState } from "preact/hooks";
import { ChoiceFields } from "./ChoiceFields";
import { DEFAULT_CHOICES, PENDING_KEY, type Choices, type Pending } from "../lib/choices";
import { problem } from "../lib/format";
import { useUser } from "../lib/session";
import { configured, supabase } from "../lib/supabase";
import { absolute, href } from "../lib/paths";

/** Step one of two. The person chooses and gives an address. The emailed link is step two. */
export default function Subscribe() {
  const user = useUser();
  const [choices, setChoices] = useState<Choices>(DEFAULT_CHOICES);
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function send(event: Event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const address = email.trim();
    const pending: Pending = { email: address, choices, at: Date.now() };
    try {
      window.localStorage.setItem(PENDING_KEY, JSON.stringify(pending));
    } catch {
      // Private browsing. The account page asks for the choices again.
    }
    const { error: failed } = await supabase.auth.signInWithOtp({
      email: address,
      options: { emailRedirectTo: absolute("/account/") },
    });
    setBusy(false);
    if (failed) setError(problem(failed));
    else setSent(true);
  }

  if (!configured) {
    return <p class="warn">This copy of the site was built without a database address.</p>;
  }
  if (user.loading) return <p class="note">Loading.</p>;
  if (user.userId) {
    return (
      <p>
        You are signed in as <strong>{user.email}</strong>.{" "}
        <a href={href("/account/")}>Choose or change your alerts.</a>
      </p>
    );
  }
  if (sent) {
    return (
      <>
        <h2>Now confirm your address</h2>
        <p>
          A link is on its way to <strong>{email.trim()}</strong>. Open it on this device to
          confirm. You get no alert until you do.
        </p>
        <p class="note">
          If you open the link on another device, it asks for your states again and then
          confirms.
        </p>
      </>
    );
  }
  return (
    <form class="plain" onSubmit={send}>
      <ChoiceFields value={choices} onChange={setChoices} />
      <label for="email">Your email address</label>
      <input
        id="email"
        type="email"
        required
        autocomplete="email"
        value={email}
        onInput={(e) => setEmail((e.target as HTMLInputElement).value)}
      />
      <div class="row">
        <button type="submit" disabled={busy || choices.states.length === 0 || !email.trim()}>
          Send me the confirmation link
        </button>
      </div>
      {choices.states.length === 0 && <p class="note">Tick at least one state.</p>}
      {error && <p class="warn">{error}</p>}
    </form>
  );
}
