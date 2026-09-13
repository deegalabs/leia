import Link from "next/link";
import { ArrowUp, BookOpen, ChevronDown, ChevronLeft, ChevronRight, ExternalLink, List } from "lucide-react";
import { DOCS, REPO_URL, type DocEntry } from "@/lib/docs";
import type { TocItem } from "@/lib/markdown";

/* Documentation layout: sidebar with grouped sections, content, previous/next pager (as in the team's other products).
   Below 1024px the sidebar becomes a collapsible section picker above the text and tables stack as cards (see globals.css).
   Long pages get a "Nesta página" list built from the h2 headings. */
export function DocsShell({ current, html, toc }: { current: DocEntry; html: string; toc: TocItem[] }) {
  const idx = DOCS.findIndex((d) => d.slug === current.slug);
  const prev = idx > 0 ? DOCS[idx - 1] : null;
  const next = idx < DOCS.length - 1 ? DOCS[idx + 1] : null;
  const groups = Array.from(new Set(DOCS.map((d) => d.group)));
  return (
    <main className="relative flex-1">
      <a href="#conteudo" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded-button focus:bg-teal focus:px-4 focus:py-2 focus:font-bold focus:text-navy">Pular para o conteúdo</a>
      <header className="bg-navy px-4 py-3 text-paper">
        <div className="mx-auto flex max-w-[1100px] items-center justify-between gap-3">
          <Link href="/" className="inline-flex min-h-[44px] items-center gap-2" aria-label="LeIA, página inicial">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo-horizontal-dark.svg" alt="LeIA" className="h-7" />
          </Link>
          <span className="inline-flex items-center gap-2 text-[0.95rem] text-paper/85"><BookOpen size={18} aria-hidden /> Documentação</span>
        </div>
      </header>
      <div className="mx-auto grid w-full max-w-[1100px] grid-cols-1 gap-6 px-4 py-5 lg:grid-cols-[240px_minmax(0,1fr)] lg:py-6">
        <nav aria-label="Seções da documentação" className="min-w-0 lg:sticky lg:top-4 lg:-m-1.5 lg:max-h-[calc(100vh-2rem)] lg:self-start lg:overflow-y-auto lg:p-1.5">
          <details className="group rounded-card border border-line bg-surface lg:hidden">
            <summary className="flex min-h-[52px] cursor-pointer list-none items-center justify-between gap-3 px-4 py-2 [&::-webkit-details-marker]:hidden">
              <span className="min-w-0 flex-1">
                <span className="block text-[0.8rem] font-bold uppercase tracking-wide text-ink-2">{current.group}</span>
                <span className="block truncate font-bold">{current.title}</span>
              </span>
              <span className="inline-flex shrink-0 items-center gap-1 text-[0.9rem] font-bold text-teal-deep">Seções <ChevronDown size={18} aria-hidden className="transition-transform group-open:rotate-180" /></span>
            </summary>
            <div className="border-t border-line px-2 pb-2 pt-1"><DocsNav groups={groups} current={current.slug} /></div>
          </details>
          <div className="hidden lg:block"><DocsNav groups={groups} current={current.slug} /></div>
        </nav>
        <article id="conteudo" tabIndex={-1} className="min-w-0 outline-none">
          <p className="mb-2 text-[0.9rem] text-ink-2">{current.group}</p>
          {toc.length >= 3 && (
            <details className="group mb-5 rounded-card border border-line bg-surface">
              <summary className="flex min-h-[48px] cursor-pointer list-none items-center justify-between gap-3 px-4 py-2 font-bold [&::-webkit-details-marker]:hidden">
                <span className="inline-flex items-center gap-2"><List size={18} aria-hidden className="text-teal-deep" /> Nesta página <span className="font-normal text-ink-2">({toc.length} seções)</span></span>
                <ChevronDown size={18} aria-hidden className="shrink-0 text-teal-deep transition-transform group-open:rotate-180" />
              </summary>
              <nav aria-label="Nesta página" className="border-t border-line px-4 pb-3 pt-2">
                <ol className="grid gap-1 md:grid-cols-2">
                  {toc.map((t) => <li key={t.id}><a href={`#${t.id}`} className="inline-flex min-h-[40px] items-center text-teal-deep underline underline-offset-4">{t.text}</a></li>)}
                </ol>
              </nav>
            </details>
          )}
          <div className="docs-prose" dangerouslySetInnerHTML={{ __html: html }} />
          <p className="mt-6 text-[0.9rem] text-ink-2">
            Fonte: <a className="break-all text-teal-deep underline underline-offset-2" href={`${REPO_URL}/blob/main/${current.source}`} target="_blank" rel="noreferrer"><ExternalLink size={14} aria-hidden className="mr-1 inline" />{current.source}</a> (abre no GitHub)
          </p>
          <p className="mt-4"><a href="#conteudo" className="inline-flex min-h-[44px] items-center gap-1 font-bold text-teal-deep underline underline-offset-4"><ArrowUp size={16} aria-hidden /> Voltar ao topo</a></p>
          <nav aria-label="Página anterior e próxima" className="mt-6 grid gap-3 sm:grid-cols-2">
            {prev ? (
              <Link href={`/docs/${prev.slug}`} className="inline-flex min-h-[52px] items-center gap-2 rounded-card border border-line bg-surface px-4 py-3 font-bold text-teal-deep">
                <ChevronLeft size={18} aria-hidden className="shrink-0" /><span className="min-w-0"><span className="block text-[0.8rem] font-normal text-ink-2">Anterior</span>{prev.title}</span>
              </Link>
            ) : <span className="hidden sm:block" />}
            {next && (
              <Link href={`/docs/${next.slug}`} className="inline-flex min-h-[52px] items-center justify-end gap-2 rounded-card border border-line bg-surface px-4 py-3 text-right font-bold text-teal-deep">
                <span className="min-w-0"><span className="block text-[0.8rem] font-normal text-ink-2">Próxima</span>{next.title}</span><ChevronRight size={18} aria-hidden className="shrink-0" />
              </Link>
            )}
          </nav>
        </article>
      </div>
    </main>
  );
}

function DocsNav({ groups, current }: { groups: string[]; current: string }) {
  return (
    <ul className="mt-2 space-y-3 lg:mt-0">
      {groups.map((g) => (
        <li key={g}>
          <p className="mb-1 px-3 text-[0.85rem] font-bold uppercase tracking-wide text-ink-2 lg:px-0">{g}</p>
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
