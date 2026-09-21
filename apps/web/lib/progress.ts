/* Quantas buscas estão em curso, e quem quer saber disso.
 *
 * Existe porque a barra do topo precisa de um ponto único por onde toda busca passa, e `lib/api.ts` tinha
 * dezenove `fetch` soltos. Com isso, quem acrescentar a vigésima chamada ganha a barra sem precisar lembrar
 * dela — que é a única forma de um indicador global continuar verdadeiro com o tempo.
 *
 * Contador, e não booleano: duas buscas simultâneas terminando uma antes da outra apagariam a barra com a
 * segunda ainda rodando. */

type Ouvinte = (emCurso: number) => void;

let emCurso = 0;
const ouvintes = new Set<Ouvinte>();

function avisar() {
  for (const o of ouvintes) o(emCurso);
}

export function assinarProgresso(o: Ouvinte): () => void {
  ouvintes.add(o);
  o(emCurso);
  return () => { ouvintes.delete(o); };
}

/** Marca o começo de algo demorado que não é uma busca, como a troca de rota. */
export function comecou(): () => void {
  emCurso += 1;
  avisar();
  let fechado = false;
  return () => {
    /* Idempotente: quem devolve este fechamento pode chamá-lo na limpeza de um efeito e de novo no fim do
       trabalho, e o contador não pode ficar negativo por isso. */
    if (fechado) return;
    fechado = true;
    emCurso = Math.max(0, emCurso - 1);
    avisar();
  };
}

/** `fetch` com o contador em volta. É o que `lib/api.ts` usa no lugar de `fetch`. */
export async function busca(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const fim = comecou();
  try {
    return await fetch(input, init);
  } finally {
    fim();
  }
}
