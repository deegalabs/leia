/* In-app mock of the cognitive service (same routes and shapes as apps/llm-service/mock/app.py), used when
   NEXT_PUBLIC_API_BASE is empty, e.g. on the hosted demo. Stateless: receipts travel as tokens. */
import fixture from "@/data/fixture-honorarios.json";
import externalFixture from "@/data/fixture-externo.json"; /* LeIA: external "Resumo estruturado" flow: topics with score, no questions */
import { attemptHash, buildPayload, canonical, encodeToken, newSalt, nowIso, sha256, type AttemptRecord } from "./registry";
import { tokenFromRequest } from "./server/session";
import { findSpan, type InferenceClass, type Inferences } from "./inferences"; /* LeIA: review flow shares the inferences with the public route */
import type { Stage } from "./api";

type FixtureQuestion = { id: number; area: string; dificuldade: string; enunciado: string; alternativas: string[]; correta: number; justificativa: string };
/* LeIA: topics may come from the local pipeline (clausula) or from the external flow (classe + score) */
type FixtureTopic = { id: number; titulo: string; explicacao: string; trecho: string; clausula?: string; classe?: string; score?: number };
type Fixture = Omit<typeof fixture, "topicos" | "documento_texto"> & { topicos: FixtureTopic[]; documento_texto: { clausula?: string; texto: string }[]; sem_perguntas?: boolean };
const F: Fixture = fixture;
/* LeIA: what the external flow leaves behind: resumo_md from "resposta_final", topics from "classe_*", no questions */
const EXT: Fixture = { ...F, tarefa: { ...F.tarefa, ...externalFixture.tarefa, pdf_nome: "peticao-inicial-cobranca.pdf" }, documento_texto: externalFixture.documento_texto, topicos: externalFixture.topicos, resumo_md: externalFixture.resumo_md, questoes: { questoes: [] }, sem_perguntas: true };
const EXTERNAL_DEMO_HASH = externalFixture.tarefa.hash;
const contentOf = (t: MockTask): Fixture => (t.externa ? EXT : F);

/* LeIA: v3 tasks live in the in-memory store; each one reuses the fixture content as if the pipeline finished. */
export function findTask(hash: string) {
  const t = storeTask(hash);
  if (!t) return null;
  const c = contentOf(t);
  return { ...c, tarefa: { ...c.tarefa, id: t.id, hash: t.hash, titulo: t.titulo, status: t.status } } as Fixture;
}

export function publicTask(f: Fixture) {
  return {
    tarefa: f.tarefa, resumo_md: f.resumo_md, topicos: f.topicos,
    questoes: (f.questoes.questoes as FixtureQuestion[]).map((q) => ({ id: q.id, enunciado: q.enunciado, alternativas: q.alternativas, area: q.area })),
    ultima_tentativa: null,
    sem_perguntas: Boolean(f.sem_perguntas), /* LeIA: external flow ends the journey without questions */
  };
}

export function evaluateQuiz(f: Fixture, respostas: Record<string, number>, numero = 1 /* LeIA: v3 counts attempts per task */) {
  const questions = f.questoes.questoes as FixtureQuestion[];
  const erros: { id: number; area: string; enunciado: string; escolhida: number | null }[] = [];
  let acertos = 0;
  for (const q of questions) {
    const chosen = respostas[String(q.id)];
    if (chosen === q.correta) acertos += 1;
    else erros.push({ id: q.id, area: q.area, enunciado: q.enunciado, escolhida: chosen ?? null });
  }
  const record: AttemptRecord = { tarefa_hash: f.tarefa.hash, numero, respostas, acertos, total: questions.length, aprovado: acertos >= f.minimo_aprovacao, criada_em: nowIso(), salt: newSalt() };
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
  /* LeIA: visible preparation. How many of the 14 steps started and finished; externa = produced by the external flow (no steps) */
  etapas_iniciadas: number; etapas_feitas: number; externa: boolean;
};

/* LeIA: the 14 workflow steps in pt-BR (docs/API-V3-CONTRACT.md, "Preparação visível e tarefas do fluxo externo") and the
   seconds each one reports once finished (illustrative; the simulated pipeline is faster than the real one) */
export const STEP_NAMES = ["Identificar as partes", "Datas e valores", "Fatos", "Fundamentos, leis e decisões", "Pedidos", "Juntar a memória", "Resumir os fatos", "Resumir os fundamentos", "Resumir os pedidos", "Quem é quem", "Contexto do processo", "Marcar o texto", "Explicar em linguagem simples", "Preparar as perguntas"];
const STEP_SECONDS = [3, 4, 5, 6, 4, 2, 5, 5, 4, 3, 4, 6, 9, 7];
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
  const finished = { etapas_iniciadas: STEP_TOTAL, etapas_feitas: STEP_TOTAL, externa: false };
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
  /* LeIA: external flow. The lawyer's panel sent the PDF to the external API: summary and marked topics with score, no
     questions, no local steps. Already released so the citizen link opens the "no questions" journey. */
  tasks.set(EXTERNAL_DEMO_HASH, {
    id: 3, hash: EXTERNAL_DEMO_HASH, titulo: EXT.tarefa.titulo, status: "enviada", criada_em: ts, atualizada_em: ts, origem: "advogado", dono_id: 1, cidadao_id: null, ready_at: 0,
    eventos: [{ tipo: "criada", ts }, { tipo: "resumo_estruturado", ts }, { tipo: "aprovada", ts }], tentativas: [], duvidas: [],
    etapas_iniciadas: 0, etapas_feitas: 0, externa: true,
  });
  return { users, tasks, seq: { user: 2, task: 3, doubt: 1 } };
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
/* the 14 steps as the public route reports them; an external task has none */
export function stagesOf(t: MockTask): Stage[] {
  if (t.externa) return [];
  return STEP_NAMES.map((nome, i) => {
    const estado: Stage["estado"] = i < t.etapas_feitas ? "concluida" : i < t.etapas_iniciadas ? (t.status === "falhou" ? "erro" : "em_andamento") : "pendente";
    return estado === "concluida" ? { id: `T${i + 1}`, nome, estado, tempo: STEP_SECONDS[i] } : { id: `T${i + 1}`, nome, estado };
  });
}

/* status settles with time: created -> processing after 1s -> ready after PIPELINE_MS.
   LeIA: while processing, the 14 steps advance one every STEP_MS so the wait screen can show them. */
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
const publicUser = (u: MockUser) => ({ id: u.id, nome: u.nome, email: u.email, papel: u.papel });
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
  const user: MockUser = { id: ++s.seq.user, nome, email, papel, oab: input.oab ? String(input.oab) : null, senha_hash: hashPassword(senha), token: newSalt() };
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
    eventos: [{ tipo: "criada", ts }], tentativas: [], duvidas: [], etapas_iniciadas: 0, etapas_feitas: 0, externa: false,
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
    link_cliente: clientLink(t), resumo_md: hasContent(t) ? contentOf(t).resumo_md : null, eventos: t.eventos.slice(-20),
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
export function publicGate(hash: string): Response | null {
  const t = storeTask(hash);
  if (!t) return Response.json({ detail: "não encontrado" }, { status: 404 });
  if (inReview(t)) return Response.json({ detail: "Em revisão pelo advogado" }, { status: 409 });
  if (!isReleased(t)) return Response.json({ detail: "ainda não está pronta" }, { status: 409 });
  return null;
}
/* LeIA: the external flow's classes (classe_partes, classe_datas_valores, ...) with a colour each */
const EXTERNAL_CLASSES: Record<string, { rotulo: string; cor: string }> = {
  partes: { rotulo: "Partes", cor: "#E3F1F1" }, datas_valores: { rotulo: "Datas e valores", cor: "#FFF4DD" }, fatos: { rotulo: "Fatos", cor: "#EDE7F6" },
  fundamentos: { rotulo: "Fundamentos, leis e decisões", cor: "#E8F5E9" }, pedidos: { rotulo: "Pedidos", cor: "#FDE7EF" },
};
/* the fixture's clauses become tagged items over the extracted text (same body as GET /api/t/{hash}/inferencias).
   LeIA: partial = while the pipeline runs (docs/API-V3-CONTRACT.md, "Preparação visível"): no text before extraction and only
   the items the finished steps would have produced, with parcial: true. External tasks group the items by class and carry the score. */
export function buildInferences(t: MockTask, partial = false): Inferences {
  const f = contentOf(t);
  const texto = partial && t.status === "criada" ? "" : f.documento_texto.map((c) => c.texto).join("\n\n");
  const visible = partial ? f.topicos.slice(0, Math.min(f.topicos.length, t.etapas_feitas)) : f.topicos;
  const classes: InferenceClass[] = [];
  const classFor = (key: string, rotulo: string, cor: string) => { let c = classes.find((x) => x.classe === key); if (!c) { c = { classe: key, rotulo, cor, itens: [] }; classes.push(c); } return c; };
  const refs: string[] = [];
  visible.forEach((tp) => {
    const key = t.externa ? tp.classe ?? "outros" : "clausulas";
    const meta = t.externa ? EXTERNAL_CLASSES[key] ?? { rotulo: key, cor: "#F1EFEA" } : { rotulo: "Cláusulas explicadas", cor: "#E3F1F1" };
    const c = classFor(key, meta.rotulo, meta.cor);
    const ref = `${key}[${c.itens.length}]`; refs.push(ref);
    const pos = texto ? findSpan(texto, tp.trecho) : null;
    const item = { ref, campo: t.externa ? tp.titulo : `cláusula ${tp.clausula}`, valor: t.externa ? tp.explicacao : tp.titulo, trecho: tp.trecho, pos, conferido: !!pos, cor: meta.cor };
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
    inferencias: buildInferences(t), resumo_md: contentOf(t).resumo_md,
    questoes: (contentOf(t).questoes.questoes as FixtureQuestion[]).map((q) => ({ id: q.id, area: q.area, dificuldade: q.dificuldade, enunciado: q.enunciado, alternativas: q.alternativas, correta: q.correta, justificativa: q.justificativa })),
    link_cliente: clientLink(t),
  };
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
  return { advogado: lawyerOf(t), tem_advogado: t.origem === "advogado", cidadao_vinculado: t.cidadao_id !== null, duvidas_enviadas: t.duvidas.length, ultima_tentativa: lastAttempt(t) };
}
/* while the pipeline runs the public payload carries no content, like the service */
export function publicTaskFor(hash: string) {
  const t = storeTask(hash); const f = findTask(hash);
  if (!t || !f) return null;
  const base = publicTask(f);
  /* LeIA: review gate. A lawyer-owned task in "pronta" answers "revisao" with no content until the lawyer approves. */
  /* LeIA: visible preparation. etapas with the 14 steps and every pipeline event (up to 60), like the service. */
  const progress = { etapas: stagesOf(t), eventos: t.eventos.slice(-60) };
  if (inReview(t)) return { ...base, tarefa: { ...base.tarefa, status: "revisao" }, resumo_md: null, topicos: null, questoes: [], sem_perguntas: false, ...progress, ...publicTaskMeta(t) };
  const ready = isReleased(t);
  return { ...base, resumo_md: ready ? base.resumo_md : "", topicos: ready ? base.topicos : null, questoes: ready ? base.questoes : [], sem_perguntas: ready && base.sem_perguntas, ...progress, ...publicTaskMeta(t) };
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
  if (t.cidadao_id === null) { t.cidadao_id = u.id; t.atualizada_em = nowIso(); t.eventos.push({ tipo: "cidadao_vinculado", ts: t.atualizada_em }); }
  return { ok: true };
}
export const isAuthError = (e: unknown): e is AuthError => typeof e === "object" && e !== null && "status" in e && "detail" in e;
export function errorResponse(e: unknown) {
  if (isAuthError(e)) return Response.json({ detail: e.detail }, { status: e.status });
  return Response.json({ detail: "erro interno" }, { status: 500 });
}
