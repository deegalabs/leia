/* O lugar da cidadã na jornada, guardado no aparelho dela.
 *
 * Antes só `answers` e `result` eram guardados, e a etapa começava sempre no início. Sair da página, e sair
 * é fácil (ver o documento marcado é navegação inteira, e aba de celular básico morre por falta de memória),
 * custava tocar "Entendi, próximo" tantas vezes quantos pontos ela já tinha lido, relendo tudo. Para quem lê
 * com esforço e está com medo, recomeçar é motivo para desistir. */

export type Step =
  | { kind: "welcome" }
  | { kind: "topic"; n: number }
  | { kind: "question"; k: number }
  | { kind: "result" }
  | { kind: "done" };

export type Answers = Record<string, number>;
export type Saved<R> = { answers: Answers; result: R | null; step: Step };
export type Bounds = { topics: number; questions: number };

/** A etapa cabe no documento que está aberto. Documento reprocessado tem outro número de pontos, e mandar
 *  a pessoa para o ponto 8 de um documento com 3 é pior que mandar para o começo. */
export function fitsStep(step: Step, b: Bounds): boolean {
  if (step.kind === "topic") return Number.isInteger(step.n) && step.n >= 0 && step.n < b.topics;
  if (step.kind === "question") return Number.isInteger(step.k) && step.k >= 0 && step.k < b.questions;
  return step.kind === "welcome" || step.kind === "result" || step.kind === "done";
}

/** O que restaurar ao abrir o link de novo. Aceita o formato antigo, sem `step`, porque ele já está gravado
 *  no aparelho de quem começou antes desta mudança. */
export function restore<R extends { aprovado?: boolean }>(raw: string | null, b: Bounds): Partial<Saved<R>> {
  let saved: Partial<Saved<R>> | null = null;
  try { saved = raw ? JSON.parse(raw) : null; } catch { return {}; }
  if (!saved || typeof saved !== "object") return {};
  const out: Partial<Saved<R>> = {};
  if (saved.answers && typeof saved.answers === "object") out.answers = saved.answers;
  /* Só um resultado aprovado reabre na tela final: o link é compartilhado, e uma reprovação guardada aqui
     mandaria a próxima pessoa direto para "vamos ver de novo" sem ela ter respondido nada. */
  if (saved.result?.aprovado) { out.result = saved.result; out.step = { kind: "result" }; return out; }
  if (saved.step && fitsStep(saved.step, b)) out.step = saved.step;
  return out;
}

/** As respostas que sobrevivem a uma tentativa reprovada: as que ela acertou.
 *
 *  Apagar tudo fazia quem errou uma de três perder as duas certas. Não é mais seguro: o serviço já devolve
 *  quais foram erradas, então nada novo é revelado, e o teto de tentativas continua valendo igual. */
export function keptAfterRetry(answers: Answers, erros: { id: number }[]): Answers {
  const errados = new Set(erros.map((e) => String(e.id)));
  return Object.fromEntries(Object.entries(answers).filter(([id]) => !errados.has(id)));
}

/** A primeira pergunta ainda sem resposta, para ela retomar onde parou em vez de repassar pelas certas. */
export function firstUnanswered(questions: { id: number }[], answers: Answers): number {
  const i = questions.findIndex((q) => answers[String(q.id)] === undefined);
  return i < 0 ? 0 : i;
}
