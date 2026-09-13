import { writeFileSync } from "node:fs";

const apiBase = (process.env.HATCOMMWAYS_API_BASE || "").trim().replace(/\/+$/, "");

if (!apiBase) {
  console.error("HATCOMMWAYS_API_BASE is required to generate runtime-config.js.");
  process.exit(1);
}

function serialize(value) {
  return JSON.stringify(value || "")
    .replaceAll("<", "\\u003c")
    .replaceAll("\u2028", "\\u2028")
    .replaceAll("\u2029", "\\u2029");
}

const source = [
  "// Generated at deploy time. Do not commit this file.",
  `window.HATCOMMWAYS_API_BASE = ${serialize(apiBase)};`,
  `window.HATCOMMWAYS_GOOGLE_MAPS_API_KEY = ${serialize(process.env.HATCOMMWAYS_GOOGLE_MAPS_API_KEY)};`,
  `window.HATCOMMWAYS_GOOGLE_MAPS_MAP_ID = ${serialize(process.env.HATCOMMWAYS_GOOGLE_MAPS_MAP_ID)};`,
  "",
].join("\n");

writeFileSync(new URL("./runtime-config.js", import.meta.url), source, "utf8");
console.log("Generated apps/web/runtime-config.js.");
