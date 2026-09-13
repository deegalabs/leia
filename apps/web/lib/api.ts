/* Client for the cognitive service. Routes follow the service (see docs/LLM-API-CONTRACT.md).
   NEXT_PUBLIC_API_BASE empty = the in-app mock (app/api/*), used on the hosted demo. */
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "").replace(/\/$/, "");
export const usingInternalMock = API_BASE === "";

export type Topic = { id: number; titulo: string; explicacao?: string; explicacao_md?: string; trecho?: string; clausula?: string };
export type Question = { id: number; enunciado: string; alternativas: string[]; area?: string };
export type Attempt = { aprovado: boolean; hash_imutavel: string; acertos: number; total: number; numero?: number };
export type Task = {
  tarefa: { hash: string; titulo: string; status: string };
  resumo_md: string;
  topicos: Topic[] | null;
  questoes: Question[];
  ultima_tentativa: Attempt | null;
  eventos?: { tipo?: string; step?: string; ts?: string; [k: string]: unknown }[];
};
export type QuizResult = Attempt & { comprovante_token?: string; erros: { id: number; area?: string; enunciado?: string; escolhida?: number | null }[] };
export type VerifyResult = {
  payload: { schema: string; documentToken: string; attemptRound: number; attemptSha256: string; understood: boolean; answered: number; createdAt: string };
  canonical: string;
  payloadHash: string;
  otsPresent: boolean;
  demo?: boolean;
};

async function check(r: Response) {
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r;
}

export async function getTask(hash: string): Promise<Task> {
  const r = await check(await fetch(`${API_BASE}/api/t/${hash}`, { headers: { Accept: "application/json" }, cache: "no-store" }));
  return r.json();
}

export async function submitQuiz(hash: string, respostas: Record<string, number>): Promise<QuizResult> {
  const r = await check(await fetch(`${API_BASE}/api/t/${hash}/quiz`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ respostas }),
  }));
  return r.json();
}

/* SSE over fetch: "data: {t: '...'}" per token, "data: {error: '...'}" on failure. */
export async function chat(hash: string, mensagem: string, onText: (acc: string) => void): Promise<string> {
  const r = await check(await fetch(`${API_BASE}/api/t/${hash}/chat`, {
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
  const url = usingInternalMock ? `/api/verify/${attempt}` : `${API_BASE}/verify/${attempt}?format=json`;
  const r = await check(await fetch(url, { cache: "no-store" }));
  return r.json();
}

export const proofUrl = (attempt: string) => `${API_BASE}/verify/${attempt}/proof.ots`;
/* The professional's panel lives in the service; without a service there is no panel to link. */
export const panelUrl = (): string | null => (usingInternalMock ? null : `${API_BASE}/`);

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
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short", timeZone: "America/Sao_Paulo" }).format(d);
}
