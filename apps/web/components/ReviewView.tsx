"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Check, CheckCircle2, ExternalLink } from "lucide-react";
import { approveTask, clientLinkUrl, formatDateTime, getReview, getTaskDetail, topicsOf, type Review, type Task } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, m } from "@/lib/i18n";
import { hasReview, needsReview, statusInfo } from "@/lib/status";
import { AppHeader, BottomActionBar, Button, Card, CopyButton, LinkButton, Page, StatusChip } from "./ui";
import { AuthNav, RequireAuth } from "./Session";
import { Paragraphs, cleanTitle } from "./Inline";
import { ClassCards, MarkCounts, MarkedText, scrollToMark } from "./InferenceMarks";

/* Lawyer review before release (docs/API-V3-CONTRACT.md, "Revisão do advogado antes de liberar"):
   what the workflow marked in the text, what it concluded, what the citizen will read and the questions,
   then "Aprovar e liberar para a cliente". Citizens never see this page. */

const TABS = ["marks", "text", "conclusions", "explanation", "questions"] as const;
type Tab = (typeof TABS)[number];
const MARK_PREFIX = "review-mark";

export function ReviewView({ id }: { id: string }) {
  return (
    <Page wide>
      <AppHeader right={<AuthNav />} />
      <RequireAuth next={`/painel/${id}/revisao`}><Body id={id} /></RequireAuth>
    </Page>
  );
}

function Body({ id }: { id: string }) {
  const { isCitizen, ready } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<Review | null>(null);
  const [releasedAt, setReleasedAt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [tab, setTab] = useState<Tab>("marks");
  const [pendingRef, setPendingRef] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [approveError, setApproveError] = useState<string | null>(null);

  useEffect(() => { if (ready && isCitizen) router.replace(`/painel/${id}`); }, [ready, isCitizen, router, id]);

  useEffect(() => {
    if (isCitizen) return;
    let alive = true;
    getReview(id).then((r) => { if (alive) { setData(r); setError(null); } })
      .catch((e: Error & { status?: number }) => {
        if (!alive) return;
        if (e.status === 409) { setError(m.panel.review.notReady); setTimeout(() => { if (alive) setTick((n) => n + 1); }, 4000); return; }
        setError(e.status === 404 || e.status === 403 ? m.panel.review.notFound : m.common.systemError);
      });
    /* the release date lives in the task events ("aprovada"); the review body has no dates */
    getTaskDetail(id).then((d) => {
      if (!alive) return;
      const ev = [...d.eventos].reverse().find((e) => e.tipo === "aprovada");
      setReleasedAt(ev?.ts ? String(ev.ts) : d.tarefa.status === "enviada" || d.tarefa.status === "assinada" ? d.tarefa.atualizada_em : null);
    }).catch(() => { /* the date is optional */ });
    return () => { alive = false; };
  }, [id, tick, isCitizen]);

  /* "Ver no texto" from another tab: switch to the text, then scroll once the marks are in the page */
  useEffect(() => {
    if (tab !== "text" || !pendingRef) return;
    const t = setTimeout(() => { scrollToMark(MARK_PREFIX, pendingRef); setPendingRef(null); }, 50);
    return () => clearTimeout(t);
  }, [tab, pendingRef]);
  const viewInText = (ref: string) => { setPendingRef(ref); setTab("text"); };

  const allItems = useMemo(() => (data ? data.inferencias.classes.flatMap((c) => c.itens) : []), [data]);
  const topics = useMemo(() => (data ? topicsOf({ tarefa: data.tarefa, resumo_md: data.resumo_md, topicos: null, questoes: [], ultima_tentativa: null } as Task) : []), [data]);

  async function approve() {
    if (!data || busy) return;
    setBusy(true); setApproveError(null);
    try {
      const r = await approveTask(id);
      setData({ ...data, tarefa: { ...data.tarefa, status: r.status || "enviada" } });
      setReleasedAt(new Date().toISOString());
    } catch (e) {
      const err = e as Error & { status?: number };
      setApproveError(err.status === 409 ? m.panel.review.alreadyReleased : m.panel.review.approveFailed);
      if (err.status === 409) setTick((n) => n + 1);
    } finally { setBusy(false); }
  }

  if (isCitizen) return <p role="status" className="text-ink-2">{m.common.loading}</p>;
  if (!data) return <p role="status" className="text-ink-2">{error ?? m.panel.review.loading}</p>;
  const s = statusInfo(data.tarefa.status, false, data.tarefa.origem);
  const link = clientLinkUrl(data.link_cliente || data.tarefa.hash);
  const pending = needsReview(data.tarefa.status, data.tarefa.origem);
  const released = data.tarefa.status === "enviada" || data.tarefa.status === "assinada" || (data.tarefa.status === "pronta" && data.tarefa.origem === "cidadao");
  const tabLabels: Record<Tab, string> = { marks: m.panel.review.tabs.marks, text: m.panel.review.tabs.text, conclusions: m.panel.review.tabs.conclusions, explanation: m.panel.review.tabs.explanation, questions: m.panel.review.tabs.questions };

  return (
    <>
      <Link href={`/painel/${id}`} className="mb-3 inline-flex min-h-[48px] items-center gap-1 font-bold text-teal-deep underline underline-offset-4"><ArrowLeft size={18} aria-hidden /> {m.panel.review.backToDocument}</Link>
      <div className="mb-1 flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-[0.95rem] text-ink-2">{m.panel.review.title}</p>
          <h1 className="text-[1.5rem]">{data.tarefa.titulo}</h1>
        </div>
        <StatusChip tone={s.tone}>{s.label}</StatusChip>
      </div>
      <p className="mb-4 text-[0.95rem] text-ink-2">{m.panel.review.intro}</p>
      {error && <p role="alert" className="mb-3 text-danger">{error}</p>}

      <div role="group" aria-label={m.panel.review.tabsLabel} className="mb-4 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button key={t} type="button" aria-pressed={tab === t} aria-controls={`review-panel-${t}`} onClick={() => setTab(t)}
            className={`min-h-[44px] rounded-button border-2 px-3.5 font-bold transition-colors ${tab === t ? "border-teal-deep bg-teal-deep text-white" : "border-line bg-surface text-ink hover:bg-teal-soft"}`}>
            {tabLabels[t]}
          </button>
        ))}
      </div>

      {tab === "marks" && (
        <div id="review-panel-marks" className="grid gap-3">
          <p>{m.panel.review.marksIntro}</p>
          <MarkCounts data={data.inferencias} />
          <ClassCards classes={data.inferencias.classes} onView={viewInText} withSeal />
        </div>
      )}
      {tab === "text" && (
        <div id="review-panel-text" className="grid gap-3">
          <MarkCounts data={data.inferencias} />
          <Card>
            <h2 className="mb-2 text-[1.15rem]">{m.panel.review.textTitle}</h2>
            <MarkedText texto={data.inferencias.texto} items={allItems} idPrefix={MARK_PREFIX} />
          </Card>
        </div>
      )}
      {tab === "conclusions" && (
        <Card className="scroll-mt-4">
          <h2 id="review-panel-conclusions" className="mb-2 text-[1.15rem]">{m.panel.review.conclusionsTitle}</h2>
          {data.inferencias.sinteses.length === 0 ? <p className="text-ink-2">{m.panel.review.noConclusions}</p> : (
            <div className="space-y-4">
              {data.inferencias.sinteses.map((sy, i) => (
                <div key={i}>
                  <p className="font-bold">{sy.rotulo}</p>
                  <p>{sy.texto}</p>
                  {sy.lastro.length > 0 && (
                    <p className="mt-1 flex flex-wrap items-center gap-1.5 text-[0.9rem] text-ink-2">
                      <span>{sy.lastro.length === 1 ? m.panel.review.basedOnOne : fmt(m.panel.review.basedOn, { n: sy.lastro.length })}</span>
                      {sy.lastro.map((r) => <button key={r} type="button" onClick={() => viewInText(r)} className="inline-flex min-h-[36px] items-center rounded-full bg-teal-soft px-2.5 font-mono text-[0.85rem] text-teal-deep underline underline-offset-2">{r}</button>)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
      {tab === "explanation" && (
        <div id="review-panel-explanation" className="grid gap-3">
          <Card tone="soft">
            <h2 className="mb-1 text-[1.15rem]">{m.panel.review.explanationTitle}</h2>
            <p className="text-[0.95rem] text-ink-2">{m.panel.review.explanationIntro}</p>
          </Card>
          {topics.map((t, i) => (
            <Card key={t.id}>
              <p className="mb-1 text-[0.9rem] text-ink-2">{fmt(m.common.topicOf, { n: i + 1, total: topics.length })}</p>
              <h2 className="mb-2 text-[1.2rem]">{cleanTitle(t.titulo)}</h2>
              <Paragraphs text={t.explicacao ?? t.explicacao_md ?? ""} />
            </Card>
          ))}
        </div>
      )}
      {tab === "questions" && (
        <div id="review-panel-questions" className="grid gap-3">
          <Card tone="soft">
            <h2 className="mb-1 text-[1.15rem]">{m.panel.review.questionsTitle}</h2>
            <p className="text-[0.95rem] text-ink-2">{m.panel.review.questionsIntro}</p>
          </Card>
          {data.questoes.map((q, i) => (
            <Card key={q.id}>
              <p className="mb-1 text-[0.9rem] text-ink-2">{i + 1} de {data.questoes.length}{q.area ? ` · ${q.area}` : ""}{q.dificuldade ? ` · ${q.dificuldade}` : ""}</p>
              <h2 className="mb-3 text-[1.15rem]">{q.enunciado}</h2>
              <ol className="grid gap-2">
                {q.alternativas.map((a, k) => {
                  const right = k === q.correta;
                  return (
                    <li key={k} className={`flex items-start gap-3 rounded-button border-2 px-3.5 py-2.5 ${right ? "border-ok bg-ok-soft" : "border-line bg-surface"}`}>
                      <span aria-hidden className={`grid h-[30px] w-[30px] flex-none place-items-center rounded-full border-2 text-[0.95rem] font-bold ${right ? "border-ok bg-ok text-white" : "border-ink"}`}>{"ABCD"[k] ?? k + 1}</span>
                      <span className="flex-1">{a}</span>
                      {right && <span className="inline-flex items-center gap-1 text-[0.9rem] font-bold text-ok"><Check size={18} aria-hidden /> {m.panel.review.correctAnswer}</span>}
                    </li>
                  );
                })}
              </ol>
              {q.justificativa && <p className="mt-3 text-[0.95rem]"><span className="font-bold">{m.panel.review.why}:</span> {q.justificativa}</p>}
            </Card>
          ))}
        </div>
      )}

      {hasReview(data.tarefa.status) && (
        <BottomActionBar>
          {pending && (
            <>
              {approveError && <p role="alert" className="text-danger">{approveError}</p>}
              <Button onClick={approve} disabled={busy}><CheckCircle2 size={20} aria-hidden /> {busy ? m.panel.review.approving : m.panel.review.approve}</Button>
              <p className="text-center text-[0.9rem] text-ink-2">{m.panel.review.approveHint}</p>
            </>
          )}
          {released && (
            <div className="rounded-card border border-line bg-surface p-4" role="status">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <StatusChip tone="ok"><CheckCircle2 size={18} aria-hidden /> {m.panel.review.released}</StatusChip>
                <span className="text-[0.95rem] text-ink-2">{data.tarefa.origem === "cidadao" ? m.panel.review.citizenOwned : releasedAt ? fmt(m.panel.review.releasedAt, { date: formatDateTime(releasedAt) }) : m.panel.review.releasedNoDate}</span>
              </div>
              <code className="block break-all font-mono text-[0.95rem]">{link}</code>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <CopyButton text={link} label={m.panel.copyClientLink} />
                <LinkButton href={`/t/${data.tarefa.hash}`} variant="ghost" className="!w-auto"><ExternalLink size={18} aria-hidden /> {m.panel.openAsClient}</LinkButton>
              </div>
            </div>
          )}
        </BottomActionBar>
      )}
    </>
  );
}
