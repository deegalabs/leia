"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronRight, FilePlus2, MessageSquare, ListChecks } from "lucide-react";
import { clientLinkUrl, formatDateTime, listTasks, type TaskSummary } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, m } from "@/lib/i18n";
import { isSettled, statusInfo } from "@/lib/status";
import { AppHeader, Card, CopyButton, LinkButton, Page, StatusChip } from "./ui";
import { AuthNav, RequireAuth } from "./Session";

export function Panel() {
  return (
    <Page wide>
      <AppHeader right={<AuthNav />} />
      <RequireAuth next="/painel"><PanelBody /></RequireAuth>
    </Page>
  );
}

function PanelBody() {
  const { isCitizen } = useAuth();
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
      {!tasks && <p role="status" className="text-ink-2">{error ?? m.panel.loading}</p>}
      {tasks && tasks.length === 0 && <Card tone="soft"><p>{isCitizen ? m.panel.emptyCitizen : m.panel.emptyLawyer}</p></Card>}
      {tasks && tasks.length > 0 && (
        <ul className="grid gap-3">
          {tasks.map((t) => <li key={t.id}>{isCitizen ? <CitizenCard t={t} /> : <LawyerCard t={t} />}</li>)}
        </ul>
      )}
    </>
  );
}

function LawyerCard({ t }: { t: TaskSummary }) {
  const s = statusInfo(t.status, false);
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
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <LinkButton href={`/t/${t.hash}`} variant={approved ? "secondary" : "primary"}>{m.ch.continue}</LinkButton>
        {approved && <LinkButton href={`/comprovante/${approved.comprovante_token ?? approved.hash_imutavel}`}>{m.ch.viewReceipt}</LinkButton>}
        <Link href={`/painel/${t.id}`} className="inline-flex min-h-[48px] items-center gap-1 px-1 font-bold text-teal-deep underline underline-offset-4 sm:col-span-2">{m.panel.details} <ChevronRight size={18} aria-hidden /></Link>
      </div>
    </Card>
  );
}
