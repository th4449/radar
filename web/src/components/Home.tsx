import { useState } from "preact/hooks";
import { Frame } from "./Frame";
import { problem } from "../lib/format";
import type { Account } from "../lib/session";
import { supabase } from "../lib/supabase";

function SignIn() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(event: Event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const { error: failed } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: { emailRedirectTo: `${window.location.origin}/review/` },
    });
    setBusy(false);
    if (failed) setError(problem(failed));
    else setSent(true);
  }

  if (sent) {
    return (
      <p>
        A sign-in link is on its way to <strong>{email.trim()}</strong>. Open it on this device.
        You can close this page.
      </p>
    );
  }
  return (
    <form class="plain" onSubmit={send}>
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
        <button type="submit" disabled={busy}>
          Send the sign-in link
        </button>
      </div>
      {error && <p class="warn">{error}</p>}
    </form>
  );
}

function Apply({ account }: { account: Account }) {
  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function apply(event: Event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const { error: failed } = await supabase.from("reviewers").insert({
      user_id: account.userId,
      display_name: name.trim(),
      application_note: note.trim() || null,
      agreed_terms_at: new Date().toISOString(),
    });
    setBusy(false);
    if (failed) setError(problem(failed));
    else account.refresh();
  }

  return (
    <form class="plain" onSubmit={apply}>
      <h2>Apply to review</h2>
      <p>
        Reviewers check each possible alert against its source record before anything is
        published. Dekleptocracy Alliance approves every reviewer. Applying gives you no access
        until it does.
      </p>
      <label for="name">Your name, as other reviewers will see it</label>
      <input
        id="name"
        type="text"
        required
        maxLength={120}
        value={name}
        onInput={(e) => setName((e.target as HTMLInputElement).value)}
      />
      <label for="note">Who you are and why you want to review</label>
      <textarea
        id="note"
        maxLength={2000}
        value={note}
        onInput={(e) => setNote((e.target as HTMLTextAreaElement).value)}
      />
      <p class="note">Only the organization's administrators read this.</p>
      <label class="inline">
        <input
          type="checkbox"
          checked={agreed}
          onChange={(e) => setAgreed((e.target as HTMLInputElement).checked)}
        />
        <span>
          I have read and agree to the <a href="/review/terms/">reviewer terms</a>.
        </span>
      </label>
      <div class="row">
        <button type="submit" disabled={busy || !agreed || !name.trim()}>
          Send my application
        </button>
      </div>
      {error && <p class="warn">{error}</p>}
    </form>
  );
}

function Standing({ account }: { account: Account }) {
  const reviewer = account.reviewer;
  if (!reviewer) return <Apply account={account} />;
  if (reviewer.status === "pending") {
    return (
      <>
        <h2>Your application is with the organization</h2>
        <p>
          You applied as <strong>{reviewer.display_name}</strong>. An administrator at
          Dekleptocracy Alliance will decide. Until then you cannot see or review anything.
        </p>
      </>
    );
  }
  if (reviewer.status === "suspended") {
    return (
      <>
        <h2>Your reviewer access is suspended</h2>
        <p>An administrator suspended this account. Contact the organization if this is a mistake.</p>
      </>
    );
  }
  return (
    <>
      <h2>You are an approved reviewer</h2>
      <p>
        Signed in as <strong>{reviewer.display_name}</strong>
        {account.admin ? ", an administrator" : ""}.
      </p>
      <p>
        <a href="/review/queue/">Open the review queue</a>
        {account.admin && (
          <>
            {" "}
            or <a href="/review/admin/">the administrator desk</a>
          </>
        )}
        .
      </p>
    </>
  );
}

export default function Home() {
  return (
    <Frame need="anyone">
      {(account) => (
        <>
          <h1>Reviewer desk</h1>
          <p class="lede">
            The radar collects public records that can be early signs of a data center. A person
            checks each one against its source before it becomes an alert. This is where that
            happens.
          </p>
          {account.userId ? <Standing account={account} /> : <SignIn />}
        </>
      )}
    </Frame>
  );
}
