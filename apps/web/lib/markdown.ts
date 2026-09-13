import { readFileSync } from "node:fs";
import { join, posix } from "node:path";
import { Marked, type Tokens } from "marked";
import { DOCS, REPO_URL, type DocEntry } from "./docs";

/* Server-side markdown for the documentation pages. The content is the team's own repository docs.
   - Headings get stable ids; the h2 list comes back as a table of contents.
   - Relative links to other repository files open the matching /docs page, or the file on GitHub.
   - Tables get a scroll wrapper (keyboard reachable), ARIA roles and a data-label per cell so the stylesheet
     can stack them as cards on narrow screens without losing the header of each value. */
export type TocItem = { id: string; text: string };
type RenderContext = { toc: TocItem[]; seen: Map<string, number>; source: string };

const escapeAttr = (s: string) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const plain = (html: string) => html.replace(/<[^>]+>/g, "").replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&").replace(/\s+/g, " ").trim();
const slugify = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9\s-]/g, "").trim().replace(/\s+/g, "-").slice(0, 80) || "secao";
/* a break opportunity after each slash lets long routes and paths wrap between segments instead of mid-word */
const breakable = (html: string) => html.replace(/<code>([^<]*)<\/code>/g, (_m, t: string) => `<code>${t.replace(/\//g, "/<wbr>")}</code>`);

let ctx: RenderContext = { toc: [], seen: new Map(), source: "" };

function resolveLink(href: string, source: string): string {
  if (/^([a-z][a-z0-9+.-]*:|#|\/)/i.test(href)) return href; // absolute URL, anchor or site path
  const [path, hash] = href.split("#");
  const resolved = posix.normalize(posix.join(posix.dirname(source), path));
  const suffix = hash ? `#${hash}` : "";
  const entry = DOCS.find((d) => d.source === resolved);
  return entry ? `/docs/${entry.slug}${suffix}` : `${REPO_URL}/blob/main/${resolved}${suffix}`;
}

const md = new Marked({
  gfm: true,
  breaks: false,
  renderer: {
    heading(token: Tokens.Heading) {
      const text = this.parser.parseInline(token.tokens);
      const base = slugify(plain(text));
      const n = ctx.seen.get(base) ?? 0;
      ctx.seen.set(base, n + 1);
      const id = n ? `${base}-${n}` : base;
      if (token.depth === 2) ctx.toc.push({ id, text: plain(text) });
      return `<h${token.depth} id="${id}">${text}</h${token.depth}>\n`;
    },
    link(token: Tokens.Link) {
      const href = resolveLink(token.href, ctx.source);
      const title = token.title ? ` title="${escapeAttr(token.title)}"` : "";
      const external = /^https?:\/\//i.test(href) ? ' target="_blank" rel="noreferrer"' : "";
      return `<a href="${escapeAttr(href)}"${title}${external}>${this.parser.parseInline(token.tokens)}</a>`;
    },
    table(token: Tokens.Table) {
      const inline = (cell: Tokens.TableCell) => breakable(this.parser.parseInline(cell.tokens));
      const labels = token.header.map((h) => plain(inline(h)));
      const align = (a: string | null) => (a ? ` style="text-align:${a}"` : "");
      const head = token.header.map((h) => `<th role="columnheader" scope="col"${align(h.align)}>${inline(h)}</th>`).join("");
      const rows = token.rows.map((row) => {
        const cells = row.map((c, i) => {
          const html = inline(c);
          const empty = plain(html) === "" ? ' data-empty=""' : "";
          return `<td role="cell" data-label="${escapeAttr(labels[i] ?? "")}"${align(c.align)}${empty}>${html}</td>`;
        }).join("");
        return `<tr role="row">${cells}</tr>`;
      }).join("");
      const name = escapeAttr(`Tabela: ${labels.filter(Boolean).join(", ")}`);
      return `<div class="table-wrap" tabindex="0" role="group" aria-label="${name}"><table role="table"><thead role="rowgroup"><tr role="row">${head}</tr></thead><tbody role="rowgroup">${rows}</tbody></table></div>\n`;
    },
  },
});

export function renderDoc(entry: DocEntry): { html: string; toc: TocItem[] } {
  const source = readFileSync(join(process.cwd(), "content", "docs", entry.file), "utf8");
  ctx = { toc: [], seen: new Map(), source: entry.source };
  const html = md.parse(source) as string;
  return { html, toc: ctx.toc };
}
