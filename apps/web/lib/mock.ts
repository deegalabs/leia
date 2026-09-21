/* In-app mock of the cognitive service (same routes and shapes as apps/llm-service/mock/app.py), used when
   NEXT_PUBLIC_API_BASE is empty, e.g. on the hosted demo. Stateless: receipts travel as tokens. */
import fixture from "@/data/fixture-honorarios.json";
import { attemptHash, buildPayload, canonical, encodeToken, newSalt, nowIso, passMark, sha256, type AttemptRecord } from "./registry";
import { tokenFromRequest } from "./server/session";
import { findSpan, type Anchor, type InferenceClass, type Inferences } from "./inferences"; /* LeIA: review flow shares the inferences with the public route */
import type { Stage } from "./api";

type FixtureQuestion = { id: number; area: string; dificuldade: string; enunciado: string; alternativas: string[]; correta: number; justificativa: string; secao?: string; trecho?: string; conferencia?: Anchor };
/* LeIA: topics come from the local pipeline (clausula) */
type FixtureTopic = { id: number; titulo: string; explicacao: string; trecho: string; clausula?: string; classe?: string; score?: number };
type Fixture = Omit<typeof fixture, "topicos" | "documento_texto"> & { topicos: FixtureTopic[]; documento_texto: { clausula?: string; texto: string }[]; sem_perguntas?: boolean };
const F: Fixture = fixture;
const contentOf = (_t: MockTask): Fixture => F;

/* LeIA: v3 tasks live in the in-memory store; each one reuses the fixture content as if the pipeline finished. */
export function findTask(hash: string) {
  const t = storeTask(hash);
  if (!t) return null;
  const c = contentOf(t);
  return { ...c, tarefa: { ...c.tarefa, id: t.id, hash: t.hash, titulo: t.titulo, status: t.status } } as Fixture;
}

/* LeIA: mesma regra do serviço (leia/api_citizen.py, locate). O trecho só é mostrado como copiado do
   documento depois de ser encontrado nele, e a tela diz como foi encontrado. */
function checkedTopics(f: Fixture) {
  const texto = f.documento_texto.map((c) => c.texto).join("\n\n");
  return f.topicos.map((tp) => {
    const pos = tp.trecho ? findSpan(texto, tp.trecho) : null;
    if (!pos) return { ...tp, trecho: undefined };   // não achou no documento, então não há trecho a mostrar
    const exato = texto.slice(pos[0], pos[1]) === tp.trecho;
    return { ...tp, conferencia: { metodo: exato ? "exato" : "normalizado", score: 1 } as Anchor };
  });
}

export function publicTask(f: Fixture) {
  return {
    tarefa: f.tarefa, resumo_md: f.resumo_md, topicos: checkedTopics(f),
    questoes: (f.questoes.questoes as FixtureQuestion[]).map((q) => ({ id: q.id, enunciado: q.enunciado, alternativas: q.alternativas, area: q.area, secao: q.secao ?? null, trecho: q.trecho ?? null, conferencia: q.conferencia ?? null })),
    ultima_tentativa: null,
    sem_perguntas: Boolean(f.sem_perguntas),
  };
}

export function evaluateQuiz(f: Fixture, respostas: Record<string, number>, numero = 1 /* LeIA: v3 counts attempts per task */, consultas: Record<string, number> = {}) {
  const questions = f.questoes.questoes as FixtureQuestion[];
  const erros: { id: number; area: string; enunciado: string; escolhida: number | null }[] = [];
  let acertos = 0;
  for (const q of questions) {
    const chosen = respostas[String(q.id)];
    if (chosen === q.correta) acertos += 1;
    else erros.push({ id: q.id, area: q.area, enunciado: q.enunciado, escolhida: chosen ?? null });
  }
  const record: AttemptRecord = { tarefa_hash: f.tarefa.hash, numero, respostas, acertos, total: questions.length, aprovado: acertos >= passMark(questions.length), criada_em: nowIso(), salt: newSalt(), consultas };
  return { aprovado: record.aprovado, acertos, total: record.total, numero, hash_imutavel: attemptHash(record), comprovante_token: encodeToken(record), erros };
}

export function verifyRecord(record: AttemptRecord) {
  const payload = buildPayload(record);
  const c = canonical(payload);
  /* demo: the hosted mock has no storage, so no public timestamp is ever recorded */
  return { payload, canonical: c, payloadHash: sha256(c), otsPresent: false, demo: true };
}

const norm = (s: string) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
/* Grounded answer: topic sharing at least two words with the question; otherwise a literal refusal. */
export function answer(f: Fixture, mensagem: string): string {
  const words = new Set(norm(mensagem).replace(/\?/g, " ").split(/\s+/).filter((w) => w.length > 3));
  let best: (typeof f.topicos)[number] | null = null, score = 0;
  for (const t of f.topicos) {
    const hay = norm(`${t.titulo} ${t.explicacao} ${t.trecho}`);
    const s = [...words].filter((w) => hay.includes(w)).length;
    if (s > score) { best = t; score = s; }
  }
  if (best && score >= 2) return `${best.explicacao} O documento diz: "${best.trecho}"${best.clausula ? ` (cláusula ${best.clausula})` : ""}.`;
  return "Isso não está escrito neste documento. Posso explicar só o que está nele. Se for importante, anote para perguntar à sua advogada.";
}

/* ---------------------------------------------------------------------------------------------------
   LeIA: v3 in-memory state (docs/API-V3-CONTRACT.md): accounts, tasks per owner, attempts, doubts.
   One process-wide store kept on globalThis so dev reloads and every route handler share the same data.
   Good enough for a demo; nothing survives a restart and serverless instances do not share it. */
export type Role = "cidadao" | "advogado" | "fornecedor";
export type MockUser = { id: number; nome: string; email: string; papel: Role; oab: string | null; senha_hash: string; token: string | null };
export type MockDoubt = { id: number; texto: string; contexto: { role: "user" | "bot"; text: string }[]; criada_em: string; respondida: boolean; resposta: string | null; respondida_em: string | null };
export type MockAttempt = { numero: number; acertos: number; total: number; aprovado: boolean; criada_em: string; hash_imutavel: string; comprovante_token: string };
export type MockEvent = { tipo: string; ts: string; id?: string; idx?: number; total?: number };
export type MockTask = {
  id: number; hash: string; titulo: string; status: "criada" | "processando" | "pronta" | "enviada" | "assinada" | "falhou"; /* LeIA: enviada = released by the lawyer */
  criada_em: string; atualizada_em: string; origem: "advogado" | "cidadao"; dono_id: number; cidadao_id: number | null;
  ready_at: number; eventos: MockEvent[]; tentativas: MockAttempt[]; duvidas: MockDoubt[];
  /* LeIA: visible preparation. How many of the 15 steps started and finished */
  etapas_iniciadas: number; etapas_feitas: number;
  /* LeIA: a espécie com que o motor leu o documento, e a correção do advogado quando existe */
  tipo_documento?: MockDocumentType | null;
  /* LeIA: o que o advogado deixou na revisão (E12-T05) */
  resumo_editado?: string;
  questoes_mantidas?: number[];
  /* LeIA: o convite que governa o link; ausente significa link aberto, como sempre foi */
  convite?: MockInvite | null;
};

export type MockDocumentType = { tipo: string; rotulo: string; trecho: string; pos: [number, number] | null; conferido: boolean; revisado_por_advogado: boolean; aplicado?: boolean };
/* LeIA: as espécies que o protocolo declara (apps/llm-service/protocolo_pdf.json, "tipos_de_documento") */
export const DOC_TYPES: { tipo: string; rotulo: string }[] = [
  { tipo: "peca_processual", rotulo: "Documento de um processo" },
  { tipo: "decisao_judicial", rotulo: "Decisão da Justiça" },
  { tipo: "contrato", rotulo: "Contrato" },
  { tipo: "comunicacao_oficial", rotulo: "Aviso oficial" },
  { tipo: "indefinido", rotulo: "Tipo não identificado" },
];

/* `usuario_id`: de quem o convite passou a ser. Destinatária é uma conta, não um endereço, porque a conta
   criada pela confirmação de nome não tem e-mail nenhum para comparar. Igual ao serviço. */
export type MockInvite = { id: number; nome: string | null; email: string | null; usuario_id: number | null; expira_em: string | null; revogado_em: string | null; criado_em: string };

/* LeIA: the 15 workflow steps in pt-BR (docs/API-V3-CONTRACT.md, "Preparação visível e tarefas do fluxo externo") and the
   seconds each one reports once finished (illustrative; the simulated pipeline is faster than the real one) */
export const STEP_NAMES = ["Reconhecer o tipo do documento", "Identificar as partes", "Datas e valores", "Fatos", "Fundamentos, leis e decisões", "Pedidos", "Juntar a memória", "Resumir os fatos", "Resumir os fundamentos", "Resumir os pedidos", "Quem é quem", "Contexto do processo", "Marcar o texto", "Explicar em linguagem simples", "Preparar as perguntas"];
const STEP_SECONDS = [2, 3, 4, 5, 6, 4, 2, 5, 5, 4, 3, 4, 6, 9, 7];
const STEP_TOTAL = STEP_NAMES.length;
type Store = { users: Map<number, MockUser>; tasks: Map<string, MockTask>; seq: { user: number; task: number; doubt: number } };

const PIPELINE_MS = 8000;
const PROCESSING_DELAY_MS = 1000; /* criada -> processando */
const STEP_MS = (PIPELINE_MS - PROCESSING_DELAY_MS) / STEP_TOTAL; /* each simulated step */
const REVIEW_DEMO_HASH = "revisao-exemplo"; /* LeIA: seeded lawyer task waiting for review */
const SEED_PASSWORD = "leia1234";
const hashPassword = (senha: string) => sha256(`leia-mock:${senha}`);

function seed(): Store {
  const users = new Map<number, MockUser>();
  users.set(1, { id: 1, nome: "Advogada Exemplo", email: "advogada@exemplo.leia", papel: "advogado", oab: "PR 000000", senha_hash: hashPassword(SEED_PASSWORD), token: null });
  users.set(2, { id: 2, nome: "Cidadã Exemplo", email: "cidada@exemplo.leia", papel: "cidadao", oab: null, senha_hash: hashPassword(SEED_PASSWORD), token: null });
  const ts = nowIso();
  const tasks = new Map<string, MockTask>();
  /* LeIA: review flow. The demo task is already released ("enviada") so the landing example keeps working;
     a second task of the same lawyer waits in "pronta" to show the review screen. */
  const finished = { etapas_iniciadas: STEP_TOTAL, etapas_feitas: STEP_TOTAL };
  /* the seeded tasks finished the pipeline before the process started: full step log with the same timestamp */
  const stepEvents: MockEvent[] = STEP_NAMES.flatMap((_, i) => [{ tipo: "task_start", ts, id: `T${i + 1}`, idx: i, total: STEP_TOTAL }, { tipo: "task_done", ts, id: `T${i + 1}`, idx: i, total: STEP_TOTAL }]);
  tasks.set(F.tarefa.hash, {
    id: F.tarefa.id, hash: F.tarefa.hash, titulo: F.tarefa.titulo, status: "enviada", criada_em: ts, atualizada_em: ts, origem: "advogado", dono_id: 1, cidadao_id: null, ready_at: 0,
    eventos: [{ tipo: "criada", ts }, { tipo: "extracao_texto", ts }, ...stepEvents, { tipo: "pipeline_concluido", ts }, { tipo: "aprovada", ts }], tentativas: [],
    duvidas: [{ id: 1, texto: "Se eu perder a ação, ainda pago os 20%?", contexto: [{ role: "user", text: "Se eu perder a ação, ainda pago os 20%?" }, { role: "bot", text: "O documento diz que os 20% incidem sobre o valor efetivamente recebido na ação." }], criada_em: ts, respondida: false, resposta: null, respondida_em: null }],
    ...finished,
  });
  tasks.set(REVIEW_DEMO_HASH, {
    id: 2, hash: REVIEW_DEMO_HASH, titulo: "Contrato de honorários: ação de cobrança", status: "pronta", criada_em: ts, atualizada_em: ts, origem: "advogado", dono_id: 1, cidadao_id: null, ready_at: 0,
    eventos: [{ tipo: "criada", ts }, { tipo: "extracao_texto", ts }, ...stepEvents, { tipo: "pipeline_concluido", ts }], tentativas: [], duvidas: [], ...finished,
  });
  return { users, tasks, seq: { user: 2, task: 2, doubt: 1 } };
}
const g = globalThis as unknown as { __leiaMockStore?: Store };
const store = (): Store => (g.__leiaMockStore ??= seed());

/* LeIA: visible preparation. Moves the step counters forward and logs task_start / task_done like the workflow's log.jsonl. */
function advanceSteps(t: MockTask, done: number, started: number) {
  const ts = nowIso();
  while (t.etapas_feitas < Math.min(done, STEP_TOTAL)) {
    const i = t.etapas_feitas;
    if (t.etapas_iniciadas <= i) { t.eventos.push({ tipo: "task_start", ts, id: `T${i + 1}`, idx: i, total: STEP_TOTAL }); t.etapas_iniciadas = i + 1; }
    t.eventos.push({ tipo: "task_done", ts, id: `T${i + 1}`, idx: i, total: STEP_TOTAL }); t.etapas_feitas = i + 1;
  }
  if (t.etapas_iniciadas < Math.min(started, STEP_TOTAL)) { const i = t.etapas_iniciadas; t.eventos.push({ tipo: "task_start", ts, id: `T${i + 1}`, idx: i, total: STEP_TOTAL }); t.etapas_iniciadas = i + 1; }
}
/* the 15 steps as the public route reports them */
export function stagesOf(t: MockTask): Stage[] {
  return STEP_NAMES.map((nome, i) => {
    const estado: Stage["estado"] = i < t.etapas_feitas ? "concluida" : i < t.etapas_iniciadas ? (t.status === "falhou" ? "erro" : "em_andamento") : "pendente";
    return estado === "concluida" ? { id: `T${i + 1}`, nome, estado, tempo: STEP_SECONDS[i] } : { id: `T${i + 1}`, nome, estado };
  });
}

/* status settles with time: created -> processing after 1s -> ready after PIPELINE_MS.
   LeIA: while processing, the 15 steps advance one every STEP_MS so the wait screen can show them. */
function settle(t: MockTask): MockTask {
  const now = Date.now();
  const processingAt = t.ready_at - PIPELINE_MS + PROCESSING_DELAY_MS;
  if (t.status === "criada" && now >= processingAt) { t.status = "processando"; t.atualizada_em = nowIso(); t.eventos.push({ tipo: "extracao_texto", ts: t.atualizada_em }); }
  if (t.status === "processando") {
    const done = Math.min(STEP_TOTAL, Math.floor((now - processingAt) / STEP_MS));
    advanceSteps(t, done, done + 1);
  }
  if (t.status === "processando" && now >= t.ready_at) { advanceSteps(t, STEP_TOTAL, STEP_TOTAL); t.status = "pronta"; t.atualizada_em = nowIso(); t.eventos.push({ tipo: "pipeline_concluido", ts: t.atualizada_em }); }
  return t;
}
export const storeTask = (hash: string): MockTask | null => { const t = store().tasks.get(hash); return t ? settle(t) : null; };
export const storeTaskById = (id: number): MockTask | null => { for (const t of store().tasks.values()) if (t.id === id) return settle(t); return null; };
const userById = (id: number) => store().users.get(id) ?? null;
/* A chave `oab` está sempre aqui e é nula para quem não tem número, como no serviço: a tela lê o
   número sem precisar perguntar antes de quem é a conta. */
const publicUser = (u: MockUser) => ({ id: u.id, nome: u.nome, email: u.email, papel: u.papel, oab: u.oab });
const nameOf = (id: number | null) => { const u = id ? userById(id) : null; return u ? { nome: u.nome } : null; };

/* auth */
export type AuthError = { status: number; detail: string };
const fail = (status: number, detail: string): AuthError => ({ status, detail });
export function register(input: { nome?: unknown; email?: unknown; senha?: unknown; papel?: unknown; oab?: unknown }) {
  const nome = String(input.nome ?? "").trim(), email = String(input.email ?? "").trim().toLowerCase(), senha = String(input.senha ?? ""), papel = String(input.papel ?? "cidadao");
  if (!nome || !email || !senha) throw fail(422, "nome, e-mail e senha são obrigatórios");
  if (papel !== "cidadao" && papel !== "advogado") throw fail(403, "papel não permitido");
  const s = store();
  for (const u of s.users.values()) if (u.email === email) throw fail(409, "e-mail já cadastrado");
  const user: MockUser = { id: ++s.seq.user, nome, email, papel, oab: papel === "advogado" ? String(input.oab ?? "").trim() || null : null, senha_hash: hashPassword(senha), token: newSalt() };
  s.users.set(user.id, user);
  return { token: user.token as string, usuario: publicUser(user) };
}
export function login(input: { email?: unknown; senha?: unknown }) {
  const email = String(input.email ?? "").trim().toLowerCase(), senha = String(input.senha ?? "");
  for (const u of store().users.values()) {
    if (u.email === email && u.senha_hash === hashPassword(senha)) { u.token = newSalt(); return { token: u.token, usuario: publicUser(u) }; }
  }
  throw fail(401, "e-mail ou senha inválidos");
}
export function userFromRequest(req: Request): MockUser | null {
  /* The session lives in an HttpOnly cookie (lib/server/session.ts). Bearer stays accepted so a request
     made by hand, or a page still running an old bundle, keeps working. */
  const h = req.headers.get("authorization") ?? "";
  const token = h.toLowerCase().startsWith("bearer ") ? h.slice(7).trim() : tokenFromRequest(req) ?? "";
  if (!token) return null;
  for (const u of store().users.values()) if (u.token === token) return u;
  return null;
}
export function logout(u: MockUser) { u.token = null; return { ok: true }; }
export const meOf = (u: MockUser) => ({ usuario: publicUser(u) });

/* tasks */
const canSee = (u: MockUser, t: MockTask) => u.papel === "fornecedor" || t.dono_id === u.id || t.cidadao_id === u.id;
const canManage = (u: MockUser, t: MockTask) => u.papel === "fornecedor" || t.dono_id === u.id;
const clientLink = (t: MockTask) => `/t/${t.hash}`;
const lastAttempt = (t: MockTask) => { const a = t.tentativas[t.tentativas.length - 1]; return a ? { aprovado: a.aprovado, acertos: a.acertos, total: a.total, numero: a.numero, hash_imutavel: a.hash_imutavel, comprovante_token: a.comprovante_token } : null; };
const lawyerOf = (t: MockTask) => (t.origem === "advogado" ? nameOf(t.dono_id) : null);
/* Para a cidadã o nome vem com o número da OAB, que é o que ela pode conferir no cadastro da Ordem.
   No painel do advogado o número não acrescenta nada, então `lawyerOf` continua só com o nome. */
const lawyerForCitizen = (t: MockTask) => {
  if (t.origem !== "advogado") return null;
  const u = userById(t.dono_id);
  return u ? { nome: u.nome, oab: u.oab } : null;
};

export function listTasks(u: MockUser) {
  const all = [...store().tasks.values()].map(settle).filter((t) => canSee(u, t));
  all.sort((a, b) => (a.criada_em < b.criada_em ? 1 : -1));
  return { tarefas: all.map((t) => ({
    id: t.id, hash: t.hash, titulo: t.titulo, status: t.status, criada_em: t.criada_em, atualizada_em: t.atualizada_em, link_cliente: clientLink(t), origem: t.origem,
    ultima_tentativa: lastAttempt(t), duvidas_abertas: t.duvidas.filter((d) => !d.respondida).length, cidadao: nameOf(t.cidadao_id), advogado: lawyerOf(t),
  })) };
}
export function createTask(u: MockUser, titulo: string) {
  const s = store();
  const ts = nowIso();
  const t: MockTask = {
    id: ++s.seq.task, hash: newSalt().slice(0, 16), titulo: titulo.trim() || "Documento sem título", status: "criada", criada_em: ts, atualizada_em: ts,
    origem: u.papel === "cidadao" ? "cidadao" : "advogado", dono_id: u.id, cidadao_id: u.papel === "cidadao" ? u.id : null, ready_at: Date.now() + PIPELINE_MS,
    eventos: [{ tipo: "criada", ts }], tentativas: [], duvidas: [], etapas_iniciadas: 0, etapas_feitas: 0,
  };
  s.tasks.set(t.hash, t);
  return { id: t.id, hash: t.hash, status: t.status };
}
export function taskDetail(u: MockUser, id: number) {
  const t = storeTaskById(id);
  if (!t) throw fail(404, "não encontrado");
  if (!canSee(u, t)) throw fail(403, "sem acesso");
  return {
    tarefa: { id: t.id, hash: t.hash, titulo: t.titulo, status: t.status, criada_em: t.criada_em, atualizada_em: t.atualizada_em, origem: t.origem },
    convite: t.convite ?? null, link_cliente: clientLink(t), resumo_md: hasContent(t) ? contentOf(t).resumo_md : null, eventos: t.eventos.slice(-20),
    tentativas: t.tentativas.map(({ numero, acertos, total, aprovado, criada_em, hash_imutavel, comprovante_token }) => ({ numero, acertos, total, aprovado, criada_em, hash_imutavel, comprovante_token })),
    duvidas: t.duvidas, cidadao: nameOf(t.cidadao_id), advogado: lawyerOf(t),
  };
}
export function answerDoubt(u: MockUser, id: number, duvidaId: number, resposta: string) {
  const t = storeTaskById(id);
  if (!t) throw fail(404, "não encontrado");
  if (!canManage(u, t)) throw fail(403, "sem acesso");
  const d = t.duvidas.find((x) => x.id === duvidaId);
  if (!d) throw fail(404, "dúvida não encontrada");
  if (!resposta.trim()) throw fail(422, "resposta vazia");
  d.resposta = resposta.trim(); d.respondida = true; d.respondida_em = nowIso(); t.atualizada_em = d.respondida_em;
  return { ok: true };
}

/* LeIA: review flow (docs/API-V3-CONTRACT.md, "Revisão do advogado antes de liberar") */
const hasContent = (t: MockTask) => t.status === "pronta" || t.status === "enviada" || t.status === "assinada";
/* the citizen may open the explanation: released, signed, or a citizen-owned task that is ready */
export const isReleased = (t: MockTask) => t.status === "enviada" || t.status === "assinada" || (t.status === "pronta" && t.origem === "cidadao");
export const inReview = (t: MockTask) => t.status === "pronta" && t.origem === "advogado";
/* 409 body shared by the public routes while the lawyer reviews or the pipeline runs */
function ownedByMe(u: MockUser, id: number): MockTask {
  const t = storeTaskById(id);
  if (!t || t.dono_id !== u.id) throw fail(404, "Documento não encontrado");
  return t;
}

export function issueInvite(u: MockUser, id: number, input: { nome?: unknown; email?: unknown; validade_horas?: unknown }): MockInvite {
  const t = ownedByMe(u, id);
  const horas = Math.max(1, Number(input.validade_horas) || 30 * 24);
  const email = String(input.email ?? "").trim().toLowerCase() || null;
  const nome = String(input.nome ?? "").trim();
  if (!nome) throw fail(422, "o nome de quem vai receber é obrigatório");
  t.convite = { id: (t.convite?.id ?? 0) + 1, nome, email, usuario_id: null, criado_em: nowIso(), revogado_em: null,
                expira_em: new Date(Date.now() + horas * 3600_000).toISOString() };
  return t.convite;
}

export function retryTask(u: MockUser, id: number) {
  const t = ownedByMe(u, id);
  if (t.status === "processando") throw fail(409, "Este documento ainda está sendo preparado.");
  t.status = "criada"; t.etapas_iniciadas = 0; t.etapas_feitas = 0; t.ready_at = Date.now() + 6000;
  t.atualizada_em = nowIso();
  t.eventos.push({ tipo: "reprocessar", ts: t.atualizada_em });
  return { ok: true, status: t.status };
}

export function unbindTask(u: MockUser, id: number) {
  const t = ownedByMe(u, id);
  if (t.cidadao_id === null) throw fail(404, "Este documento não está vinculado a ninguém.");
  /* A tentativa pertence à tarefa, não à pessoa: trocar a conta vinculada por cima de uma tentativa faria a
     próxima cidadã herdar o comprovante da anterior, que afirma que outra pessoa entendeu o documento. */
  if (t.tentativas.length > 0) throw fail(409, "Este documento já tem conferência registrada nesta conta. Envie o documento de novo para a outra pessoa, em vez de trocar quem está vinculado aqui.");
  t.cidadao_id = null;
  t.atualizada_em = nowIso();
  t.eventos.push({ tipo: "cidadao_desvinculado", ts: t.atualizada_em });
  return { ok: true };
}

export function revokeInvite(u: MockUser, id: number): MockInvite {
  const t = ownedByMe(u, id);
  if (!t.convite) throw fail(404, "Este documento não tem convite para cancelar.");
  t.convite.revogado_em = t.convite.revogado_em ?? nowIso();
  return t.convite;
}

/* LeIA: mesma regra do serviço (apps/llm-service/leia/invites.py), em duas camadas.
   Validade do link vale para todo mundo; a destinatária só vale para o que produz o comprovante. */
const mine = (t: MockTask, visitor: MockUser | null) => Boolean(visitor && (visitor.id === t.dono_id || visitor.id === t.cidadao_id));

export function inviteGate(t: MockTask, visitor: MockUser | null): Response | null {
  if (mine(t, visitor)) return null;
  const c = t.convite;
  if (!c) return null;
  if (c.revogado_em) return Response.json({ detail: "Este link foi cancelado por quem enviou o documento." }, { status: 403 });
  if (c.expira_em && new Date(c.expira_em).getTime() <= Date.now()) {
    return Response.json({ detail: "Este link venceu. Peça um novo a quem enviou o documento." }, { status: 403 });
  }
  return null;
}

/* Ler e perguntar não exigem conta. O comprovante exige, porque ele afirma que uma pessoa entendeu. */
export function recipientGate(t: MockTask, visitor: MockUser | null): Response | null {
  const invalid = inviteGate(t, visitor);
  if (invalid) return invalid;
  if (mine(t, visitor)) return null;
  const c = t.convite;
  if (!c?.email) return null;
  if (!visitor) return Response.json({ detail: "Para guardar o comprovante, entre com o e-mail que recebeu este documento." }, { status: 403 });
  if (visitor.email.trim().toLowerCase() !== c.email) {
    return Response.json({ detail: "Este documento foi enviado para outra pessoa, então o comprovante não pode sair nesta conta." }, { status: 403 });
  }
  return null;
}

const maskedEmail = (email: string | null) => {
  if (!email || !email.includes("@")) return null;
  const [user, domain] = email.split("@");
  return `${user.slice(0, 2)}***@${domain}`;
};

export function invitePublicJson(t: MockTask) {
  const c = t.convite;
  if (!c || c.revogado_em) return null;
  return { nome: c.nome, enderecado: Boolean(c.email), para: maskedEmail(c.email), expira_em: c.expira_em };
}

export function publicGate(hash: string, visitor: MockUser | null = null, needsRecipient = false): Response | null {
  const t = storeTask(hash);
  if (!t) return Response.json({ detail: "não encontrado" }, { status: 404 });
  const invite = needsRecipient ? recipientGate(t, visitor) : inviteGate(t, visitor);
  if (invite) return invite;
  if (inReview(t)) return Response.json({ detail: "Em revisão pelo advogado" }, { status: 409 });
  if (!isReleased(t)) return Response.json({ detail: "ainda não está pronta" }, { status: 409 });
  return null;
}
/* the fixture's clauses become tagged items over the extracted text (same body as GET /api/t/{hash}/inferencias).
   LeIA: partial = while the pipeline runs (docs/API-V3-CONTRACT.md, "Preparação visível"): no text before extraction and only
   the items the finished steps would have produced, with parcial: true. */
export function buildInferences(t: MockTask, partial = false): Inferences {
  const f = contentOf(t);
  const texto = partial && t.status === "criada" ? "" : f.documento_texto.map((c) => c.texto).join("\n\n");
  const visible = partial ? f.topicos.slice(0, Math.min(f.topicos.length, t.etapas_feitas)) : f.topicos;
  const classes: InferenceClass[] = [];
  const classFor = (key: string, rotulo: string, cor: string) => { let c = classes.find((x) => x.classe === key); if (!c) { c = { classe: key, rotulo, cor, itens: [] }; classes.push(c); } return c; };
  const refs: string[] = [];
  visible.forEach((tp) => {
    const key = "clausulas";
    const meta = { rotulo: "Cláusulas explicadas", cor: "#E3F1F1" };
    const c = classFor(key, meta.rotulo, meta.cor);
    const ref = `${key}[${c.itens.length}]`; refs.push(ref);
    const pos = texto ? findSpan(texto, tp.trecho) : null;
    const item = { ref, campo: `cláusula ${tp.clausula}`, valor: tp.titulo, trecho: tp.trecho, pos, conferido: !!pos, cor: meta.cor,
                   ...(pos ? { conferencia: { metodo: texto.slice(pos[0], pos[1]) === tp.trecho ? "exato" : "normalizado", score: 1 } as Anchor } : {}) };
    c.itens.push(tp.score !== undefined ? { ...item, score: tp.score } : item);
  });
  const itens = classes.flatMap((c) => c.itens);
  return {
    tarefa: { hash: t.hash, titulo: t.titulo },
    texto, classes,
    sinteses: partial ? [] : visible.map((tp, n) => ({ classe: refs[n].replace(/\[\d+\]$/, ""), rotulo: tp.titulo, texto: tp.explicacao, lastro: [refs[n]] })),
    total: itens.length, conferidos: itens.filter((i) => i.conferido).length,
    ...(partial ? { parcial: true } : {}),
  };
}
/* LeIA: partial inferences are only for a task still in the pipeline (409 in review, null otherwise) */
export const isProcessing = (t: MockTask) => t.status === "criada" || t.status === "processando";
export function review(u: MockUser, id: number) {
  const t = storeTaskById(id);
  if (!t) throw fail(404, "não encontrado");
  if (!canManage(u, t)) throw fail(403, "sem acesso");
  if (!hasContent(t)) throw fail(409, t.status === "falhou" ? "a explicação não pôde ser preparada" : "ainda não está pronta");
  return {
    tarefa: { id: t.id, hash: t.hash, titulo: t.titulo, status: t.status, origem: t.origem },
    tipo_documento: docTypeOf(t), tipos_documento: DOC_TYPES,
    inferencias: buildInferences(t), resumo_md: contentOf(t).resumo_md,
    questoes: (contentOf(t).questoes.questoes as FixtureQuestion[]).map((q) => ({ id: q.id, area: q.area, dificuldade: q.dificuldade, enunciado: q.enunciado, alternativas: q.alternativas, correta: q.correta, justificativa: q.justificativa })),
    link_cliente: clientLink(t),
  };
}
/* LeIA: a resposta do advogado sobre a espécie. Ela vale para a próxima rodada, então `aplicado` fica falso
   até o documento ser refeito, e a tela diz isso em vez de fingir que a explicação já mudou. */
export function setDocumentType(u: MockUser, id: number, tipo: string) {
  const t = storeTaskById(id);
  if (!t) throw fail(404, "não encontrado");
  if (!canManage(u, t)) throw fail(403, "sem acesso");
  const escolhido = DOC_TYPES.find((d) => d.tipo === tipo);
  if (!escolhido) throw fail(422, "Essa espécie de documento não existe.");
  t.tipo_documento = { ...escolhido, trecho: "", pos: null, conferido: false, revisado_por_advogado: true, aplicado: false };
  t.eventos.push({ tipo: "tipo_documento", ts: nowIso() });
  return { ok: true, tipo_documento: t.tipo_documento };
}

/* LeIA (E12-T05): a demonstração guarda a edição na tarefa, do mesmo jeito que o serviço guarda no
   workspace. O piso é o mesmo: ou nenhuma pergunta, ou pelo menos QUESTION_FLOOR. */
const QUESTION_FLOOR = 4;
export function saveReview(u: MockUser, id: number, body: { resumo_md?: string; questoes?: number[] }) {
  const t = storeTaskById(id);
  if (!t) throw fail(404, "não encontrado");
  if (!canManage(u, t)) throw fail(403, "sem acesso");
  if (t.status === "enviada" || t.status === "assinada")
    throw fail(409, "Este documento já foi liberado. Para mudar a explicação, refaça o documento.");
  if (body.questoes) {
    if (body.questoes.length > 0 && body.questoes.length < QUESTION_FLOOR)
      throw fail(422, `Com menos de ${QUESTION_FLOOR} perguntas o comprovante afirma mais do que mediu.`);
    t.questoes_mantidas = body.questoes;
  }
  if (typeof body.resumo_md === "string") t.resumo_editado = body.resumo_md;
  t.eventos.push({ tipo: "revisao_salva", ts: nowIso() });
  return { ok: true, porta_qualidade: { motivo: null } };
}

/* LeIA (E15): a demonstração cria a conta sem e-mail e sem senha, igual ao serviço, e vincula o documento
   a ela. A segunda pessoa no mesmo documento recebe 409: o comprovante afirma que **uma** pessoa entendeu. */
export function confirmName(hash: string) {
  const t = storeTask(hash);
  if (!t) throw fail(404, "não encontrado");
  const inv = t.convite;
  if (!inv || inv.revogado_em || !inv.nome) throw fail(409, "Este convite não diz para quem é.");
  if (t.cidadao_id !== null || inv.usuario_id !== null) throw fail(409, "Este documento já está vinculado a outra conta.");
  const s = store();
  const id = ++s.seq.user;
  const token = `tok-${id}-${sha256(`confirm:${hash}:${id}`).slice(0, 16)}`;
  const u: MockUser = { id, nome: inv.nome, email: "", papel: "cidadao", oab: null, senha_hash: "", token };
  s.users.set(id, u);
  t.cidadao_id = id;
  inv.usuario_id = id;
  return { token, usuario: { nome: u.nome, papel: u.papel } };
}

export function approve(u: MockUser, id: number) {
  const t = storeTaskById(id);
  if (!t) throw fail(404, "não encontrado");
  if (!canManage(u, t)) throw fail(403, "sem acesso");
  if (t.status !== "pronta") throw fail(409, `só é possível aprovar em "pronta" (estado atual: ${t.status})`);
  t.status = "enviada"; t.atualizada_em = nowIso(); t.eventos.push({ tipo: "aprovada", ts: t.atualizada_em });
  return { ok: true, status: t.status };
}

/* citizen side (public by hash) */
export function publicTaskMeta(t: MockTask) {
  return { advogado: lawyerForCitizen(t), tem_advogado: t.origem === "advogado", cidadao_vinculado: t.cidadao_id !== null, duvidas_enviadas: t.duvidas.length, ultima_tentativa: lastAttempt(t), tipo_documento: docTypeOf(t) };
}
/* O exemplo semeado é um contrato de honorários, então a espécie da demonstração é essa; tarefa que ainda
   não passou pela primeira etapa não tem espécie nenhuma, e ausente é o que a tela precisa saber. */
function docTypeOf(t: MockTask): MockDocumentType | null {
  if (t.tipo_documento) return t.tipo_documento;
  if (t.etapas_feitas < 1) return null;
  return { tipo: "contrato", rotulo: "Contrato", trecho: "CONTRATO DE PRESTAÇÃO DE SERVIÇOS ADVOCATÍCIOS",
           pos: null, conferido: true, revisado_por_advogado: false, aplicado: true };
}
/* while the pipeline runs the public payload carries no content, like the service */
export function publicTaskFor(hash: string) {
  const t = storeTask(hash); const f = findTask(hash);
  if (!t || !f) return null;
  const base = publicTask(f);
  /* LeIA: review gate. A lawyer-owned task in "pronta" answers "revisao" with no content until the lawyer approves. */
  /* LeIA: visible preparation. etapas with the 14 steps and every pipeline event (up to 60), like the service. */
  const progress = { etapas: stagesOf(t), eventos: t.eventos.slice(-60) };
  if (inReview(t)) return { ...base, tarefa: { ...base.tarefa, status: "revisao" }, resumo_md: null, topicos: null, questoes: [], sem_perguntas: false, ...progress, ...publicTaskMeta(t), convite: invitePublicJson(t) };
  const ready = isReleased(t);
  return { ...base, resumo_md: ready ? base.resumo_md : "", topicos: ready ? base.topicos : null, questoes: ready ? base.questoes : [], sem_perguntas: ready && base.sem_perguntas, ...progress, ...publicTaskMeta(t), convite: invitePublicJson(t) };
}
export function recordAttempt(hash: string, r: ReturnType<typeof evaluateQuiz>) {
  const t = storeTask(hash);
  if (!t) return;
  t.tentativas.push({ numero: r.numero, acertos: r.acertos, total: r.total, aprovado: r.aprovado, criada_em: nowIso(), hash_imutavel: r.hash_imutavel, comprovante_token: r.comprovante_token });
  t.atualizada_em = nowIso();
  t.eventos.push({ tipo: r.aprovado ? "entendimento_registrado" : "tentativa_registrada", ts: t.atualizada_em, id: String(r.numero) });
  if (r.aprovado) t.status = "assinada";
}
export const nextAttemptNumber = (hash: string) => (storeTask(hash)?.tentativas.length ?? 0) + 1;
export function sendDoubt(hash: string, texto: string, contexto: unknown) {
  const t = storeTask(hash);
  if (!t) throw fail(404, "não encontrado");
  if (t.origem !== "advogado") throw fail(409, "a tarefa não tem advogado");
  if (!texto.trim()) throw fail(422, "texto vazio");
  const ctx = Array.isArray(contexto) ? contexto.filter((m) => m && (m.role === "user" || m.role === "bot") && typeof m.text === "string").map((m) => ({ role: m.role as "user" | "bot", text: String(m.text).slice(0, 2000) })).slice(-12) : [];
  const d: MockDoubt = { id: ++store().seq.doubt, texto: texto.trim().slice(0, 2000), contexto: ctx, criada_em: nowIso(), respondida: false, resposta: null, respondida_em: null };
  t.duvidas.push(d); t.atualizada_em = d.criada_em;
  return { id: d.id, criada_em: d.criada_em };
}
export function bindTask(u: MockUser, hash: string) {
  const t = storeTask(hash);
  if (!t) throw fail(404, "não encontrado");
  if (u.papel !== "cidadao") throw fail(403, "só a cidadã pode se vincular");
  /* Ler segue aberto a quem tem o link. Vincular é virar dona do documento, e quem chega depois recebe
     409, então o primeiro que aparece trancaria os demais: exige convite vivo, como no serviço. */
  if (!mine(t, u) && !t.convite) throw fail(403, "Este documento ainda não tem convite. Peça um link novo a quem enviou.");
  if (t.cidadao_id === null) { t.cidadao_id = u.id; t.atualizada_em = nowIso(); t.eventos.push({ tipo: "cidadao_vinculado", ts: t.atualizada_em }); }
  return { ok: true };
}
export const isAuthError = (e: unknown): e is AuthError => typeof e === "object" && e !== null && "status" in e && "detail" in e;
export function errorResponse(e: unknown) {
  if (isAuthError(e)) return Response.json({ detail: e.detail }, { status: e.status });
  return Response.json({ detail: "erro interno" }, { status: 500 });
}
