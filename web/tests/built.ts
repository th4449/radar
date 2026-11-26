// Reads a built site and finds any address that points outside the path the site was built
// for. Used by a test and, on a real build, from the command line:
//
//     node tests/built.ts dist /radar
//
// It ends with an error and lists what it found, or says the build is clean.

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { basePrefix } from "../src/lib/paths.ts";

// How a script uses an address it wrote by hand. A built script holds every path of the site as
// text, because each one is handed to href(): `href:f("/account/")`. Those are right. What is
// wrong is a path put straight into a link or a redirect, with no helper around it.
const BY_HAND_IN_SCRIPT = [
  /\b(?:href|src|action):\s*(["'`])(\/(?!\/)[^"'`]*)\1/g, // href:"/review/"
  /location\.(?:assign|replace)\(\s*(["'`])(\/(?!\/)[^"'`]*)\1/g, // location.assign("/alert/…")
  /location\.href\s*=\s*(["'`])(\/(?!\/)[^"'`]*)\1/g,
  /location\.origin\}(\/)([^`]*)`/g, // `${window.location.origin}/account/`
];

/** Each address that starts at the root of the domain and is not under the base path. */
export function strayAddresses(
  text: string,
  base: string,
  kind: "html" | "script" = "html",
): string[] {
  const prefix = basePrefix(base);
  if (!prefix) return []; // at the root of a domain every address from the root is the site's
  const under = (address: string) => address === prefix || address.startsWith(`${prefix}/`);
  const found: string[] = [];
  if (kind === "html") {
    for (const m of text.matchAll(/\b(href|src|action)=(["'])(\/(?!\/)[^"']*)\2/g)) {
      if (!under(m[3])) found.push(`${m[1]}="${m[3]}"`);
    }
  } else {
    for (const pattern of BY_HAND_IN_SCRIPT) {
      for (const m of text.matchAll(pattern)) found.push(m[0]);
    }
  }
  return found;
}

function files(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    return entry.isDirectory() ? files(path) : [path];
  });
}

/** Every stray address in a built site, each with the file it is in. */
export function strayInBuild(dir: string, base: string): string[] {
  const found: string[] = [];
  for (const file of files(dir)) {
    const kind = file.endsWith(".html") ? "html" : /\.m?js$/.test(file) ? "script" : null;
    if (!kind) continue;
    const text = readFileSync(file, "utf8");
    for (const address of strayAddresses(text, base, kind)) found.push(`${file}: ${address}`);
    // A page's own scripts are written into it.
    if (kind === "html") {
      for (const m of text.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) {
        for (const address of strayAddresses(m[1], base, "script")) found.push(`${file}: ${address}`);
      }
    }
  }
  return found;
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].split("/").pop() ?? "\0")) {
  const [dir, base] = process.argv.slice(2);
  if (!dir || base === undefined) {
    console.error("usage: node tests/built.ts <built folder> <base path>");
    process.exit(2);
  }
  const found = strayInBuild(dir, base);
  const pages = files(dir).filter((f) => f.endsWith(".html")).length;
  if (found.length === 0) {
    console.log(`${pages} pages built for ${basePrefix(base) || "/"}: every address stays inside.`);
  } else {
    console.error(`${found.length} addresses point outside ${basePrefix(base)}:`);
    for (const line of found) console.error(`  ${line}`);
    process.exit(1);
  }
}
