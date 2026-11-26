import { defineConfig } from "astro/config";
import preact from "@astrojs/preact";

// Where the site sits on its domain. "/" at the root, or a path such as "/radar" when it is
// served under someone else's domain. Set when the site is built:
//
//     RADAR_BASE_PATH=/radar npm run build
//
// Every link in the site goes through href() in src/lib/paths.ts, which reads this.
const base = (process.env.RADAR_BASE_PATH ?? "").trim() || "/";
if (!base.startsWith("/")) {
  throw new Error(`RADAR_BASE_PATH must start with a slash: ${JSON.stringify(base)}`);
}

// A static site. Every page that shows data reads it in the browser with the visitor's own
// session, so the database's policies decide what anyone sees.
export default defineConfig({
  base,
  integrations: [preact()],
  server: { host: "127.0.0.1", port: 4321 },
});
