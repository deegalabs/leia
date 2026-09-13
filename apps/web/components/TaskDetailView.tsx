"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ExternalLink, Send } from "lucide-react";
import { answerDoubt, clientLinkUrl, formatDateTime, getTaskDetail, type Doubt, type TaskDetail } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, m } from "@/lib/i18n";
import { isSettled, statusInfo } from "@/lib/status";
import { AppHeader, Button, Card, CopyButton, LinkButton, Page, StatusChip } from "./ui";
import { AuthNav, RequireAuth } from "./Session";
import { Inline } from "./Inline";

export function TaskDetailView({ id }: { id: string }) {
  return (
    <Page wide>
      <AppHeader right={<AuthNav />} />
      <RequireAuth next={`/painel/${id}`}><Body id={id} /></RequireAuth>
    </Page>
  );
}

const eventNames: Record<string, string> = m.panel.detail.eventNames;
const eventLabel = (e: TaskDetail["eventos"][number]) => `${eventNames[String(e.tipo ?? "")] ?? String(e.tipo ?? "").replace(/_/g, " ")}${e.id ? ` (${String(e.id)}${e.idx !== undefined && e.total ? `, ${Number(e.idx) + 1} de ${String(e.total)}` : ""})` : ""}`;

function Body({ id }: { id: string }) {
  const { isCitizen } = useAuth();
  const [data, setData] = useState<TaskDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    getTaskDetail(id).then((d) => { if (alive) { setData(d); setError(null); } })
      .catch((e: Error & { status?: number }) => { if (alive) setError(e.status === 404 || e.status === 403 ? "Documento não encontrado." : m.common.systemError); });
    return () => { alive = false; };
  }, [id, tick]);
  useEffect(() => {
    if (!data || isSettled(data.tarefa.status)) return;
    const t = setTimeout(() => setTick((n) => n + 1), 4000);
    return () => clearTimeout(t);
  }, [data]);

  if (!data) return <p role="status" className="text-ink-2">{error ?? m.common.loading}</p>;
  const s = statusInfo(data.tarefa.status, isCitizen);
  const link = clientLinkUrl(data.link_cliente || data.tarefa.hash);
  const last = data.eventos.length ? data.eventos[data.eventos.length - 1] : null;
  const approved = [...data.tentativas].reverse().find((a) => a.aprovado) ?? null;

  return (
    <>
      <Link href="/painel" className="mb-3 inline-flex min-h-[44px] items-center gap-1 font-bold text-teal-deep underline underline-offset-4"><ArrowLeft size={18} aria-hidden /> {m.panel.backToList}</Link>
      <div className="mb-1 flex flex-wrap items-start justify-between gap-2">
        <h1 className="text-[1.5rem]">{data.tarefa.titulo}</h1>
        <StatusChip tone={s.tone}>{s.label}</StatusChip>
      </div>
      <p className="mb-4 text-[0.95rem] text-ink-2">
        {formatDateTime(data.tarefa.criada_em)} · {m.panel.detail.origin} {data.tarefa.origem === "advogado" ? m.panel.detail.originLawyer : m.panel.detail.originCitizen}
        {data.cidadao ? ` · ${m.panel.detail.citizen}: ${data.cidadao.nome}` : ""}{data.advogado ? ` · ${m.panel.detail.lawyer}: ${data.advogado.nome}` : ""}
      </p>
      {error && <p role="alert" className="mb-3 text-danger">{error}</p>}

      <div className="grid gap-3">
        {!isCitizen && (
          <Card>
            <h2 className="mb-1 text-[1.15rem]">{m.panel.detail.clientLink}</h2>
            <p className="mb-2 text-[0.95rem] text-ink-2">{m.panel.detail.clientLinkHint}</p>
            <code className="block break-all font-mono text-[0.95rem]">{link}</code>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <CopyButton text={link} label={m.panel.copyClientLink} />
              <LinkButton href={`/t/${data.tarefa.hash}`} variant="ghost" className="!w-auto"><ExternalLink size={18} aria-hidden /> {m.panel.openAsClient}</LinkButton>
            </div>
            <p className="mt-2"><LinkButton href={`/t/${data.tarefa.hash}/documento`} variant="ghost">Ver o documento com as marcações e o que a assistente concluiu</LinkButton></p>
          </Card>
        )}
        {isCitizen && (
          <div className="grid gap-2 sm:grid-cols-2">
            <LinkButton href={`/t/${data.tarefa.hash}`} variant={approved ? "secondary" : "primary"}>{m.ch.continue}</LinkButton>
            {approved && <LinkButton href={`/comprovante/${approved.comprovante_token ?? approved.hash_imutavel}`}>{m.ch.viewReceipt}</LinkButton>}
          </div>
        )}

        <Card>
          <h2 className="mb-1 text-[1.15rem]">{m.panel.detail.lastStep}</h2>
          {last ? <p>{eventLabel(last)}{last.ts ? <span className="text-ink-2"> · {formatDateTime(String(last.ts))}</span> : null}</p> : <p className="text-ink-2">Ainda sem etapas.</p>}
          {data.eventos.length > 1 && (
            <details className="mt-2">
              <summary className="min-h-[44px] cursor-pointer font-bold text-teal-deep">{m.panel.detail.events} ({data.eventos.length})</summary>
              <ol className="mt-2 space-y-1 text-[0.95rem]">{data.eventos.map((e, i) => <li key={i}>{eventLabel(e)}{e.ts ? <span className="text-ink-2"> · {formatDateTime(String(e.ts))}</span> : null}</li>)}</ol>
            </details>
          )}
        </Card>

        <Card>
          <h2 className="mb-2 text-[1.15rem]">{isCitizen ? m.panel.detail.attemptsCitizen : m.panel.detail.attempts}</h2>
          {data.tentativas.length === 0 ? <p className="text-ink-2">{m.panel.detail.noAttempts}</p> : (
            <ul className="grid gap-2">
              {data.tentativas.map((a) => (
                <li key={a.numero} className="flex flex-wrap items-center justify-between gap-2 rounded-[12px] bg-muted px-3.5 py-2.5">
                  <span>{fmt(m.panel.detail.attemptLine, { n: a.numero, acertos: a.acertos, total: a.total })} <span className="text-ink-2">· {formatDateTime(a.criada_em)}</span></span>
                  <span className="flex items-center gap-2">
                    <StatusChip tone={a.aprovado ? "ok" : "pending"}>{a.aprovado ? m.status.understood : m.c4.seeAgainTitle}</StatusChip>
                    {a.aprovado && <Link href={`/comprovante/${a.comprovante_token ?? a.hash_imutavel}`} className="inline-flex min-h-[44px] items-center font-bold text-teal-deep underline underline-offset-4">{m.ch.viewReceipt}</Link>}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <h2 className="mb-2 text-[1.15rem]">{isCitizen ? m.panel.detail.doubtsCitizen : m.panel.detail.doubts}</h2>
          {data.duvidas.length === 0 ? <p className="text-ink-2">{m.panel.detail.noDoubts}</p> : (
            <ul className="grid gap-3">
              {data.duvidas.map((d) => <DoubtItem key={d.id} taskId={id} d={d} canReply={!isCitizen} onReplied={() => setTick((n) => n + 1)} />)}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}

function DoubtItem({ taskId, d, canReply, onReplied }: { taskId: string; d: Doubt; canReply: boolean; onReplied: () => void }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  async function reply() {
    if (!text.trim() || busy) return;
    setBusy(true); setErr(null);
    try { await answerDoubt(taskId, d.id, text.trim()); setText(""); onReplied(); }
    catch { setErr(m.common.systemError); }
    finally { setBusy(false); }
  }
  return (
    <li className="rounded-[12px] border border-line p-3.5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="font-bold">{d.texto}</p>
        <StatusChip tone={d.respondida ? "ok" : "pending"}>{d.respondida ? m.panel.detail.replied : m.panel.detail.awaitingReply}</StatusChip>
      </div>
      <p className="mt-1 text-[0.9rem] text-ink-2">{formatDateTime(d.criada_em)}</p>
      {d.contexto.length > 0 && (
        <details className="mt-2">
          <summary className="min-h-[44px] cursor-pointer font-bold text-teal-deep">{m.panel.detail.chatContext}</summary>
          <div className="mt-2 grid gap-1.5">
            {d.contexto.map((c, i) => <p key={i} className={`max-w-[92%] rounded-[12px] px-3 py-2 text-[0.95rem] ${c.role === "user" ? "self-end bg-navy text-paper" : "self-start bg-muted"}`}><Inline text={c.text} /></p>)}
          </div>
        </details>
      )}
      {d.respondida && d.resposta && (
        <div className="mt-3 rounded-[12px] bg-teal-soft px-3.5 py-3">
          <p className="mb-1 text-[0.9rem] text-ink-2">{m.panel.detail.lawyer}{d.respondida_em ? ` · ${formatDateTime(d.respondida_em)}` : ""}</p>
          <p className="whitespace-pre-wrap">{d.resposta}</p>
        </div>
      )}
      {canReply && !d.respondida && (
        <form className="mt-3 grid gap-2" onSubmit={(e) => { e.preventDefault(); reply(); }}>
          <label htmlFor={`resposta-${d.id}`} className="sr-only">{m.panel.detail.reply}</label>
          <textarea id={`resposta-${d.id}`} value={text} onChange={(e) => setText(e.target.value)} rows={3} placeholder={m.panel.detail.replyPlaceholder}
            className="w-full rounded-button border-2 border-line bg-surface px-3 py-2 text-[1.05rem] focus:border-teal-deep" />
          {err && <p role="alert" className="text-danger">{err}</p>}
          <Button type="submit" className="sm:!w-auto" disabled={busy || !text.trim()}><Send size={18} aria-hidden /> {busy ? m.common.loading : m.panel.detail.reply}</Button>
        </form>
      )}
    </li>
  );
}
