import Link from "next/link";
import { BookOpen, ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { DOCS, REPO_URL, type DocEntry } from "@/lib/docs";

/* Documentation layout: sidebar with grouped sections, content, previous/next pager (as in the team's other products). */
export function DocsShell({ current, html }: { current: DocEntry; html: string }) {
  const idx = DOCS.findIndex((d) => d.slug === current.slug);
  const prev = idx > 0 ? DOCS[idx - 1] : null;
  const next = idx < DOCS.length - 1 ? DOCS[idx + 1] : null;
  const groups = Array.from(new Set(DOCS.map((d) => d.group)));
  return (
    <main className="flex-1">
      <header className="bg-navy px-4 py-3 text-paper">
        <div className="mx-auto flex max-w-[1100px] items-center justify-between gap-3">
          <Link href="/" className="inline-flex items-center gap-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo-horizontal-dark.svg" alt="LeIA" className="h-7" />
          </Link>
          <span className="inline-flex items-center gap-2 text-[0.95rem] text-paper/85"><BookOpen size={18} aria-hidden /> Documentação</span>
        </div>
      </header>
      <div className="mx-auto grid max-w-[1100px] gap-6 px-4 py-6 md:grid-cols-[240px_minmax(0,1fr)]">
        <nav aria-label="Seções da documentação" className="md:sticky md:top-4 md:self-start">
          <details className="md:hidden rounded-card border border-line bg-surface p-3" open={false}>
            <summary className="min-h-[44px] cursor-pointer font-bold">Seções</summary>
            <DocsNav groups={groups} current={current.slug} />
          </details>
          <div className="hidden md:block"><DocsNav groups={groups} current={current.slug} /></div>
        </nav>
        <article>
          <p className="mb-2 text-[0.9rem] text-ink-2">{current.group}</p>
          <div className="docs-prose" dangerouslySetInnerHTML={{ __html: html }} />
          <p className="mt-6 text-[0.9rem] text-ink-2">
            Fonte: <a className="text-teal-deep underline underline-offset-2" href={`${REPO_URL}/blob/main/${current.source}`} target="_blank" rel="noreferrer">{current.source} <ExternalLink size={14} aria-hidden className="inline" /></a>
          </p>
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            {prev ? <Link href={`/docs/${prev.slug}`} className="inline-flex min-h-[48px] items-center gap-2 rounded-card border border-line bg-surface px-4 py-3 font-bold text-teal-deep"><ChevronLeft size={18} aria-hidden /> {prev.title}</Link> : <span />}
            {next && <Link href={`/docs/${next.slug}`} className="inline-flex min-h-[48px] items-center justify-end gap-2 rounded-card border border-line bg-surface px-4 py-3 font-bold text-teal-deep">{next.title} <ChevronRight size={18} aria-hidden /></Link>}
          </div>
        </article>
      </div>
    </main>
  );
}

function DocsNav({ groups, current }: { groups: string[]; current: string }) {
  return (
    <ul className="mt-2 space-y-3 md:mt-0">
      {groups.map((g) => (
        <li key={g}>
          <p className="mb-1 text-[0.85rem] font-bold uppercase tracking-wide text-ink-2">{g}</p>
          <ul>
            {DOCS.filter((d) => d.group === g).map((d) => (
              <li key={d.slug}>
                <Link href={`/docs/${d.slug}`} aria-current={d.slug === current ? "page" : undefined}
                  className={`block min-h-[44px] rounded-[10px] px-3 py-2.5 ${d.slug === current ? "bg-teal-soft font-bold text-ink" : "text-ink-2 hover:bg-muted"}`}>{d.title}</Link>
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}
