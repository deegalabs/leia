/* Documentation shown at /docs: markdown copied from the repository by scripts/sync-docs.mjs (content/docs/*.md). */
export type DocEntry = { slug: string; title: string; file: string; source: string; group: string };

export const DOCS: DocEntry[] = [
  { slug: "inicio", title: "Visão geral", file: "README.md", source: "README.md", group: "Produto" },
  { slug: "posicionamento", title: "Posicionamento e limites", file: "POSITIONING.md", source: "docs/POSITIONING.md", group: "Produto" },
  { slug: "casos-de-uso", title: "Personas e casos de uso", file: "USE-CASES.md", source: "docs/USE-CASES.md", group: "Produto" },
  { slug: "telas", title: "Telas", file: "SCREENS.md", source: "docs/SCREENS.md", group: "Produto" },
  { slug: "situacao", title: "Situação em 13/09/2026", file: "STATUS.md", source: "docs/STATUS.md", group: "Produto" },
  { slug: "arquitetura", title: "Arquitetura", file: "ARCHITECTURE.md", source: "docs/ARCHITECTURE.md", group: "Técnico" },
  { slug: "api", title: "API do serviço", file: "API-V3-CONTRACT.md", source: "docs/API-V3-CONTRACT.md", group: "Técnico" },
  { slug: "servico", title: "Mapa do serviço cognitivo", file: "SERVICE-V2-MAP.md", source: "docs/SERVICE-V2-MAP.md", group: "Técnico" },
  { slug: "escala", title: "Escala e custo", file: "SCALING.md", source: "docs/SCALING.md", group: "Técnico" },
  { slug: "auditoria", title: "Roteiro de auditoria", file: "AUDIT-GUIDE.md", source: "docs/AUDIT-GUIDE.md", group: "Hackathon" },
  { slug: "entregas", title: "Entregas versionadas", file: "DELIVERIES.md", source: "docs/DELIVERIES.md", group: "Hackathon" },
  { slug: "roadmap", title: "Roadmap", file: "ROADMAP.md", source: "docs/ROADMAP.md", group: "Hackathon" },
  { slug: "contribuir", title: "Como contribuir", file: "CONTRIBUTING.md", source: "docs/CONTRIBUTING.md", group: "Hackathon" },
];

export const REPO_URL = "https://github.com/deegalabs/leia";
export const docBySlug = (slug: string) => DOCS.find((d) => d.slug === slug) ?? null;
