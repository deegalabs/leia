"use client";
import { useMemo } from "react";
import type { Inferences, InferenceClass, InferenceItem } from "@/lib/inferences";
import { fmt, m } from "@/lib/i18n";
import { Card, StatusChip } from "./ui";

/* Original text with the tagged quotes, the class cards with "Ver no texto", and the helpers to jump to a mark.
   Used by the citizen's document page and by the lawyer's review. */

type Seg = { text: string; item?: InferenceItem };

/* Splits the text into plain and marked segments; overlapping quotes keep the first one. */
export function segments(texto: string, items: InferenceItem[]): Seg[] {
  const spans = items.filter((i) => i.pos).map((i) => ({ s: i.pos![0], e: i.pos![1], item: i })).sort((a, b) => a.s - b.s);
  const out: Seg[] = []; let cursor = 0;
  for (const sp of spans) {
    if (sp.s < cursor) continue;
    if (sp.s > cursor) out.push({ text: texto.slice(cursor, sp.s) });
    out.push({ text: texto.slice(sp.s, sp.e), item: sp.item }); cursor = sp.e;
  }
  if (cursor < texto.length) out.push({ text: texto.slice(cursor) });
  return out;
}

export const markId = (prefix: string, ref: string) => `${prefix}-${ref}`;

/* Scrolls to a mark and flashes a ring around it. Returns false when the mark is not in the page yet. */
export function scrollToMark(prefix: string, ref: string): boolean {
  const el = document.getElementById(markId(prefix, ref));
  if (!el) return false;
  el.scrollIntoView({ block: "center", behavior: "smooth" });
  el.classList.add("ring-4", "ring-teal-deep");
  setTimeout(() => el.classList.remove("ring-4", "ring-teal-deep"), 1600);
  return true;
}

export function MarkedText({ texto, items, idPrefix = "mark" }: { texto: string; items: InferenceItem[]; idPrefix?: string }) {
  const segs = useMemo(() => segments(texto, items), [texto, items]);
  return (
    <div className="whitespace-pre-wrap font-mono text-[0.92rem] leading-relaxed">
      {segs.map((sg, i) => sg.item
        ? <mark key={i} id={markId(idPrefix, sg.item.ref)} style={{ backgroundColor: sg.item.cor }} className="rounded px-0.5 text-ink no-underline" title={`${sg.item.campo ?? ""}: ${sg.item.valor ?? ""}`}>{sg.text}</mark>
        : <span key={i}>{sg.text}</span>)}
    </div>
  );
}

export function MarkCounts({ data }: { data: Pick<Inferences, "total" | "conferidos"> }) {
  return (
    <div className="flex flex-wrap gap-2">
      <StatusChip tone="ok">{fmt(m.panel.review.checkedCount, { n: data.conferidos })}</StatusChip>
      {data.total - data.conferidos > 0 && <StatusChip tone="pending">{fmt(m.panel.review.notFoundCount, { n: data.total - data.conferidos })}</StatusChip>}
    </div>
  );
}

/* One card per class: field, value, quote, "checked" seal and the jump button. */
export function ClassCards({ classes, onView, withSeal = false }: { classes: InferenceClass[]; onView: (ref: string) => void; withSeal?: boolean }) {
  return (
    <>
      {classes.map((c) => (
        <Card key={c.classe}>
          <h2 className="mb-2 flex items-center gap-2 text-[1.1rem]"><span aria-hidden className="inline-block h-4 w-4 rounded" style={{ backgroundColor: c.cor }} />{c.rotulo} <span className="text-[0.9rem] font-normal text-ink-2">({c.itens.length})</span></h2>
          <ul className="space-y-2">
            {c.itens.map((it) => (
              <li key={it.ref} className="rounded-[10px] border border-line p-2.5 text-[0.95rem]">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p><span className="font-bold">{(it.campo ?? "").replace(/_/g, " ")}</span>{it.valor ? `: ${it.valor}` : ""}</p>
                  {withSeal && <StatusChip tone={it.conferido ? "ok" : "pending"}>{it.conferido ? m.panel.review.checked : m.panel.review.notLocated}</StatusChip>}
                </div>
                <p className="mt-1 text-ink-2">“{it.trecho}”</p>
                {it.conferido
                  ? <button type="button" onClick={() => onView(it.ref)} className="mt-1 min-h-[44px] font-bold text-teal-deep underline underline-offset-2">{m.panel.review.viewInText}</button>
                  : !withSeal && <p className="mt-1 text-[0.9rem] text-pend">Não localizado palavra por palavra no texto.</p>}
              </li>
            ))}
          </ul>
        </Card>
      ))}
    </>
  );
}

/* Highlighted text next to the class cards (the citizen's document page layout). */
export function InferenceMarks({ inferences, showClasses = true, idPrefix = "mark" }: { inferences: Inferences; showClasses?: boolean; idPrefix?: string }) {
  const allItems = useMemo(() => inferences.classes.flatMap((c) => c.itens), [inferences]);
  const text = (
    <Card>
      <h2 className="mb-2 text-[1.15rem]">{m.panel.review.textTitle}</h2>
      <MarkedText texto={inferences.texto} items={allItems} idPrefix={idPrefix} />
    </Card>
  );
  if (!showClasses) return text;
  return (
    <div className="grid gap-4 md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      {text}
      <div className="space-y-3"><ClassCards classes={inferences.classes} onView={(ref) => scrollToMark(idPrefix, ref)} /></div>
    </div>
  );
}
