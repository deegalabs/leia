"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronRight, ClipboardCheck, FilePlus2, MessageSquare, ListChecks } from "lucide-react";
import { clientLinkUrl, formatDateTime, listTasks, type TaskSummary } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, m } from "@/lib/i18n";
import { isSettled, needsReview, statusInfo } from "@/lib/status";
import { Card, CopyButton, LinkButton, StatusChip } from "./ui";
import { LawyerShell } from "./LawyerShell";
import { useWide } from "@/lib/wide";
import { AuthNav, RequireAuth } from "./Session";
import { SkeletonCard } from "./Skeleton";

export function Panel() {
  return (
    <LawyerShell right={<AuthNav />}>
      <RequireAuth next="/painel"><PanelBody /></RequireAuth>
    </LawyerShell>
  );
}

function PanelBody() {
  const { isCitizen } = useAuth();
  const larga = useWide();
  const [tasks, setTasks] = useState<TaskSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    listTasks().then((t) => { if (alive) { setTasks(t); setError(null); } }).catch(() => { if (alive) setError(m.common.systemError); });
    return () => { alive = false; };
  }, [tick]);
  /* keep refreshing while some document is still being prepared */
  useEffect(() => {
    if (!tasks || tasks.every((t) => isSettled(t.status))) return;
    const id = setTimeout(() => setTick((n) => n + 1), 4000);
    return () => clearTimeout(id);
  }, [tasks]);

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-[1.5rem]">{isCitizen ? m.panel.citizenTitle : m.panel.lawyerTitle}</h1>
        <LinkButton href="/enviar" className="!w-auto"><FilePlus2 size={20} aria-hidden /> {isCitizen ? m.panel.sendMyDocument : m.panel.sendDocument}</LinkButton>
      </div>
      {!tasks && (error
        ? <p role="status" className="text-ink-2">{error}</p>
        : <div className="grid gap-3"><SkeletonCard linhas={2} rotulo={m.panel.loading} /><SkeletonCard linhas={2} rotulo="" /></div>)}
      {tasks && tasks.length === 0 && <Card tone="soft"><p>{isCitizen ? m.panel.emptyCitizen : m.panel.emptyLawyer}</p></Card>}
      {/* Cartão no celular, colunas no computador, e nunca os dois ao mesmo tempo escondidos por CSS.
          O advogado percorre a lista todo dia, e comparar dez documentos empilhados em cartão custa rolar;
          em colunas, ele lê na vertical. A cidadã tem um documento, às vezes dois, e para ela o cartão diz
          mais. Por isso a cidadã fica no cartão mesmo no computador. */}
      {tasks && tasks.length > 0 && (larga && !isCitizen
        ? <LawyerTable tasks={tasks} />
        : (
          <ul className="grid gap-3">
            {tasks.map((t) => <li key={t.id}>{isCitizen ? <CitizenCard t={t} /> : <LawyerCard t={t} />}</li>)}
          </ul>
        ))}
    </>
  );
}

function LawyerCard({ t }: { t: TaskSummary }) {
  const s = statusInfo(t.status, false, t.origem);
  const a = t.ultima_tentativa;
  const answers = a ? fmt(m.panel.detail.attemptLine, { n: a.numero ?? 1, acertos: a.acertos, total: a.total }) : m.panel.detail.noAttempts;
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h2 className="text-[1.15rem]">{t.titulo}</h2>
        <StatusChip tone={s.tone}>{s.label}</StatusChip>
      </div>
      <p className="mt-1 text-[0.95rem] text-ink-2">{formatDateTime(t.criada_em)}{t.cidadao ? ` · ${m.panel.detail.citizen}: ${t.cidadao.nome}` : ""}</p>
      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-[1rem]">
        <li className="inline-flex items-center gap-1.5"><ListChecks size={18} aria-hidden className="text-teal-deep" /> {answers}</li>
        <li className="inline-flex items-center gap-1.5"><MessageSquare size={18} aria-hidden className="text-teal-deep" /> {t.duvidas_abertas === 1 ? m.panel.openDoubtsOne : t.duvidas_abertas > 0 ? fmt(m.panel.openDoubts, { n: t.duvidas_abertas }) : m.panel.noDoubts}</li>
      </ul>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {/* LeIA: review flow. "Revisar" while the lawyer still has to release the link. */}
        {needsReview(t.status, t.origem) && <Link href={`/painel/${t.id}/revisao`} className="inline-flex min-h-[48px] items-center gap-1.5 rounded-button bg-teal-deep px-3.5 font-bold text-white hover:bg-[#195C5C]"><ClipboardCheck size={18} aria-hidden /> {m.panel.reviewShort}</Link>}
        <CopyButton text={clientLinkUrl(t.link_cliente || t.hash)} label={m.panel.copyClientLink} />
        <Link href={`/painel/${t.id}`} className="inline-flex min-h-[48px] items-center gap-1 rounded-button px-2 font-bold text-teal-deep underline underline-offset-4 hover:bg-teal-soft">{m.panel.details} <ChevronRight size={18} aria-hidden /></Link>
      </div>
    </Card>
  );
}

function CitizenCard({ t }: { t: TaskSummary }) {
  const s = statusInfo(t.status, true);
  const approved = t.ultima_tentativa?.aprovado ? t.ultima_tentativa : null;
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h2 className="text-[1.15rem]">{t.titulo}</h2>
        <StatusChip tone={s.tone}>{s.label}</StatusChip>
      </div>
      <p className="mt-1 text-[0.95rem] text-ink-2">{t.advogado ? fmt(m.ch.sentBy, { lawyer: t.advogado.nome, date: formatDateTime(t.criada_em) }) : formatDateTime(t.criada_em)}</p>
      <div className="mt-3 grid gap-2 wide:grid-cols-2">
        <LinkButton href={`/t/${t.hash}`} variant={approved ? "secondary" : "primary"}>{m.ch.continue}</LinkButton>
        {approved && <LinkButton href={`/comprovante/${approved.comprovante_token ?? approved.hash_imutavel}`}>{m.ch.viewReceipt}</LinkButton>}
        <Link href={`/painel/${t.id}`} className="inline-flex min-h-[48px] items-center gap-1 px-1 font-bold text-teal-deep underline underline-offset-4 wide:col-span-2">{m.panel.details} <ChevronRight size={18} aria-hidden /></Link>
      </div>
    </Card>
  );
}

/* A lista do advogado em colunas. Tabela de verdade, e não uma grade de `div`: são dados tabulares, e o
   leitor de tela anuncia linha e coluna, o que transforma "o terceiro campo desta linha" em "Estado:
   aguardando revisão". A versão de celular continua sendo o cartão, sem tabela e sem rolagem lateral. */
function LawyerTable({ tasks }: { tasks: TaskSummary[] }) {
  return (
    <table className="w-full border-collapse text-left text-[0.95rem]">
      <caption className="sr-only">{m.panel.lawyerTitle}</caption>
      <thead>
        <tr className="border-b-2 border-line text-[0.85rem] uppercase tracking-wide text-ink-2">
          <th scope="col" className="py-2 pr-3 font-bold">Documento</th>
          <th scope="col" className="py-2 pr-3 font-bold">Estado</th>
          <th scope="col" className="py-2 pr-3 font-bold">Conferência</th>
          <th scope="col" className="py-2 pr-3 font-bold">Dúvidas</th>
          <th scope="col" className="py-2 font-bold"><span className="sr-only">Ações</span></th>
        </tr>
      </thead>
      <tbody>
        {tasks.map((t) => {
          const s = statusInfo(t.status, false, t.origem);
          const a = t.ultima_tentativa;
          return (
            <tr key={t.id} className="border-b border-line align-top">
              <th scope="row" className="py-3 pr-3 font-bold">
                {t.titulo}
                <span className="block font-normal text-[0.9rem] text-ink-2">
                  {formatDateTime(t.criada_em)}{t.cidadao ? ` · ${t.cidadao.nome}` : ""}
                </span>
              </th>
              <td className="py-3 pr-3"><StatusChip tone={s.tone}>{s.label}</StatusChip></td>
              <td className="py-3 pr-3 tabular-nums">
                {a ? fmt(m.panel.detail.attemptLine, { n: a.numero ?? 1, acertos: a.acertos, total: a.total })
                   : m.panel.detail.noAttempts}
              </td>
              <td className="py-3 pr-3 tabular-nums">
                {t.duvidas_abertas === 1 ? m.panel.openDoubtsOne
                  : t.duvidas_abertas > 0 ? fmt(m.panel.openDoubts, { n: t.duvidas_abertas })
                  : m.panel.noDoubts}
              </td>
              <td className="py-3">
                <Link href={needsReview(t.status, t.origem) ? `/painel/${t.id}/revisao` : `/painel/${t.id}`}
                      className="inline-flex min-h-[44px] items-center gap-1 font-bold text-teal-deep underline underline-offset-4">
                  {needsReview(t.status, t.origem) ? m.panel.reviewShort : m.panel.details}
                  <ChevronRight size={18} aria-hidden />
                </Link>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
