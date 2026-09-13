/* Writes public/sw.js from scripts/sw.template.js with a build id (commit sha on Vercel, timestamp elsewhere). */
import { readFileSync, writeFileSync } from "node:fs";
import { execSync } from "node:child_process";
const dir = new URL(".", import.meta.url).pathname;
let sha = process.env.VERCEL_GIT_COMMIT_SHA || process.env.GIT_COMMIT_SHA || "";
if (!sha) { try { sha = execSync("git rev-parse HEAD", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim(); } catch { sha = ""; } }
const buildId = (sha ? sha.slice(0, 7) : "dev") + "-" + Date.now().toString(36);
const out = readFileSync(dir + "sw.template.js", "utf8").replace("__BUILD_ID__", buildId);
writeFileSync(dir + "../public/sw.js", out);
console.log("sw.js build id:", buildId);
