/* A documentação vem de markdown do repositório, que agora é público e aceita contribuição.
   Um pull request só de documentação, que ninguém revisa procurando HTML, não pode virar script
   na página: a sessão da pessoa está no navegador e a área de documentação roda na mesma origem. */
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { renderDoc } from "./markdown";
import type { DocEntry } from "./docs";

let dir: string;
const cwd = process.cwd();

function doc(markdown: string): DocEntry {
  const nome = `caso-${Math.abs(hash(markdown))}.md`;
  writeFileSync(join(dir, "content", "docs", nome), markdown, "utf8");
  return { slug: "caso", title: "Caso", file: nome, source: "docs/CASO.md", group: "Técnico" };
}
function hash(s: string) {
  let h = 0;
  for (const c of s) h = (h * 31 + c.charCodeAt(0)) | 0;
  return h;
}
const html = (markdown: string) => renderDoc(doc(markdown)).parts.map((p) => (p.kind === "html" ? p.html : "")).join("");

beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), "leia-docs-"));
  mkdirSync(join(dir, "content", "docs"), { recursive: true });
  process.chdir(dir);
});
afterAll(() => {
  process.chdir(cwd);
  rmSync(dir, { recursive: true, force: true });
});

describe("markdown da documentação", () => {
  it("não deixa passar script embutido", () => {
    const out = html("# Título\n\n<script>window.roubado = localStorage.getItem('leia:auth')</script>\n");
    expect(out).not.toMatch(/<script/i);
    expect(out).toContain("&lt;script");
  });

  it("não deixa passar atributo de evento em tag bruta", () => {
    const out = html('# Título\n\n<img src=x onerror="alert(1)">\n');
    expect(out).not.toMatch(/<img[^>]*onerror/i);
  });

  it("não deixa passar iframe nem objeto embutido", () => {
    const out = html('# Título\n\n<iframe src="https://exemplo.invalido"></iframe>\n');
    expect(out).not.toMatch(/<iframe/i);
  });

  it("recusa esquema de link que executa código", () => {
    const out = html("[clique](javascript:alert(1))\n");
    expect(out).not.toMatch(/href="javascript:/i);
  });

  it("recusa dados embutidos em link", () => {
    const out = html("[clique](data:text/html;base64,PHNjcmlwdD4=)\n");
    expect(out).not.toMatch(/href="data:/i);
  });

  it("continua renderizando o markdown legítimo", () => {
    const out = html("# Título\n\nUm parágrafo com `código` e um [link](https://exemplo.org).\n\n| a | b |\n|---|---|\n| 1 | 2 |\n");
    expect(out).toContain("<h1");
    expect(out).toContain("<code>");
    expect(out).toContain('href="https://exemplo.org"');
    expect(out).toContain("table-wrap");
  });
});
