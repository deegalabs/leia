/* In-app mock of the cognitive service (same routes and shapes as apps/llm-service/mock/app.py), used when
   NEXT_PUBLIC_API_BASE is empty, e.g. on the hosted demo. Stateless: receipts travel as tokens. */
import fixture from "@/data/fixture-honorarios.json";
import { attemptHash, buildPayload, canonical, encodeToken, newSalt, nowIso, sha256, type AttemptRecord } from "./registry";

type FixtureQuestion = { id: number; area: string; dificuldade: string; enunciado: string; alternativas: string[]; correta: number; justificativa: string };
type Fixture = typeof fixture;
const F: Fixture = fixture;

export function findTask(hash: string) {
  return hash === F.tarefa.hash ? F : null;
}

export function publicTask(f: Fixture) {
  return {
    tarefa: f.tarefa, resumo_md: f.resumo_md, topicos: f.topicos,
    questoes: (f.questoes.questoes as FixtureQuestion[]).map((q) => ({ id: q.id, enunciado: q.enunciado, alternativas: q.alternativas, area: q.area })),
    ultima_tentativa: null,
  };
}

export function evaluateQuiz(f: Fixture, respostas: Record<string, number>) {
  const questions = f.questoes.questoes as FixtureQuestion[];
  const erros: { id: number; area: string; enunciado: string; escolhida: number | null }[] = [];
  let acertos = 0;
  for (const q of questions) {
    const chosen = respostas[String(q.id)];
    if (chosen === q.correta) acertos += 1;
    else erros.push({ id: q.id, area: q.area, enunciado: q.enunciado, escolhida: chosen ?? null });
  }
  const record: AttemptRecord = { tarefa_hash: f.tarefa.hash, numero: 1, respostas, acertos, total: questions.length, aprovado: acertos >= f.minimo_aprovacao, criada_em: nowIso(), salt: newSalt() };
  return { aprovado: record.aprovado, acertos, total: record.total, numero: 1, hash_imutavel: attemptHash(record), comprovante_token: encodeToken(record), erros };
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
