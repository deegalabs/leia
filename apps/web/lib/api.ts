/* Client for the cognitive service, reached through this app and never directly.
   Every call is same origin, so the session cookie travels on its own and the browser never holds a token.
   The route handlers in app/api/* either forward to the service (SERVICE_URL) or answer from the in-app mock,
   which is what the hosted demo uses. */

import { busca } from "./progress";

/* LeIA: score (0..1 or 0..100) only on topics from the external "Resumo estruturado" flow */
/* `pos` é onde o trecho está no texto extraído, e é o que permite dizer em que página do documento ele
   fica. Ele existe desde que o trecho publicado passou a ser a fatia do documento naquela posição. */
export type Topic = { id: number; titulo: string; explicacao?: string; explicacao_md?: string; trecho?: string; pos?: [number, number] | null; pagina?: string | null; clausula?: string; score?: number; conferencia?: import("./inferences").Anchor };
/* LeIA: the species the engine read the document as. It comes first in the pipeline and it is what chooses
   the vocabulary every later step uses to name the parties, so it travels with every task: `conferido` says
   whether `trecho` was found in the document, `revisado_por_advogado` that a person answered instead of the
   model, and `aplicado` whether the explanation on screen was actually produced with it. */
export type DocumentType = { tipo: string; rotulo: string; trecho: string; pos: [number, number] | null;
                             conferido: boolean; revisado_por_advogado: boolean; aplicado?: boolean };
export type DocumentTypeOption = { tipo: string; rotulo: string };
/* LeIA: one of the 15 workflow steps as the public route reports it (docs/API-V3-CONTRACT.md, "Preparação visível") */
export type StageState = "pendente" | "em_andamento" | "concluida" | "erro";
export type Stage = { id: string; nome: string; estado: StageState; tempo?: number | null };
/* LeIA: a pergunta nasce presa a um ponto do documento (E12). `secao` é o título exato da seção da
   explicação de onde ela veio e `trecho` é a fatia literal do documento que sustenta a resposta: são
   os dois que o "não lembro, mostra de novo" abre. O gabarito nunca viaja junto. */
export type Question = { id: number; enunciado: string; alternativas: string[]; area?: string;
                         secao?: string | null; trecho?: string | null;
                         conferencia?: import("./inferences").Anchor | null };
export type Attempt = { aprovado: boolean; hash_imutavel: string; acertos: number; total: number; numero?: number };
export type Task = {
  tarefa: { hash: string; titulo: string; status: string };
  resumo_md: string;
  topicos: Topic[] | null;
  questoes: Question[];
  ultima_tentativa: (Attempt & { comprovante_token?: string }) | null;
  eventos?: { tipo?: string; id?: string; idx?: number; total?: number; ts?: string; [k: string]: unknown }[];
  /* LeIA: v3 (docs/API-V3-CONTRACT.md) */
  advogado?: { nome: string; oab?: string | null } | null;
  tem_advogado?: boolean;
  cidadao_vinculado?: boolean;
  duvidas_enviadas?: number;
  /* LeIA: o convite que governa este link, sem revelar o endereço da destinatária */
  convite?: { nome: string | null; enderecado: boolean; para: string | null; expira_em: string | null } | null;
  /* LeIA: visible preparation (docs/API-V3-CONTRACT.md, "Preparação visível e tarefas do fluxo externo") */
  etapas?: Stage[];
  tipo_documento?: DocumentType | null;
  sem_perguntas?: boolean;
};
export type QuizResult = Attempt & { comprovante_token?: string; erros: { id: number; area?: string; enunciado?: string; escolhida?: number | null }[] };
export type VerifyResult = {
  /* leia.payload.v3 as the service builds it: the document appears only as hashes, never as a token that could
     be handed around, and the ruler (instrument, passMark, reviewedByLawyer) travels with it so a third party
     can weigh the receipt instead of accepting it blind. */
  payload: { schema: string; documentRef: string; attemptRound: number; attemptSha256: string;
             documentSha256: string; summarySha256: string; understood: boolean;
             instrument: string; passMark: number; answered: number; consulted: number;
             reviewedByLawyer: boolean; createdAt: string };
  canonical: string;
  payloadHash: string;
  otsPresent: boolean;
  /* The stamp as the service knows it (ADR-0010). Optional because the in-app mock, which answers when no
     service is configured, still reports otsPresent alone; read them through stampView, never one by one. */
  otsState?: import("./stamp").StampState;
  otsBlockHeight?: number | null;
  otsLastAttempt?: string | null;
};

/* The service explains its refusals in the "detail" field. Carrying that text through means the screen can
   say "this link was cancelled" instead of a generic error it then retries forever. */
async function check(r: Response) {
  if (r.ok) return r;
  let detail = "";
  try { detail = String(((await r.clone().json()) as { detail?: unknown })?.detail ?? ""); } catch { /* sem corpo JSON */ }
  const e: Error & { status?: number } = new Error(detail.trim() || `HTTP ${r.status}`);
  e.status = r.status;
  throw e;
}

export async function getTask(hash: string): Promise<Task> {
  const r = await check(await busca(`/api/t/${hash}`, { headers: { Accept: "application/json" }, cache: "no-store" }));
  return r.json();
}

/* `consultas` conta quantas vezes a pessoa abriu "não lembro, mostra de novo" em cada pergunta. Viaja junto
   com as respostas porque entra no hash da tentativa e no comprovante: número que circula ao lado da prova
   sem estar dentro dela é número que qualquer um troca depois. */
export async function submitQuiz(hash: string, respostas: Record<string, number>,
                                 consultas: Record<string, number> = {}): Promise<QuizResult> {
  const r = await check(await busca(`/api/t/${hash}/quiz`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ respostas, consultas }),
  }));
  return r.json();
}

/* SSE over fetch: "data: {t: '...'}" per token, "data: {error: '...'}" on failure. */
export async function chat(hash: string, mensagem: string, onText: (acc: string) => void): Promise<string> {
  const r = await check(await busca(`/api/t/${hash}/chat`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mensagem }),
  }));
  if (!r.body) throw new Error("sem corpo");
  const reader = r.body.getReader();
  const dec = new TextDecoder();
  let buf = "", acc = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i: number;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, i).trim();
      buf = buf.slice(i + 2);
      if (!chunk.startsWith("data:")) continue;
      let ev: { t?: string; error?: string } = {};
      try { ev = JSON.parse(chunk.slice(5).trim()); } catch { continue; }
      if (ev.error) throw new Error(ev.error);
      if (ev.t) { acc += ev.t; onText(acc); }
    }
  }
  return acc;
}

export async function getVerify(attempt: string): Promise<VerifyResult> {
  const r = await check(await busca(`/api/verify/${attempt}`, { cache: "no-store" }));
  return r.json();
}

export const proofUrl = (attempt: string) => `/api/verify/${attempt}/proof`;

/* Topics: structured list from the service, or sections split from the markdown summary. */
export function topicsOf(task: Task): Topic[] {
  if (task.topicos && task.topicos.length) return task.topicos;
  const parts = (task.resumo_md || "").split(/\n(?=##? )/).map((p) => p.trim()).filter(Boolean);
  const topics = parts.map((p, i) => {
    const m = p.match(/^##? (.+)\n?([\s\S]*)$/);
    return m ? { id: i + 1, titulo: m[1].trim(), explicacao_md: m[2].trim() } : { id: i + 1, titulo: `Ponto ${i + 1}`, explicacao_md: p };
  });
  return topics.length ? topics : [{ id: 1, titulo: "Explicação", explicacao_md: task.resumo_md || "Explicação indisponível." }];
}

export function formatDateTime(iso: string): string {
  /* the service emits naive UTC timestamps (no Z); treat any string without a zone as UTC */
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short", timeZone: "America/Sao_Paulo" }).format(d);
}

/* ------------------------------------------------------------------------------------------------
   LeIA: v3 accounts and panels (docs/API-V3-CONTRACT.md). The session travels as the cookie of this origin. */
/* LeIA: review flow (docs/API-V3-CONTRACT.md, "Revisão do advogado"): pronta = waiting for the lawyer, enviada = released to
   the citizen; the public route answers "revisao" while a lawyer-owned task waits. */
export type TaskStatus = "criada" | "processando" | "pronta" | "enviada" | "assinada" | "falhou" | "revisao" | string;
export type TaskSummary = {
  id: number; hash: string; titulo: string; status: TaskStatus; criada_em: string; atualizada_em: string; link_cliente: string;
  origem: "advogado" | "cidadao"; ultima_tentativa: (Attempt & { comprovante_token?: string }) | null; duvidas_abertas: number;
  cidadao: { nome: string } | null; advogado: { nome: string } | null;
};
export type ChatTurn = { role: "user" | "bot"; text: string };
export type Doubt = { id: number; texto: string; contexto: ChatTurn[]; criada_em: string; respondida: boolean; resposta: string | null; respondida_em: string | null };
export type TaskEvent = { tipo?: string; id?: string; idx?: number; total?: number; ts?: string; [k: string]: unknown };
/* LeIA: o convite que governa o link do documento. Sem convite, o link abre para quem o tiver, como sempre foi. */
export type Invite = { id: number; nome: string | null; email: string | null; expira_em: string | null; revogado_em: string | null; criado_em: string };
export type TaskDetail = {
  tarefa: { id: number; hash: string; titulo: string; status: TaskStatus; criada_em: string; atualizada_em: string; origem: "advogado" | "cidadao" };
  link_cliente: string; convite?: Invite | null; resumo_md: string | null; eventos: TaskEvent[];
  tentativas: { numero: number; acertos: number; total: number; aprovado: boolean; criada_em: string; hash_imutavel: string; comprovante_token?: string }[];
  duvidas: Doubt[]; cidadao: { nome: string } | null; advogado: { nome: string } | null;
};

const jsonHeaders = () => ({ "Content-Type": "application/json", Accept: "application/json" });

export async function listTasks(): Promise<TaskSummary[]> {
  const r = await check(await busca(`/api/tarefas`, { headers: { Accept: "application/json" }, cache: "no-store" }));
  const { tarefas } = (await r.json()) as { tarefas: TaskSummary[] };
  return tarefas;
}
export async function createTask(titulo: string, pdf: File): Promise<{ id: number; hash: string; status: TaskStatus }> {
  const form = new FormData();
  form.append("titulo", titulo);
  form.append("pdf", pdf, pdf.name);
  const r = await check(await busca(`/api/tarefas`, { method: "POST", headers: { Accept: "application/json" }, body: form }));
  return r.json();
}
export async function getTaskDetail(id: string | number): Promise<TaskDetail> {
  const r = await check(await busca(`/api/tarefas/${id}`, { headers: { Accept: "application/json" }, cache: "no-store" }));
  return r.json();
}
export async function answerDoubt(id: string | number, duvidaId: number, resposta: string): Promise<{ ok: boolean }> {
  const r = await check(await busca(`/api/tarefas/${id}/duvidas/${duvidaId}/responder`, { method: "POST", headers: jsonHeaders(), body: JSON.stringify({ resposta }) }));
  return r.json();
}
export async function sendDoubt(hash: string, texto: string, contexto: ChatTurn[] = []): Promise<{ id: number; criada_em: string }> {
  const r = await check(await busca(`/api/t/${hash}/duvida`, { method: "POST", headers: jsonHeaders(), body: JSON.stringify({ texto, contexto }) }));
  return r.json();
}
export async function bindTask(hash: string): Promise<{ ok: boolean }> {
  const r = await check(await busca(`/api/t/${hash}/vincular`, { method: "POST", headers: jsonHeaders(), body: "{}" }));
  return r.json();
}
/* The citizen link is always a page of this app; the service may send it relative or absolute. */
export function clientLinkUrl(linkOrHash: string): string {
  const path = linkOrHash.startsWith("/") || linkOrHash.startsWith("http") ? linkOrHash : `/t/${linkOrHash}`;
  if (path.startsWith("http")) return path;
  return typeof window === "undefined" ? path : `${window.location.origin}${path}`;
}

/* LeIA: inferences (original text with the tagged quotes and what the workflow concluded).
   While the pipeline runs the service answers 200 with parcial: true (texto may be empty, classes only what exists so far);
   409 only while the lawyer reviews, 404 when the hash is unknown. */
import type { Inferences } from "./inferences";
export async function getInferences(hash: string): Promise<Inferences> {
  const r = await check(await busca(`/api/t/${hash}/inferencias`, { cache: "no-store" }));
  const data = (await r.json()) as Inferences;
  return { ...data, texto: data.texto ?? "", classes: data.classes ?? [], sinteses: data.sinteses ?? [], total: data.total ?? 0, conferidos: data.conferidos ?? 0 };
}
/* A score as the citizen reads it: 0 to 100 (the service sends 0..1 or 0..100). */
export function scorePercent(score: number): number {
  const v = score <= 1 ? score * 100 : score;
  return Math.max(0, Math.min(100, Math.round(v)));
}

/* LeIA: lawyer review before release (docs/API-V3-CONTRACT.md, "Revisão do advogado antes de liberar"). */
export type ReviewQuestion = Question & { dificuldade?: string; correta: number; justificativa: string };
export type Review = {
  tarefa: { id: number; hash: string; titulo: string; status: TaskStatus; origem: "advogado" | "cidadao" };
  inferencias: Inferences; resumo_md: string; questoes: ReviewQuestion[]; link_cliente: string;
  tipo_documento?: DocumentType | null; tipos_documento?: DocumentTypeOption[];
};
export async function getReview(id: string | number): Promise<Review> {
  const r = await check(await busca(`/api/tarefas/${id}/revisao`, { headers: { Accept: "application/json" }, cache: "no-store" }));
  return r.json();
}
/* `nome` é obrigatório e `email` não: é o nome que a destinatária vê na tela para confirmar que é
   ela, e nome é o que identifica alguém para alguém. Endereço serve para entregar. */
export async function issueInvite(id: string | number, input: { nome: string; email?: string; validade_horas?: number }): Promise<Invite> {
  const r = await check(await busca(`/api/tarefas/${id}/convite`, { method: "POST", headers: jsonHeaders(), body: JSON.stringify(input) }));
  return r.json();
}
export async function retryTask(id: string | number): Promise<{ ok: boolean; status: string }> {
  const r = await check(await busca(`/api/tarefas/${id}/reprocessar`, { method: "POST", headers: jsonHeaders() }));
  return r.json();
}
export async function unbindTask(id: string | number): Promise<{ ok: boolean }> {
  const r = await check(await busca(`/api/tarefas/${id}/cidadao`, { method: "DELETE", headers: jsonHeaders() }));
  return r.json();
}
export async function revokeInvite(id: string | number): Promise<Invite> {
  const r = await check(await busca(`/api/tarefas/${id}/convite`, { method: "DELETE", headers: jsonHeaders() }));
  return r.json();
}

/* The lawyer's answer about the species. It does not redo the explanation: the run that produced what is on
   screen already read the document with the old vocabulary, so the screen says so and offers "refazer". */
export async function setDocumentType(id: string | number, tipo: string): Promise<{ ok: boolean; tipo_documento: DocumentType }> {
  const r = await check(await busca(`/api/tarefas/${id}/tipo-documento`, { method: "POST", headers: jsonHeaders(), body: JSON.stringify({ tipo }) }));
  return r.json();
}

/* O que o advogado deixou é o que a cliente vai ler, e é para onde o comprovante vai apontar. A resposta
   traz a medida da porta de qualidade sobre o que acabou de ser gravado, porque renomear um título de seção
   desliga a âncora dela sem barulho nenhum e isso precisa aparecer antes de liberar. */
export async function saveReview(id: string | number, input: { resumo_md?: string; questoes?: number[] }):
  Promise<{ ok: boolean; porta_qualidade: { motivo: string | null } }> {
  const r = await check(await busca(`/api/tarefas/${id}/revisao`, { method: "POST", headers: jsonHeaders(), body: JSON.stringify(input) }));
  return r.json();
}

/* A cidadã confirma que o nome do convite é o dela, e entra. Sem e-mail, sem senha, sem código: o link que
   ela recebeu já prova que é ela. O token volta guardado no cookie pela rota do app, nunca no corpo. */
export async function confirmName(hash: string): Promise<{ usuario: { nome: string; papel: string } }> {
  const r = await check(await busca(`/api/t/${hash}/confirm-name`, { method: "POST", headers: jsonHeaders(), body: "{}" }));
  return r.json();
}

export async function approveTask(id: string | number): Promise<{ ok: boolean; status: TaskStatus }> {
  const r = await check(await busca(`/api/tarefas/${id}/aprovar`, { method: "POST", headers: jsonHeaders(), body: "{}" }));
  return r.json();
}
