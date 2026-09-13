import type { NextConfig } from "next";
import { readFileSync } from "node:fs";
import { execSync } from "node:child_process";

const pkg = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf8")) as { version: string };
let sha = process.env.VERCEL_GIT_COMMIT_SHA || process.env.GIT_COMMIT_SHA || "";
if (!sha) { try { sha = execSync("git rev-parse HEAD", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim(); } catch { sha = "dev"; } }

const nextConfig: NextConfig = {
  /* Build identity for the version badge and the update prompt */
  env: { NEXT_PUBLIC_APP_VERSION: pkg.version, NEXT_PUBLIC_COMMIT_SHA: sha.slice(0, 7) },
};

export default nextConfig;
