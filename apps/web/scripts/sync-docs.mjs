/* Copies the repository documentation into content/docs/ for the /docs pages.
   Runs before dev and build; skips quietly when the repository docs are not present (e.g. on Vercel, where the
   committed copies are used). Links to other docs become /docs/<slug>; other repository links go to GitHub. */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repo = join(here, "..", "..", "..");
const out = join(here, "..", "content", "docs");
const REPO_URL = "https://github.com/deegalabs/leia";

const DOCS = [
  ["README.md", "README.md"], ["docs/POSITIONING.md", "POSITIONING.md"], ["docs/USE-CASES.md", "USE-CASES.md"],
  ["docs/SCREENS.md", "SCREENS.md"], ["docs/DOCUMENT-TYPES.md", "DOCUMENT-TYPES.md"], ["docs/STATUS.md", "STATUS.md"], ["docs/ARCHITECTURE.md", "ARCHITECTURE.md"],
  ["docs/API-V3-CONTRACT.md", "API-V3-CONTRACT.md"], ["docs/SERVICE-V2-MAP.md", "SERVICE-V2-MAP.md"],
  ["docs/RESUMO-ESTRUTURADO-E-CHAT.md", "RESUMO-ESTRUTURADO-E-CHAT.md"], ["docs/SCALING.md", "SCALING.md"],
  ["docs/AUDIT-GUIDE.md", "AUDIT-GUIDE.md"], ["docs/DELIVERIES.md", "DELIVERIES.md"], ["docs/ROADMAP.md", "ROADMAP.md"],
  ["docs/CONTRIBUTING.md", "CONTRIBUTING.md"],
];
const SLUGS = {
  "README.md": "inicio", "POSITIONING.md": "posicionamento", "USE-CASES.md": "casos-de-uso", "SCREENS.md": "telas", "DOCUMENT-TYPES.md": "tipos-de-documento",
  "STATUS.md": "situacao", "ARCHITECTURE.md": "arquitetura", "API-V3-CONTRACT.md": "api", "SERVICE-V2-MAP.md": "servico",
  "RESUMO-ESTRUTURADO-E-CHAT.md": "resumo-estruturado-e-chat", "SCALING.md": "escala", "AUDIT-GUIDE.md": "auditoria",
  "DELIVERIES.md": "entregas", "ROADMAP.md": "roadmap", "CONTRIBUTING.md": "contribuir",
};

if (!existsSync(join(repo, "docs"))) { console.log("sync-docs: repository docs not found, keeping committed copies"); process.exit(0); }
mkdirSync(out, { recursive: true });
let n = 0;
for (const [src, name] of DOCS) {
  const path = join(repo, src);
  if (!existsSync(path)) continue;
  let md = readFileSync(path, "utf8");
  /* banner and badges are GitHub chrome: the documentation site has its own header */
  md = md.replace(/<!--\s*github-only:start\s*-->[\s\S]*?<!--\s*github-only:end\s*-->\n?/g, "");
  md = md.replace(/<img[^>]*logo-dark\.jpg[^>]*>/g, "");
  /* markdown links to repository files */
  md = md.replace(/\]\(((?:\.\.\/|\.\/)?(?:docs\/)?[A-Za-z0-9_.\-]+\.md)(#[^)]*)?\)/g, (m, target, hash) => {
    const base = target.split("/").pop();
    const slug = SLUGS[base];
    return slug ? `](/docs/${slug}${hash ?? ""})` : `](${REPO_URL}/blob/main/${target.replace(/^(\.\.\/)+/, "")})`;
  });
  md = md.replace(/\]\(((?:apps|evidence|examples|prompts|scripts|docs\/brand|docs\/design)\/[^)]+)\)/g, (m, target) => `](${REPO_URL}/blob/main/${target})`);
  writeFileSync(join(out, name), md);
  n++;
}
console.log(`sync-docs: ${n} files copied to content/docs`);
