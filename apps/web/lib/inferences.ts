/* Inferences over the original text: quote positions found by whitespace-insensitive substring search.
   Mirrors leia/api_cliente.py (build_inferences) so the in-app mock and the service agree. */
/* LeIA: como o servidor achou o trecho no documento. O modelo não conta caractere, então a posição que ele
   escreve é palpite com cara de fato; quem localiza é o serviço (leia/api_citizen.py, locate). */
export type AnchorMethod = "exato" | "normalizado" | "aproximado";
export type Anchor = { metodo: AnchorMethod; score: number };

/* O que a tela pode afirmar sobre o trecho. Sem conferência, nada: afirmar cópia exata de algo que não foi
   procurado no documento é justamente a mentira que este produto não pode contar. */
export function anchorClaim(anchor?: Anchor | null): string | null {
  if (!anchor) return null;
  if (anchor.metodo === "aproximado") return "Trecho conferido no seu documento, com pequenas diferenças de digitação.";
  return "Trecho conferido: copiado exatamente do seu documento.";
}

/* LeIA: score comes from the external flow ("_ui.score_trecho_verbatim"), 0..1 or 0..100; absent on the local pipeline */
export type InferenceItem = { ref: string; campo: string | null; valor: string | null; trecho: string; pos: [number, number] | null; conferido: boolean; cor: string; pagina?: string | null; score?: number; conferencia?: Anchor };
export type InferenceClass = { classe: string; rotulo: string; cor: string; itens: InferenceItem[] };
export type Synthesis = { classe: string; rotulo: string; texto: string; lastro: string[] };
/* LeIA: parcial = answered while the pipeline runs (docs/API-V3-CONTRACT.md, "Preparação visível"): texto may still be empty
   and classes holds only what the workflow produced so far */
export type Inferences = { tarefa: { hash: string; titulo: string }; texto: string; classes: InferenceClass[]; sinteses: Synthesis[]; total: number; conferidos: number; parcial?: boolean };

function normMap(text: string): { norm: string; idx: number[] } {
  const out: string[] = []; const idx: number[] = []; let prevSpace = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (/\s/.test(ch)) { if (!prevSpace) { out.push(" "); idx.push(i); } prevSpace = true; }
    else { out.push(ch); idx.push(i); prevSpace = false; }
  }
  return { norm: out.join(""), idx };
}

export function findSpan(text: string, quote: string): [number, number] | null {
  const q = (quote || "").split(/\s+/).join(" ").trim();
  if (q.length < 3) return null;
  const { norm, idx } = normMap(text);
  let pos = norm.indexOf(q);
  if (pos < 0) { pos = norm.toLowerCase().indexOf(q.toLowerCase()); if (pos < 0) return null; }
  return [idx[pos], idx[pos + q.length - 1] + 1];
}
