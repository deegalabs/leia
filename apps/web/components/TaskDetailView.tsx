"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ClipboardCheck, ExternalLink, Send } from "lucide-react";
import { answerDoubt, clientLinkUrl, formatDateTime, getTaskDetail, issueInvite, retryTask, revokeInvite, type Doubt, type Invite, type TaskDetail } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, m } from "@/lib/i18n";
import { hasReview, isSettled, needsReview, statusInfo } from "@/lib/status";
import { Button, Card, CopyButton, LinkButton, StatusChip } from "./ui";
import { AuthNav, RequireAuth } from "./Session";
import { LawyerShell } from "./LawyerShell";
import { Inline } from "./Inline";
import { SkeletonCard } from "./Skeleton";

export function TaskDetailView({ id }: { id: string }) {
  return (
    <LawyerShell right={<AuthNav />}>
      <RequireAuth next={`/painel/${id}`}><Body id={id} /></RequireAuth>
    </LawyerShell>
  );
}

const eventNames: Record<string, string> = m.panel.detail.eventNames;
const eventLabel = (e: TaskDetail["eventos"][number]) => `${eventNames[String(e.tipo ?? "")] ?? String(e.tipo ?? "").replace(/_/g, " ")}${e.id ? ` (${String(e.id)}${e.idx !== undefined && e.total ? `, ${Number(e.idx) + 1} de ${String(e.total)}` : ""})` : ""}`;

function Body({ id }: { id: string }) {
  const { isCitizen } = useAuth();
  const [data, setData] = useState<TaskDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [refazendo, setRefazendo] = useState(false);

  async function refazer() {
    if (refazendo) return;
    setRefazendo(true); setError(null);
    try { await retryTask(id); setTick((n) => n + 1); }
    catch (e) { setError((e as Error).message || m.common.systemError); }
    finally { setRefazendo(false); }
  }

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

  if (!data) return error
    ? <p role="status" className="text-ink-2">{error}</p>
    : <SkeletonCard linhas={5} rotulo={m.common.loading} />;
  const s = statusInfo(data.tarefa.status, isCitizen, data.tarefa.origem);
  const link = clientLinkUrl(data.link_cliente || data.tarefa.hash);
  /* LeIA: review flow. The lawyer approves in /painel/{id}/revisao before the link opens the explanation. */
  const reviewPending = needsReview(data.tarefa.status, data.tarefa.origem);
  const last = data.eventos.length ? data.eventos[data.eventos.length - 1] : null;
  /* A recusa só vale enquanto ninguém se vinculou: quem negou pode ter tocado no botão errado e confirmado
     logo depois, e o aviso ficaria contradizendo a lista, que já mostra a cidadã vinculada. */
  const nomeNegado = data.cidadao === null && data.eventos.some((e) => e.tipo === "nome_negado");
  const approved = [...data.tentativas].reverse().find((a) => a.aprovado) ?? null;

  return (
    <>
      <Link href="/painel" className="mb-3 inline-flex min-h-[48px] items-center gap-1 font-bold text-teal-deep underline underline-offset-4"><ArrowLeft size={18} aria-hidden /> {m.panel.backToList}</Link>
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
        {/* Alguém abriu o link e disse que não é a pessoa do convite. Quem enviou é a única pessoa que pode
            consertar isso, e sem este aviso o documento fica parado sem nenhuma pista do motivo. Fica acima
            de tudo porque muda o que vale fazer com o documento inteiro. */}
        {!isCitizen && nomeNegado && (
          <Card tone="pending">
            <h2 className="text-[1.15rem]">{fmt(m.panel.detail.deniedTitle, { nome: data.convite?.nome ?? "" })}</h2>
            <p className="text-[0.95rem] text-ink-2">{m.panel.detail.deniedText}</p>
          </Card>
        )}
        {/* Documento que não chegou ao fim: sem isto ele morria na lista e a pessoa tinha que subir de novo,
            sem saber por quê. A causa comum é o serviço reiniciar no meio da preparação. */}
        {!isCitizen && data.tarefa.status === "falhou" && (
          <Card tone="pending">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-[1.15rem]">{m.panel.detail.retry}</h2>
                <p className="text-[0.95rem] text-ink-2">{m.panel.detail.retryHelp}</p>
              </div>
              <Button variant="primary" className="wide:!w-auto" disabled={refazendo}
                onClick={refazer}>{m.panel.detail.retry}</Button>
            </div>
          </Card>
        )}
        {!isCitizen && hasReview(data.tarefa.status) && (
          <Card tone={reviewPending ? "pending" : "soft"}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-[1.15rem]">{m.panel.review.title}</h2>
                <p className="text-[0.95rem] text-ink-2">{reviewPending ? m.panel.detail.clientLinkPending : m.panel.review.intro}</p>
              </div>
              <LinkButton href={`/painel/${id}/revisao`} variant={reviewPending ? "primary" : "secondary"} className="wide:!w-auto"><ClipboardCheck size={20} aria-hidden /> {reviewPending ? m.panel.reviewAndRelease : m.panel.viewReview}</LinkButton>
            </div>
          </Card>
        )}
        {!isCitizen && (
          <Card>
            <h2 className="mb-1 text-[1.15rem]">{m.panel.detail.clientLink}</h2>
            <p className="mb-2 text-[0.95rem] text-ink-2">{reviewPending ? m.panel.detail.clientLinkPending : m.panel.detail.clientLinkHint}</p>
            <code className="block break-all font-mono text-[0.95rem]">{link}</code>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <CopyButton text={link} label={m.panel.copyClientLink} />
              <LinkButton href={`/t/${data.tarefa.hash}`} variant="ghost" className="!w-auto"><ExternalLink size={18} aria-hidden /> {m.panel.openAsClient}</LinkButton>
            </div>
            <p className="mt-2"><LinkButton href={`/t/${data.tarefa.hash}/documento`} variant="ghost">Ver o documento com as marcações e o que a assistente concluiu</LinkButton></p>
            <InviteControl id={id} invite={data.convite ?? null} onChange={() => setTick((n) => n + 1)} />
          </Card>
        )}
        {isCitizen && (
          <div className="grid gap-2 wide:grid-cols-2">
            <LinkButton href={`/t/${data.tarefa.hash}`} variant={approved ? "secondary" : "primary"}>{m.ch.continue}</LinkButton>
            {approved && <LinkButton href={`/comprovante/${approved.comprovante_token ?? approved.hash_imutavel}`}>{m.ch.viewReceipt}</LinkButton>}
          </div>
        )}

        <Card>
          <h2 className="mb-1 text-[1.15rem]">{m.panel.detail.lastStep}</h2>
          {last ? <p>{eventLabel(last)}{last.ts ? <span className="text-ink-2"> · {formatDateTime(String(last.ts))}</span> : null}</p> : <p className="text-ink-2">Ainda sem etapas.</p>}
          {data.eventos.length > 1 && (
            <details className="mt-2">
              <summary className="min-h-[48px] cursor-pointer font-bold text-teal-deep">{m.panel.detail.events} ({data.eventos.length})</summary>
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
                    {a.aprovado && <Link href={`/comprovante/${a.comprovante_token ?? a.hash_imutavel}`} className="inline-flex min-h-[48px] items-center font-bold text-teal-deep underline underline-offset-4">{m.ch.viewReceipt}</Link>}
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
          <summary className="min-h-[48px] cursor-pointer font-bold text-teal-deep">{m.panel.detail.chatContext}</summary>
          <div className="mt-2 grid gap-1.5">
            {d.contexto.map((c, i) => <p key={i} className={`max-w-[92%] rounded-[12px] px-3 py-2 text-[0.95rem] ${c.role === "user" ? "justify-self-end bg-navy text-paper" : "justify-self-start bg-muted"}`}><Inline text={c.text} /></p>)}
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
          <Button type="submit" className="wide:!w-auto" disabled={busy || !text.trim()}><Send size={18} aria-hidden /> {busy ? m.common.loading : m.panel.detail.reply}</Button>
        </form>
      )}
    </li>
  );
}

/* LeIA: o link deixou de ser credencial de quem o tiver. Aqui quem enviou o documento decide até quando ele
   vale, para quem ele abre, e pode cancelá-lo (apps/llm-service/leia/invites.py). */
function InviteControl({ id, invite, onChange }: { id: string; invite: Invite | null; onChange: () => void }) {
  const [nome, setNome] = useState(invite?.nome ?? "");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const t = m.panel.detail;

  const revoked = Boolean(invite?.revogado_em);
  const estado = revoked ? t.inviteRevoked
    : invite?.email ? fmt(t.inviteAddressed, { email: invite.email })
    : invite?.nome ? `Para ${invite.nome}`
    : t.inviteAnyone;

  async function run(action: () => Promise<unknown>) {
    if (busy) return;
    setBusy(true); setError(null);
    try { await action(); setEmail(""); onChange(); }
    catch { setError(t.inviteFailed); }
    finally { setBusy(false); }
  }

  return (
    <div className="mt-4 border-t border-line pt-3">
      <h3 className="text-[1rem] font-bold">{t.inviteTitle}</h3>
      <p className="mt-1 text-[0.95rem] text-ink-2">{estado}</p>
      {invite && !revoked && invite.expira_em && (
        <p className="text-[0.9rem] text-ink-3">{fmt(t.inviteUntil, { data: formatDateTime(invite.expira_em) })}</p>
      )}
      {!invite && <p className="mt-1 text-[0.9rem] text-ink-3">{t.inviteOpenHint}</p>}
      {!revoked && (
        <div className="mt-2 grid gap-2">
          {/* O nome é obrigatório e vem primeiro; o e-mail é opcional e ficou abaixo. É o nome que a
              destinatária vê na tela para confirmar que é ela, e é ele que o comprovante vai afirmar. */}
          <label className="grid gap-1">
            <span className="text-[0.9rem] text-ink-2">{t.inviteName}</span>
            <input type="text" autoComplete="off" value={nome} required
              onChange={(e) => setNome(e.target.value)}
              className="min-h-[44px] rounded-button border-2 border-line-strong bg-surface px-3 text-[1rem]" />
            <span className="text-[0.85rem] text-ink-3">{t.inviteNameHint}</span>
          </label>
          <label className="grid gap-1">
            <span className="text-[0.9rem] text-ink-2">{t.inviteEmailLabel}</span>
            <input type="email" inputMode="email" autoComplete="off" value={email} placeholder={t.inviteEmailPlaceholder}
              onChange={(e) => setEmail(e.target.value)}
              className="min-h-[44px] rounded-button border-2 border-line-strong bg-surface px-3 text-[1rem]" />
          </label>
          <div className="flex flex-wrap items-end gap-2">
            <Button variant="secondary" className="!w-auto" disabled={busy || !nome.trim()}
              onClick={() => run(() => issueInvite(id, { nome: nome.trim(), ...(email.trim() ? { email: email.trim() } : {}) }))}>{t.inviteLimit}</Button>
            {invite && (
              <Button variant="ghost" className="!w-auto" disabled={busy}
                onClick={() => run(() => revokeInvite(id))}>{t.inviteCancel}</Button>
            )}
          </div>
        </div>
      )}
      {error && <p role="alert" className="mt-2 text-[0.95rem] text-danger">{error}</p>}
    </div>
  );
}
