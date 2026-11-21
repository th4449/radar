import { useEffect, useState } from "preact/hooks";
import { supabase } from "./supabase";
import type { Reviewer } from "./types";

export interface Account {
  loading: boolean;
  userId: string | null;
  email: string | null;
  reviewer: Reviewer | null;
  approved: boolean;
  admin: boolean;
  /** Read the reviewer row again, after applying. */
  refresh: () => void;
}

/** Who is signed in, and what the database says they are. */
export function useAccount(): Account {
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [reviewer, setReviewer] = useState<Reviewer | null>(null);
  const [tick, setTick] = useState(0);

  // Subscribe once. The client reports the session it starts with as an event too, so
  // re-subscribing on every event would reload forever.
  useEffect(() => {
    const { data: listener } = supabase.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_IN" || event === "SIGNED_OUT" || event === "USER_UPDATED") {
        // Never call the client from inside this callback: it holds a lock. Defer the reload.
        setTimeout(() => setTick((n) => n + 1), 0);
      }
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    let live = true;
    async function load() {
      const { data } = await supabase.auth.getSession();
      const user = data.session?.user ?? null;
      let row: Reviewer | null = null;
      if (user) {
        const found = await supabase
          .from("reviewers")
          .select("user_id, display_name, status, role, applied_at, approved_at")
          .eq("user_id", user.id)
          .maybeSingle();
        row = (found.data as Reviewer | null) ?? null;
      }
      if (!live) return;
      setUserId(user?.id ?? null);
      setEmail(user?.email ?? null);
      setReviewer(row);
      setLoading(false);
    }
    load();
    return () => {
      live = false;
    };
  }, [tick]);

  const approved = reviewer?.status === "approved";
  return {
    loading,
    userId,
    email,
    reviewer,
    approved,
    admin: approved && reviewer?.role === "admin",
    refresh: () => setTick((n) => n + 1),
  };
}

export async function signOut(to = "/review/"): Promise<void> {
  await supabase.auth.signOut();
  window.location.assign(to);
}

export interface User {
  loading: boolean;
  userId: string | null;
  email: string | null;
}

/** Who is signed in, for pages that have nothing to do with reviewing. */
export function useUser(): User {
  const [user, setUser] = useState<User>({ loading: true, userId: null, email: null });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const { data: listener } = supabase.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_IN" || event === "SIGNED_OUT" || event === "USER_UPDATED") {
        setTimeout(() => setTick((n) => n + 1), 0);
      }
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    let live = true;
    supabase.auth.getSession().then(({ data }) => {
      if (!live) return;
      const found = data.session?.user ?? null;
      setUser({ loading: false, userId: found?.id ?? null, email: found?.email ?? null });
    });
    return () => {
      live = false;
    };
  }, [tick]);

  return user;
}
