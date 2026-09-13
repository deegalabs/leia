/* Inferences over the original text: quote positions found by whitespace-insensitive substring search.
   Mirrors leia/api_cliente.py (build_inferences) so the in-app mock and the service agree. */
export type InferenceItem = { ref: string; campo: string | null; valor: string | null; trecho: string; pos: [number, number] | null; conferido: boolean; cor: string };
export type InferenceClass = { classe: string; rotulo: string; cor: string; itens: InferenceItem[] };
export type Synthesis = { classe: string; rotulo: string; texto: string; lastro: string[] };
export type Inferences = { tarefa: { hash: string; titulo: string }; texto: string; classes: InferenceClass[]; sinteses: Synthesis[]; total: number; conferidos: number };

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
