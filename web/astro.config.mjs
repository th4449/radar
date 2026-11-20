import { defineConfig } from "astro/config";
import preact from "@astrojs/preact";

// A static site. Every page that shows data reads it in the browser with the visitor's own
// session, so the database's policies decide what anyone sees.
export default defineConfig({
  integrations: [preact()],
  server: { host: "127.0.0.1", port: 4321 },
});
