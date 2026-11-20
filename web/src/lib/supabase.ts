import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = import.meta.env.PUBLIC_SUPABASE_URL as string | undefined;
const key = import.meta.env.PUBLIC_SUPABASE_ANON_KEY as string | undefined;

/** False when the site was built without a database address. The pages then say so. */
export const configured = Boolean(url && key);

// The anonymous key is public by design. What a visitor may read or change is decided by the
// database's policies, never by this code.
export const supabase: SupabaseClient = createClient(
  url ?? "http://127.0.0.1:55321",
  key ?? "not-configured",
);
