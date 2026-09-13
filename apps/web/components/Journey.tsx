"use client";
import { useEffect, useMemo, useState } from "react";
import { MessageCircle } from "lucide-react";
import { getTask, submitQuiz, topicsOf, type QuizResult, type Task } from "@/lib/api";
import { AssistantBanner, BottomActionBar, Button, Card, LinkButton, Page, ProgressSteps, SpeakButton, StatusChip } from "./ui";
import { ChatSheet } from "./ChatSheet";
import { Inline, cleanTitle } from "./Inline";

type Step = { kind: "welcome" } | { kind: "topic"; n: number } | { kind: "question"; k: number } | { kind: "result" };

function Paragraphs({ text }: { text: string }) {
  const blocks = text.split(/\n\s*\n/).map((b) => b.trim()).filter(Boolean);
  return <>{blocks.map((b, i) => {
    const lines = b.split("\n");
    if (lines.length > 1 && lines.every((l) => /^\s*([-*]|\d+[.)])\s+/.test(l))) {
      return <ul key={i} className="mb-3 list-disc space-y-1 pl-5 last:mb-0">{lines.map((l, j) => <li key={j}><Inline text={l.replace(/^\s*([-*]|\d+[.)])\s+/, "")} /></li>)}</ul>;
    }
    return <p key={i} className="mb-3 last:mb-0"><Inline text={b.replace(/^[-*]\s+/gm, "")} /></p>;
  })}</>;
}

export function Journey({ hash }: { hash: string }) {
  const [task, setTask] = useState<Task | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<Step>({ kind: "welcome" });
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [result, setResult] = useState<QuizResult | null>(null);
  const [sending, setSending] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [retry, setRetry] = useState(0);
  const storageKey = `leia:${hash}`;

  useEffect(() => {
    let alive = true;
    getTask(hash).then((t) => {
      if (!alive) return;
      setTask(t); setError(null);
      if (t.ultima_tentativa?.aprovado) { setResult({ ...t.ultima_tentativa, erros: [] }); setStep({ kind: "result" }); return; }
      try {
        const saved = JSON.parse(localStorage.getItem(storageKey) || "null");
        if (saved?.result?.aprovado) { setResult(saved.result); setStep({ kind: "result" }); return; }
        if (saved?.answers) setAnswers(saved.answers);
      } catch { /* ignore */ }
    }).catch(() => {
      if (!alive) return;
      setError("Deu um problema do nosso lado, não foi você. Estamos tentando de novo.");
      setTimeout(() => setRetry((n) => n + 1), 4000);
    });
    return () => { alive = false; };
  }, [hash, storageKey, retry]);
  /* persist only after the task is loaded, so the first render does not overwrite what the load effect restores */
  useEffect(() => { if (!task) return; try { localStorage.setItem(storageKey, JSON.stringify({ answers, result })); } catch { /* ignore */ } }, [task, answers, result, storageKey]);
  useEffect(() => { window.scrollTo({ top: 0 }); }, [step]);

  const topics = useMemo(() => (task ? topicsOf(task) : []), [task]);
  const questions = task?.questoes ?? [];
  const ready = task && (task.tarefa.status === "concluida" || task.tarefa.status === "pronta" || questions.length > 0 || topics.length > 0);

  useEffect(() => { if (task && !ready) { const id = setTimeout(() => setRetry((n) => n + 1), 8000); return () => clearTimeout(id); } }, [task, ready]);

  async function send() {
    setSending(true);
    try { const r = await submitQuiz(hash, answers); setResult(r); setStep({ kind: "result" }); }
    catch { setError("Deu um problema do nosso lado, não foi você. Tente de novo em instantes."); }
    finally { setSending(false); }
  }

  if (!task) return <Page><AssistantBanner /><p role="status" className="text-ink-2">{error ?? "Carregando sua explicação."}</p></Page>;
  if (!ready) {
    const last = task.eventos && task.eventos.length ? task.eventos[task.eventos.length - 1] : null;
    return (
      <Page><AssistantBanner />
        <Card>
          <h1 className="mb-2 text-[1.5rem]">Estamos preparando a explicação do seu documento</h1>
          <p>Isso leva alguns minutos. Esta página atualiza sozinha. Você pode fechar e abrir o mesmo link depois.</p>
          {last && <p className="mt-2 text-[0.95rem] text-ink-2" role="status">Etapa atual: {String(last.tipo ?? "").replace(/_/g, " ")}{last.step ? ` (${String(last.step)})` : ""}</p>}
        </Card>
      </Page>
    );
  }

  /* floating "doubt" button only where the action bar has no such button */
  const fab = (step.kind === "question" || (step.kind === "result" && result?.aprovado)) && (
    <button type="button" onClick={() => setChatOpen(true)} className="no-print fixed bottom-24 right-4 z-10 inline-flex min-h-[52px] items-center gap-2 rounded-full bg-navy px-4 font-bold text-paper shadow-lg md:bottom-8">
      <MessageCircle size={20} aria-hidden /> Tenho uma dúvida
    </button>
  );

  return (
    <Page>
      <AssistantBanner />
      {step.kind === "welcome" && (
        <>
          <div className="flex items-start gap-3">
            <span aria-hidden className="grid h-11 w-11 flex-none place-items-center rounded-full bg-navy">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo-mark.svg" alt="" className="h-7 w-7" />
            </span>
            <div>
              <h1 className="mb-2 text-[1.5rem]">Olá. Vou explicar o documento &ldquo;{task.tarefa.titulo}&rdquo; com você.</h1>
              <p className="mb-2">Vamos ver os {topics.length} pontos principais, um de cada vez. Depois, algumas perguntas para eu conferir se expliquei bem. Sem tempo limite.</p>
            </div>
          </div>
          <Card tone="soft" className="mt-4">
            <h2 className="mb-2 text-[1.15rem]">Quem está falando com você</h2>
            <p id="intro">Sou uma assistente automática. Explico o que está escrito neste documento. Não sou advogada e não dou conselho jurídico. Suas respostas ficam só com você.</p>
            <SpeakButton text="Sou uma assistente automática. Explico o que está escrito neste documento. Não sou advogada e não dou conselho jurídico." label="Ouvir esta apresentação" />
          </Card>
          <Card className="mt-3">
            <h2 className="mb-2 text-[1.15rem]">Como funciona</h2>
            <ol className="list-decimal space-y-1 pl-5 text-[1rem]">
              <li>Eu explico cada parte e mostro o trecho original.</li>
              <li>Você pode perguntar. Eu respondo só com o que está no documento.</li>
              <li>No fim, você responde algumas perguntas e recebe um comprovante.</li>
            </ol>
          </Card>
          <p className="mt-3 text-[0.95rem] text-ink-2">Você não assina nada aqui.</p>
          <BottomActionBar>
            <Button onClick={() => setStep({ kind: "topic", n: 0 })}>Começar a explicação</Button>
          </BottomActionBar>
        </>
      )}

      {step.kind === "topic" && (() => {
        const t = topics[step.n]; const last = step.n === topics.length - 1;
        const text = t.explicacao ?? t.explicacao_md ?? "";
        return (
          <>
            <ProgressSteps total={topics.length} current={step.n} label={`Ponto ${step.n + 1} de ${topics.length}`} />
            <Card key={t.id}>
              <h1 className="mb-3 text-[1.4rem]" aria-label={`Ponto ${step.n + 1} de ${topics.length}: ${cleanTitle(t.titulo)}`}>{cleanTitle(t.titulo)}</h1>
              <Paragraphs text={text} />
              <SpeakButton text={`${t.titulo}. ${text}`} label="Ouvir explicação" />
              {t.trecho && (
                <details className="mt-3 group">
                  <summary className="flex min-h-[48px] cursor-pointer list-none items-center font-bold text-teal-deep [&::-webkit-details-marker]:hidden">
                    <span className="group-open:hidden">Ver trecho original</span><span className="hidden group-open:inline">Fechar trecho original</span>
                  </summary>
                  <blockquote cite={t.clausula ? `Cláusula ${t.clausula}` : undefined} className="mt-2 rounded-[12px] border-l-4 border-teal-deep bg-teal-soft px-3.5 py-3 font-mono text-[0.95rem]">
                    {t.clausula && <small className="mb-1 block text-ink-2">Cláusula {t.clausula}</small>}
                    <mark aria-label="trecho destacado">&ldquo;{t.trecho}&rdquo;</mark>
                  </blockquote>
                  <p className="mt-1 text-[0.9rem] text-ok">Trecho conferido: copiado exatamente do seu documento.</p>
                </details>
              )}
            </Card>
            <BottomActionBar>
              <Button onClick={() => (last ? (questions.length ? setStep({ kind: "question", k: 0 }) : setStep({ kind: "welcome" })) : setStep({ kind: "topic", n: step.n + 1 }))}>
                {last ? (questions.length ? "Entendi, vamos conferir" : "Entendi") : "Entendi, próximo"}
              </Button>
              <div className="grid grid-cols-2 gap-2">
                <Button variant="secondary" onClick={() => (step.n === 0 ? setStep({ kind: "welcome" }) : setStep({ kind: "topic", n: step.n - 1 }))}>Voltar</Button>
                <Button variant="secondary" onClick={() => setChatOpen(true)}>Tenho uma dúvida</Button>
              </div>
            </BottomActionBar>
          </>
        );
      })()}

      {step.kind === "question" && (() => {
        const q = questions[step.k]; const last = step.k === questions.length - 1; const chosen = answers[String(q.id)];
        return (
          <>
            <ProgressSteps total={questions.length} current={step.k} label={`Conferindo ${step.k + 1} de ${questions.length}`} />
            <Card>
              <p className="mb-1 text-[1.05rem] text-ink-2">Para eu ter certeza de que expliquei bem:</p>
              <h1 className="mb-3 text-[1.35rem]">{q.enunciado}</h1>
              <div role="radiogroup" aria-label={q.enunciado} className="grid gap-2.5">
                {q.alternativas.map((a, i) => (
                  <button key={i} type="button" role="radio" aria-checked={chosen === i} onClick={() => setAnswers({ ...answers, [String(q.id)]: i })}
                    className={`flex min-h-[56px] w-full items-center gap-3 rounded-button border-2 px-3.5 py-3 text-left text-[1.05rem] ${chosen === i ? "border-teal-deep bg-[#F1F8F8]" : "border-line bg-surface"}`}>
                    <span aria-hidden className={`grid h-[34px] w-[34px] flex-none place-items-center rounded-full border-2 font-bold ${chosen === i ? "border-teal-deep bg-teal-deep text-white" : "border-ink"}`}>{"ABCD"[i] ?? i + 1}</span>
                    <span>{a}</span>
                  </button>
                ))}
              </div>
              <SpeakButton text={`${q.enunciado}. ${q.alternativas.map((a, i) => `${"ABCD"[i]}: ${a}`).join(". ")}`} label="Ouvir a pergunta" />
              {error && <p role="alert" className="mt-2 text-[#8A1C1C]">{error}</p>}
            </Card>
            <BottomActionBar>
              <Button disabled={chosen === undefined || sending} onClick={() => (last ? send() : setStep({ kind: "question", k: step.k + 1 }))}>
                {sending ? "Conferindo suas respostas" : last ? "Enviar minhas respostas" : "Próxima pergunta"}
              </Button>
              <Button variant="secondary" onClick={() => (step.k === 0 ? setStep({ kind: "topic", n: topics.length - 1 }) : setStep({ kind: "question", k: step.k - 1 }))}>
                {step.k === 0 ? "Rever a explicação" : "Voltar"}
              </Button>
            </BottomActionBar>
          </>
        );
      })()}

      {step.kind === "result" && result && (
        result.aprovado ? (
          <>
            <StatusChip tone="ok">Entendimento registrado</StatusChip>
            <h1 className="mb-2 mt-3 text-[1.5rem]">Você entendeu o documento.</h1>
            <p>Seu comprovante está pronto. Ele mostra que você leu a explicação e respondeu às perguntas hoje. Ele não é a assinatura do contrato.</p>
            <Card className="mt-4">
              <h2 className="mb-2 text-[1.15rem]">O que você viu</h2>
              <ul className="space-y-1">{topics.map((t) => <li key={t.id} className="flex gap-2"><span aria-hidden className="text-ok">✓</span>{cleanTitle(t.titulo)}</li>)}</ul>
            </Card>
            <BottomActionBar>
              <LinkButton href={`/comprovante/${result.comprovante_token ?? result.hash_imutavel}`}>Ver meu comprovante</LinkButton>
              <Button variant="secondary" onClick={() => { setResult(null); setStep({ kind: "topic", n: 0 }); }}>Rever a explicação</Button>
            </BottomActionBar>
          </>
        ) : (
          <>
            <StatusChip tone="pending">Vamos ver de novo</StatusChip>
            <h1 className="mb-2 mt-3 text-[1.5rem]">Alguns pontos merecem outra explicação.</h1>
            <p>Isso é normal. Vou explicar de novo e depois você responde outra vez, sem pressa.</p>
            {result.erros.length > 0 && (
              <Card className="mt-4">
                <h2 className="mb-2 text-[1.15rem]">O que vale ver de novo</h2>
                <ul className="list-disc space-y-1 pl-5">{result.erros.map((e) => <li key={e.id}>{e.enunciado ?? `Pergunta ${e.id}`}</li>)}</ul>
              </Card>
            )}
            <BottomActionBar>
              <Button onClick={() => { setAnswers({}); setResult(null); setStep({ kind: "topic", n: 0 }); }}>Ler a explicação de novo</Button>
              <Button variant="secondary" onClick={() => setChatOpen(true)}>Tenho uma dúvida</Button>
            </BottomActionBar>
          </>
        )
      )}

      {fab}
      <ChatSheet hash={hash} open={chatOpen} onClose={() => setChatOpen(false)} />
    </Page>
  );
}
