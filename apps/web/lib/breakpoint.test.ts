/* O produto tem um ponto de virada, e só um.
 *
 * Antes eram 46 usos de `sm:`, `md:` e `lg:` em 11 arquivos, escolhidos um a um. Com cinco larguras
 * disponíveis, ninguém conseguia responder "o que esta tela faz em 768 px" sem abrir os onze. A escala
 * padrão do Tailwind foi zerada em `app/tokens.css` e ficou `wide:`, em 1024 px.
 *
 * Zerar a escala não é defesa suficiente: no Tailwind v4, uma variante que não existe **não gera erro**, ela
 * simplesmente não produz regra nenhuma. Quem escrever `md:grid-cols-2` por hábito vê a classe no HTML, não
 * vê estilo nenhum, e não vê aviso. Este teste é o aviso.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const RAIZ = join(__dirname, "..");
const ESCALA_PADRAO = /\b(?:sm|md|lg|xl|2xl):/;

function arquivosDeTela(dir: string, achados: string[] = []): string[] {
  for (const nome of readdirSync(dir)) {
    const caminho = join(dir, nome);
    if (nome === "node_modules" || nome === ".next") continue;
    if (statSync(caminho).isDirectory()) arquivosDeTela(caminho, achados);
    else if (nome.endsWith(".tsx")) achados.push(caminho);
  }
  return achados;
}

describe("o ponto de virada", () => {
  it("é declarado uma vez em tokens.css, e a escala padrão está zerada", () => {
    const css = readFileSync(join(RAIZ, "app", "tokens.css"), "utf8");
    expect(css, "a escala padrão do Tailwind precisa ser zerada, senão sm/md/lg continuam valendo")
      .toContain("--breakpoint-*: initial");
    expect(css).toMatch(/--breakpoint-wide:\s*1024px/);
    /* Um, e não dois: a tentação é acrescentar "só mais um" para um caso específico, e é assim que se volta
       a cinco. Ponto de virada novo é decisão de projeto e passa por aqui. */
    expect(css.match(/--breakpoint-(?!\*)[a-z0-9-]+:/g) ?? []).toHaveLength(1);
  });

  it("o CSS escrito à mão não abre um segundo ponto de virada", () => {
    /* Zerar a escala do Tailwind não alcança consulta de mídia escrita à mão. O `/docs` trocava tabela por
       cartão em 639 px, que era uma segunda virada escondida num arquivo que ninguém liga a layout: a régua
       dizia uma e eram duas. Consulta de mídia não lê variável de CSS, então o número fica escrito, e é
       esta linha que garante que ele é o mesmo. */
    const larguras = new Set<string>();
    for (const arquivo of ["globals.css", "tokens.css"]) {
      const css = readFileSync(join(RAIZ, "app", arquivo), "utf8");
      for (const m of css.matchAll(/@media[^{]*?(?:min|max)-width:\s*([0-9.]+(?:px|rem))/g)) larguras.add(m[1]);
    }
    expect([...larguras].sort(), "toda virada tem que ser a do token: 1024px, ou 1023px quando a consulta é max-width")
      .toEqual(["1023px"]);
  });

  it("nenhuma tela usa a escala que foi zerada", () => {
    const culpados = arquivosDeTela(join(RAIZ, "components"))
      .concat(arquivosDeTela(join(RAIZ, "app")))
      .filter((caminho) => ESCALA_PADRAO.test(readFileSync(caminho, "utf8")))
      .map((caminho) => caminho.slice(RAIZ.length + 1));
    expect(culpados, `estes arquivos usam sm:/md:/lg:, que não produzem estilo nenhum desde que a escala foi zerada:\n  ${culpados.join("\n  ")}`)
      .toEqual([]);
  });
});
