"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { getInferences } from "@/lib/api";
import type { Inferences, InferenceItem } from "@/lib/inferences";
import { AssistantBanner, Card, Page, StatusChip } from "./ui";

type Seg = { text: string; item?: InferenceItem };

/* Splits the text into plain and marked segments; overlapping quotes keep the first one. */
function segments(texto: string, items: InferenceItem[]): Seg[] {
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

export function DocumentView({ hash }: { hash: string }) {
  const [data, setData] = useState<Inferences | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    getInferences(hash).then(setData).catch((e: Error) => setError(e.message.includes("409") ? "A explicação ainda está sendo preparada. Volte em alguns minutos." : e.message.includes("404") ? "Documento não encontrado." : "Deu um problema do nosso lado, não foi você. Tente de novo em instantes."));
  }, [hash]);
  const allItems = useMemo(() => (data ? data.classes.flatMap((c) => c.itens) : []), [data]);
  const segs = useMemo(() => (data ? segments(data.texto, allItems) : []), [data, allItems]);
  const goTo = (ref: string) => { const el = document.getElementById(`mark-${ref}`); if (el) { el.scrollIntoView({ block: "center", behavior: "smooth" }); el.classList.add("ring-4", "ring-teal-deep"); setTimeout(() => el.classList.remove("ring-4", "ring-teal-deep"), 1600); } };

  return (
    <Page wide>
      <AssistantBanner />
      <h1 className="mb-2 text-[1.5rem]">O documento e o que a assistente encontrou nele</h1>
      {!data && <p role="status" className="text-ink-2">{error ?? "Carregando o documento."}</p>}
      {data && (
        <>
          <p className="mb-3">Cada marcação mostra de onde veio uma informação usada na explicação. Marcações conferidas foram encontradas palavra por palavra no texto.</p>
          <div className="mb-4 flex flex-wrap gap-2">
            <StatusChip tone="ok">{data.conferidos} conferidas no texto</StatusChip>
            {data.total - data.conferidos > 0 && <StatusChip tone="pending">{data.total - data.conferidos} não localizadas</StatusChip>}
          </div>
          {data.sinteses.length > 0 && (
            <Card className="mb-4">
              <h2 className="mb-2 text-[1.15rem]">O que a assistente concluiu</h2>
              <div className="space-y-3">
                {data.sinteses.map((s, i) => (
                  <div key={i}>
                    <p className="font-bold">{s.rotulo}</p>
                    <p>{s.texto}</p>
                    {s.lastro.length > 0 && <p className="text-[0.9rem] text-ink-2">Baseado em {s.lastro.length} {s.lastro.length === 1 ? "marcação" : "marcações"}: {s.lastro.map((r) => <button key={r} type="button" onClick={() => goTo(r)} className="mr-2 underline underline-offset-2 text-teal-deep">{r}</button>)}</p>}
                  </div>
                ))}
              </div>
            </Card>
          )}
          <div className="grid gap-4 md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
            <Card>
              <h2 className="mb-2 text-[1.15rem]">Texto do documento com as marcações</h2>
              <div className="whitespace-pre-wrap font-mono text-[0.92rem] leading-relaxed">
                {segs.map((sg, i) => sg.item
                  ? <mark key={i} id={`mark-${sg.item.ref}`} style={{ backgroundColor: sg.item.cor }} className="rounded px-0.5 text-ink no-underline" title={`${sg.item.campo ?? ""}: ${sg.item.valor ?? ""}`}>{sg.text}</mark>
                  : <span key={i}>{sg.text}</span>)}
              </div>
            </Card>
            <div className="space-y-3">
              {data.classes.map((c) => (
                <Card key={c.classe}>
                  <h2 className="mb-2 flex items-center gap-2 text-[1.1rem]"><span aria-hidden className="inline-block h-4 w-4 rounded" style={{ backgroundColor: c.cor }} />{c.rotulo} <span className="text-[0.9rem] font-normal text-ink-2">({c.itens.length})</span></h2>
                  <ul className="space-y-2">
                    {c.itens.map((it) => (
                      <li key={it.ref} className="rounded-[10px] border border-line p-2.5 text-[0.95rem]">
                        <p><span className="font-bold">{(it.campo ?? "").replace(/_/g, " ")}</span>{it.valor ? `: ${it.valor}` : ""}</p>
                        <p className="mt-1 text-ink-2">“{it.trecho}”</p>
                        {it.conferido
                          ? <button type="button" onClick={() => goTo(it.ref)} className="mt-1 min-h-[44px] font-bold text-teal-deep underline underline-offset-2">Ver no texto</button>
                          : <p className="mt-1 text-[0.9rem] text-pend">Não localizado palavra por palavra no texto.</p>}
                      </li>
                    ))}
                  </ul>
                </Card>
              ))}
            </div>
          </div>
          <p className="mt-4"><Link href={`/t/${hash}`} className="font-bold text-teal-deep underline underline-offset-4">Voltar para a explicação</Link></p>
        </>
      )}
    </Page>
  );
}
