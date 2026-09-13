/* Registry primitives, same field names and canonicalization as apps/llm-service/leia/registry.py,
   so the Python service and this TypeScript mock produce identical hashes for identical attempts. */
import { createHash, randomBytes } from "node:crypto";

export const PAYLOAD_SCHEMA = "leia.payload.v1";

type Json = string | number | boolean | null | Json[] | { [k: string]: Json };
function sortKeys(v: Json): Json {
  if (Array.isArray(v)) return v.map(sortKeys);
  if (v && typeof v === "object") return Object.fromEntries(Object.keys(v).sort().map((k) => [k, sortKeys((v as { [k: string]: Json })[k])]));
  return v;
}
/* Sorted keys, no whitespace, UTF-8 kept: equals Python json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False). */
export const canonical = (obj: Json) => JSON.stringify(sortKeys(obj));
export const sha256 = (s: string) => createHash("sha256").update(s, "utf8").digest("hex");
export const nowIso = () => new Date().toISOString().replace(/\.\d{3}Z$/, "Z");

export type AttemptRecord = { tarefa_hash: string; numero: number; respostas: Record<string, number>; acertos: number; total: number; aprovado: boolean; criada_em: string; salt: string };

export function attemptHash(a: AttemptRecord): string {
  return sha256(canonical({ tarefa: a.tarefa_hash, numero: a.numero, respostas: a.respostas, criada_em: a.criada_em }));
}

export function buildPayload(a: AttemptRecord) {
  return {
    schema: PAYLOAD_SCHEMA, documentToken: a.tarefa_hash, attemptRound: a.numero, attemptSha256: attemptHash(a),
    documentSha256: "", summarySha256: "", understood: a.aprovado, answered: a.total, createdAt: a.criada_em, salt: a.salt,
  };
}

export const newSalt = () => randomBytes(20).toString("hex");

/* Stateless receipt token for the hosted demo: the attempt record travels in the URL, the hash is recomputed. */
export function encodeToken(a: AttemptRecord): string {
  const compact = { h: a.tarefa_hash, n: a.numero, r: Object.entries(a.respostas).sort(([x], [y]) => Number(x) - Number(y)).map(([k, v]) => `${k}:${v}`).join(","), a: a.acertos, t: a.total, ok: a.aprovado, c: a.criada_em, s: a.salt };
  return Buffer.from(JSON.stringify(compact), "utf8").toString("base64url");
}
export function decodeToken(token: string): AttemptRecord | null {
  try {
    const c = JSON.parse(Buffer.from(token, "base64url").toString("utf8"));
    const respostas: Record<string, number> = {};
    for (const pair of String(c.r || "").split(",").filter(Boolean)) { const [k, v] = pair.split(":"); respostas[k] = Number(v); }
    if (typeof c.h !== "string" || typeof c.s !== "string" || typeof c.c !== "string") return null;
    return { tarefa_hash: c.h, numero: Number(c.n), respostas, acertos: Number(c.a), total: Number(c.t), aprovado: Boolean(c.ok), criada_em: c.c, salt: c.s };
  } catch { return null; }
}
