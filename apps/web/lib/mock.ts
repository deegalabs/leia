/* In-app mock of the cognitive service (same routes and shapes as apps/llm-service/mock/app.py), used when
   NEXT_PUBLIC_API_BASE is empty, e.g. on the hosted demo. Stateless: receipts travel as tokens. */
import fixture from "@/data/fixture-honorarios.json";
import { attemptHash, buildPayload, canonical, encodeToken, newSalt, nowIso, sha256, type AttemptRecord } from "./registry";
import { findSpan, type Inferences } from "./inferences"; /* LeIA: review flow shares the inferences with the public route */

type FixtureQuestion = { id: number; area: string; dificuldade: string; enunciado: string; alternativas: string[]; correta: number; justificativa: string };
type Fixture = typeof fixture;
const F: Fixture = fixture;

/* LeIA: v3 tasks live in the in-memory store; each one reuses the fixture content as if the pipeline finished. */
export function findTask(hash: string) {
  const t = storeTask(hash);
  if (!t) return null;
  return { ...F, tarefa: { ...F.tarefa, id: t.id, hash: t.hash, titulo: t.titulo, status: t.status } } as Fixture;
}

export function publicTask(f: Fixture) {
  return {
    tarefa: f.tarefa, resumo_md: f.resumo_md, topicos: f.topicos,
    questoes: (f.questoes.questoes as FixtureQuestion[]).map((q) => ({ id: q.id, enunciado: q.enunciado, alternativas: q.alternativas, area: q.area })),
    ultima_tentativa: null,
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
  if (best && score >= 2) return `${best.explicacao} O documento diz: "${best.trecho}" (cláusula ${best.clausula}).`;
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
};
type Store = { users: Map<number, MockUser>; tasks: Map<string, MockTask>; seq: { user: number; task: number; doubt: number } };

const PIPELINE_MS = 8000;
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
  tasks.set(F.tarefa.hash, {
    id: F.tarefa.id, hash: F.tarefa.hash, titulo: F.tarefa.titulo, status: "enviada", criada_em: ts, atualizada_em: ts, origem: "advogado", dono_id: 1, cidadao_id: null, ready_at: 0,
    eventos: [{ tipo: "criada", ts }, { tipo: "pipeline_concluido", ts }, { tipo: "aprovada", ts }], tentativas: [],
    duvidas: [{ id: 1, texto: "Se eu perder a ação, ainda pago os 20%?", contexto: [{ role: "user", text: "Se eu perder a ação, ainda pago os 20%?" }, { role: "bot", text: "O documento diz que os 20% incidem sobre o valor efetivamente recebido na ação." }], criada_em: ts, respondida: false, resposta: null, respondida_em: null }],
  });
  tasks.set(REVIEW_DEMO_HASH, {
    id: 2, hash: REVIEW_DEMO_HASH, titulo: "Contrato de honorários: ação de cobrança", status: "pronta", criada_em: ts, atualizada_em: ts, origem: "advogado", dono_id: 1, cidadao_id: null, ready_at: 0,
    eventos: [{ tipo: "criada", ts }, { tipo: "pipeline_concluido", ts }], tentativas: [], duvidas: [],
  });
  return { users, tasks, seq: { user: 2, task: 2, doubt: 1 } };
}
const g = globalThis as unknown as { __leiaMockStore?: Store };
const store = (): Store => (g.__leiaMockStore ??= seed());

/* status settles with time: created -> processing after 1s -> ready after PIPELINE_MS */
function settle(t: MockTask): MockTask {
  const now = Date.now();
  if (t.status === "criada" && now >= t.ready_at - PIPELINE_MS + 1000) { t.status = "processando"; t.atualizada_em = nowIso(); t.eventos.push({ tipo: "extracao_texto", ts: t.atualizada_em }); }
  if (t.status === "processando" && now >= t.ready_at) { t.status = "pronta"; t.atualizada_em = nowIso(); t.eventos.push({ tipo: "pipeline_concluido", ts: t.atualizada_em }); }
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
  const h = req.headers.get("authorization") ?? "";
  const token = h.toLowerCase().startsWith("bearer ") ? h.slice(7).trim() : "";
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
    eventos: [{ tipo: "criada", ts }], tentativas: [], duvidas: [],
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
    link_cliente: clientLink(t), resumo_md: hasContent(t) ? F.resumo_md : null, eventos: t.eventos.slice(-20),
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
/* the fixture's clauses become tagged items over the extracted text (same body as GET /api/t/{hash}/inferencias) */
export function buildInferences(t: MockTask): Inferences {
  const texto = F.documento_texto.map((c) => c.texto).join("\n\n");
  const itens = F.topicos.map((tp, n) => {
    const pos = findSpan(texto, tp.trecho);
    return { ref: `clausulas[${n}]`, campo: `cláusula ${tp.clausula}`, valor: tp.titulo, trecho: tp.trecho, pos, conferido: !!pos, cor: "#E3F1F1" };
  });
  return {
    tarefa: { hash: t.hash, titulo: t.titulo },
    texto,
    classes: [{ classe: "clausulas", rotulo: "Cláusulas explicadas", cor: "#E3F1F1", itens }],
    sinteses: F.topicos.map((tp, n) => ({ classe: "clausulas", rotulo: tp.titulo, texto: tp.explicacao, lastro: [`clausulas[${n}]`] })),
    total: itens.length, conferidos: itens.filter((i) => i.conferido).length,
  };
}
export function review(u: MockUser, id: number) {
  const t = storeTaskById(id);
  if (!t) throw fail(404, "não encontrado");
  if (!canManage(u, t)) throw fail(403, "sem acesso");
  if (!hasContent(t)) throw fail(409, t.status === "falhou" ? "a explicação não pôde ser preparada" : "ainda não está pronta");
  return {
    tarefa: { id: t.id, hash: t.hash, titulo: t.titulo, status: t.status, origem: t.origem },
    inferencias: buildInferences(t), resumo_md: F.resumo_md,
    questoes: (F.questoes.questoes as FixtureQuestion[]).map((q) => ({ id: q.id, area: q.area, dificuldade: q.dificuldade, enunciado: q.enunciado, alternativas: q.alternativas, correta: q.correta, justificativa: q.justificativa })),
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
  if (inReview(t)) return { ...base, tarefa: { ...base.tarefa, status: "revisao" }, resumo_md: null, topicos: null, questoes: [], eventos: t.eventos, ...publicTaskMeta(t) };
  const ready = isReleased(t);
  return { ...base, resumo_md: ready ? base.resumo_md : "", topicos: ready ? base.topicos : null, questoes: ready ? base.questoes : [], eventos: t.eventos, ...publicTaskMeta(t) };
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
