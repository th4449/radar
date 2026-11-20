import type { ComponentChildren } from "preact";
import { signOut, useAccount, type Account } from "../lib/session";
import { configured } from "../lib/supabase";

type Need = "anyone" | "reviewer" | "admin";

interface Props {
  need: Need;
  children: (account: Account) => ComponentChildren;
}

/** The masthead, and the check that the visitor may see the page under it. */
export function Frame({ need, children }: Props) {
  const account = useAccount();

  let body: ComponentChildren;
  if (!configured) {
    body = (
      <p class="warn">
        This copy of the site was built without a database address. Set PUBLIC_SUPABASE_URL and
        PUBLIC_SUPABASE_ANON_KEY and build it again.
      </p>
    );
  } else if (account.loading) {
    body = <p class="note">Loading.</p>;
  } else if (need === "reviewer" && !account.approved) {
    body = (
      <p>
        This page is for approved reviewers. <a href="/review/">Go to the reviewer desk</a> to sign
        in or to see where your application stands.
      </p>
    );
  } else if (need === "admin" && !account.admin) {
    body = (
      <p>
        This page is for administrators. <a href="/review/">Go to the reviewer desk.</a>
      </p>
    );
  } else {
    body = children(account);
  }

  return (
    <>
      <header class="masthead">
        <a class="name" href="/review/">
          Radar reviewer desk
        </a>
        <nav aria-label="Reviewer desk">
          {account.approved && <a href="/review/queue/">Queue</a>}
          {account.admin && <a href="/review/admin/">Administrator</a>}
          <a href="/review/terms/">Reviewer terms</a>
        </nav>
        {account.email && (
          <span class="who">
            {account.email}{" "}
            <button class="quiet" type="button" onClick={() => signOut()}>
              Sign out
            </button>
          </span>
        )}
      </header>
      <main>{body}</main>
    </>
  );
}
