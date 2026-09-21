/* Em que página do documento cada trecho está.
 *
 * "Está no seu documento" é uma afirmação que a pessoa precisa conseguir conferir no papel dela, e sem o
 * número da página ela tem que varrer catorze folhas atrás de uma frase. O extrator já escreve
 * `===== PÁGINA n =====` no texto (`core/pdf_extract.py`), então a informação existe e só não estava sendo
 * usada.
 */
import { describe, expect, it } from "vitest";

import { pageOf, splitPages } from "./pages";

const DOC = [
  "===== PÁGINA 1 =====", "", "CLÁUSULA 1. O CONTRATANTE contrata.", "",
  "===== PÁGINA 2 =====", "", "CLÁUSULA 2. Pagará vinte por cento.", "",
  "===== PÁGINA 3 =====", "", "Curitiba, 13 de setembro de 2026.",
].join("\n");

describe("a página de um trecho", () => {
  it("diz a página de cada posição", () => {
    expect(pageOf(DOC, DOC.indexOf("contrata"))).toBe(1);
    expect(pageOf(DOC, DOC.indexOf("vinte por cento"))).toBe(2);
    expect(pageOf(DOC, DOC.indexOf("Curitiba"))).toBe(3);
  });

  it("conta o separador como parte da página que ele abre", () => {
    expect(pageOf(DOC, DOC.indexOf("===== PÁGINA 2"))).toBe(2);
  });

  it("devolve null quando o documento não tem separador, em vez de chutar 1", () => {
    /* Documento antigo, extraído antes de o separador existir. Dizer "página 1" ali seria inventar uma
       informação que ninguém pode conferir, que é exatamente o que este produto não faz. */
    expect(pageOf("Um contrato sem marcação de página nenhuma.", 5)).toBeNull();
  });

  it("devolve null para posição fora do texto", () => {
    expect(pageOf(DOC, -1)).toBeNull();
    expect(pageOf(DOC, DOC.length + 10)).toBeNull();
  });

  it("separa o documento em folhas, com o número e o texto de cada uma", () => {
    const folhas = splitPages(DOC);
    expect(folhas.map((f) => f.numero)).toEqual([1, 2, 3]);
    expect(folhas[1].texto).toContain("vinte por cento");
    expect(folhas[1].texto).not.toContain("PÁGINA");
    /* A fatia é crua, sem aparar: é contra as posições do documento que a marcação é desenhada, e aparar
       aqui deslocaria toda marcação daquela folha. */
    expect(DOC.slice(folhas[1].conteudoInicio, folhas[1].fim)).toBe(folhas[1].texto);
    /* O deslocamento é o que liga a folha de volta ao documento inteiro: sem ele, a marcação de um trecho
       não sabe onde desenhar dentro da folha. */
    expect(DOC.slice(folhas[1].inicio, folhas[1].fim)).toContain("vinte por cento");
  });

  it("documento sem separador vira uma folha só, sem número", () => {
    const folhas = splitPages("Texto solto.");
    expect(folhas).toEqual([{ numero: null, texto: "Texto solto.", inicio: 0, conteudoInicio: 0, fim: 12 }]);
  });
});
