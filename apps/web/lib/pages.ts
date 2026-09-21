/* O documento tem páginas, e a tela precisa saber quais.
 *
 * O extrator escreve `===== PÁGINA n =====` entre as folhas (`apps/llm-service/core/pdf_extract.py`), e
 * essa informação estava no texto sem ninguém usá-la. Ela importa por um motivo só: o produto diz "isto
 * está no seu documento", e sem o número da página a pessoa tem que varrer catorze folhas atrás de uma
 * frase para conferir. Afirmação que é cara demais de checar não é conferível na prática.
 *
 * Documento sem separador devolve `null`, nunca `1`. Dizer "página 1" num texto que não tem marcação
 * nenhuma seria inventar o dado que este módulo existe para trazer.
 */

const SEPARADOR = /=+ *P[ÁA]GINA (\d+) *=+/g;

/* `inicio` é o do separador e `conteudoInicio` o da primeira letra da folha. Os dois existem porque servem
   a coisas diferentes: `pageOf` usa `inicio` para decidir a qual folha uma posição pertence, e quem desenha
   a marcação usa `conteudoInicio` para converter posição do documento em posição dentro da folha. */
export type Folha = { numero: number | null; texto: string; inicio: number; conteudoInicio: number; fim: number };

/** As folhas do documento, com o número, o texto sem o separador e onde cada uma começa e termina. */
export function splitPages(documento: string): Folha[] {
  const marcas = [...(documento || "").matchAll(SEPARADOR)];
  if (marcas.length === 0) {
    return [{ numero: null, texto: documento || "", inicio: 0, conteudoInicio: 0, fim: (documento || "").length }];
  }
  return marcas.map((m, i) => {
    /* O conteúdo da folha começa depois do separador e vai até o separador seguinte. O `inicio` guardado é
       o do separador, e não o do conteúdo, porque é ele que `pageOf` usa para decidir a qual folha uma
       posição pertence: quem cair em cima do separador pertence à folha que ele abre. */
    const inicio = m.index ?? 0;
    const fim = i + 1 < marcas.length ? (marcas[i + 1].index ?? documento.length) : documento.length;
    const conteudoInicio = inicio + m[0].length;
    /* Sem `trim`: o texto da folha é a fatia crua do documento, porque é contra as posições do documento
       que as marcações são desenhadas. Aparar aqui deslocaria toda marcação daquela folha. */
    return { numero: Number(m[1]), texto: documento.slice(conteudoInicio, fim), inicio, conteudoInicio, fim };
  });
}

/** Em que página está esta posição do texto, ou `null` quando não dá para saber. */
export function pageOf(documento: string, posicao: number): number | null {
  if (!documento || posicao < 0 || posicao > documento.length) return null;
  const folhas = splitPages(documento);
  if (folhas.length === 1 && folhas[0].numero === null) return null;
  for (const f of folhas) if (posicao >= f.inicio && posicao < f.fim) return f.numero;
  return folhas[folhas.length - 1].numero;
}

/** "Página 3 de 14", ou `null` quando o documento não diz. Uma frase só, para a tela não montar a sua. */
export function pageLabel(documento: string, posicao: number): string | null {
  const n = pageOf(documento, posicao);
  if (n === null) return null;
  const total = splitPages(documento).length;
  return total > 1 ? `Página ${n} de ${total}` : `Página ${n}`;
}
