"use client";
import { useEffect, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, Circle, LoaderCircle } from "lucide-react";
import { getInferences, type Stage, type Task } from "@/lib/api";
import type { Inferences } from "@/lib/inferences";
import { fmt, m } from "@/lib/i18n";
import { AssistantBanner, Card, Page } from "./ui";
import { ClassCounts, MarkCounts, MarkedText } from "./InferenceMarks";

/* LeIA: visible preparation (docs/API-V3-CONTRACT.md, "Preparação visível e tarefas do fluxo externo").
   The wait screen while the pipeline runs: the 14 steps with state and time, a "n de 14" bar and, below, the document
   with the marks found so far. The task itself is polled by the journey; only the partial inferences are polled here. */

const POLL_MS = 8000;
const STEP_TOTAL = 14;

const icons: Record<Stage["estado"], { Icon: typeof Circle; cls: string }> = {
  pendente: { Icon: Circle, cls: "text-ink-3" },
  em_andamento: { Icon: LoaderCircle, cls: "animate-spin text-teal-deep" },
  concluida: { Icon: CheckCircle2, cls: "text-ok" },
  erro: { Icon: AlertCircle, cls: "text-danger" },
};

const seconds = (n: number) => fmt(m.journey.seconds, { n: Math.max(1, Math.round(n)) });

export function StageList({ etapas }: { etapas: Stage[] }) {
  const total = etapas.length || STEP_TOTAL;
  const done = etapas.filter((e) => e.estado === "concluida").length;
  return (
    <div>
      <p className="mb-1.5 font-bold" id="prep-progress-label">{fmt(m.journey.stepsProgress, { n: done, total })}</p>
      <div role="progressbar" aria-labelledby="prep-progress-label" aria-valuemin={0} aria-valuemax={total} aria-valuenow={done} className="h-2.5 w-full overflow-hidden rounded-full bg-line">
        <div className="h-full rounded-full bg-teal-deep transition-[width] duration-500" style={{ width: `${Math.round((done / total) * 100)}%` }} />
      </div>
      <ol aria-label={m.journey.stepsLabel} className="mt-3 space-y-1.5">
        {etapas.map((e) => {
          const { Icon, cls } = icons[e.estado] ?? icons.pendente;
          const current = e.estado === "em_andamento";
          return (
            <li key={e.id} className={`flex items-center gap-2.5 text-[1rem] ${e.estado === "pendente" ? "text-ink-2" : "text-ink"} ${current ? "font-bold" : ""}`} aria-current={current ? "step" : undefined}>
              <Icon size={20} aria-hidden className={`flex-none ${cls}`} />
              <span className="flex-1">{e.nome}<span className="sr-only">, {m.journey.stepState[e.estado] ?? e.estado}</span></span>
              {typeof e.tempo === "number" && e.estado === "concluida" && <span className="flex-none font-mono text-[0.9rem] text-ink-2">{seconds(e.tempo)}</span>}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/* "O que a assistente está lendo agora": polls the partial inferences; hidden on any error (409, 404, network). */
export function ReadingNow({ hash }: { hash: string }) {
  const [partial, setPartial] = useState<Inferences | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let alive = true; let timer: number | undefined;
    const tick = () => {
      getInferences(hash)
        .then((d) => { if (alive) { setPartial(d); setFailed(false); } })
        .catch(() => { if (alive) setFailed(true); })
        .finally(() => { if (alive) timer = window.setTimeout(tick, POLL_MS); });
    };
    tick();
    return () => { alive = false; if (timer !== undefined) clearTimeout(timer); };
  }, [hash]);
  const items = useMemo(() => (partial ? partial.classes.flatMap((c) => c.itens) : []), [partial]);
  if (failed || !partial) return null;
  const hasText = Boolean(partial.texto && partial.texto.trim());
  return (
    <Card className="mt-4">
      <h2 className="mb-2 text-[1.15rem]">{m.journey.readingTitle}</h2>
      {!hasText ? <p className="text-ink-2" role="status">{m.journey.readingNoText}</p> : (
        <>
          <p className="mb-3 text-[0.95rem] text-ink-2">{m.journey.readingIntro}</p>
          {partial.classes.length === 0 ? <p className="text-ink-2" role="status">{m.journey.readingNoMarks}</p> : (
            <div className="grid gap-2">
              <ClassCounts classes={partial.classes} />
              <MarkCounts data={partial} />
            </div>
          )}
          <details className="group mt-3">
            <summary className="flex min-h-[48px] cursor-pointer list-none items-center font-bold text-teal-deep [&::-webkit-details-marker]:hidden">
              <span className="group-open:hidden">{m.journey.readingToggle}</span><span className="hidden group-open:inline">{m.journey.readingToggleClose}</span>
            </summary>
            <div className="mt-2 max-h-[60vh] overflow-y-auto rounded-[12px] border border-line p-3">
              <MarkedText texto={partial.texto} items={items} idPrefix="prep-mark" />
            </div>
          </details>
        </>
      )}
    </Card>
  );
}

export function Preparing({ hash, task }: { hash: string; task: Task }) {
  const etapas = task.etapas ?? [];
  const last = task.eventos && task.eventos.length ? task.eventos[task.eventos.length - 1] : null;
  const lastLabel = last ? `${String(last.tipo ?? "").replace(/_/g, " ")}${last.id ? ` (${String(last.id)}${last.idx !== undefined && last.total ? `, ${Number(last.idx) + 1} de ${String(last.total)}` : ""})` : ""}` : "";
  return (
    <Page>
      <AssistantBanner />
      <Card>
        <h1 className="mb-2 text-[1.5rem]">{m.journey.preparingTitle}</h1>
        <p className={etapas.length ? "mb-4" : ""}>{m.journey.preparingText}</p>
        {etapas.length > 0
          ? <StageList etapas={etapas} />
          : last && <p className="mt-2 text-[0.95rem] text-ink-2" role="status">{fmt(m.journey.currentStep, { step: lastLabel })}</p>}
      </Card>
      <ReadingNow hash={hash} />
    </Page>
  );
}
