/* Um conteúdo principal, um destino para o atalho.
 *
 * Antes, `Page` e `DocsShell` criavam cada um o seu `<main>`, e a landing criava um terceiro. Numa página
 * que usasse dois deles, o leitor de tela oferecia "ir para o conteúdo principal" e a pessoa não tinha como
 * saber qual dos dois ia receber. O mesmo vale para o `id` do atalho: dois iguais na mesma página fazem o
 * navegador escolher o primeiro, que não é necessariamente o que quem escreveu o link tinha em mente.
 *
 * Como em `error-screen.test.ts`, isto lê o código-fonte porque não há renderizador de DOM aqui. Prova que
 * ninguém criou um segundo marco; não prova que o primeiro está no lugar certo da tela.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const RAIZ = join(__dirname, "..");

function telas(dir: string, achados: string[] = []): string[] {
  for (const nome of readdirSync(dir)) {
    const caminho = join(dir, nome);
    if (nome === "node_modules" || nome === ".next") continue;
    if (statSync(caminho).isDirectory()) telas(caminho, achados);
    else if (nome.endsWith(".tsx")) achados.push(caminho);
  }
  return achados;
}

/* Sem comentário: este arquivo explica em prosa o que ele proíbe em código, e os comentários citam tanto
   `<main>` quanto o `id` do atalho. Sem tirar comentário, o teste acusa a própria documentação. */
const semComentario = (fonte: string) =>
  fonte.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const FONTES = [...telas(join(RAIZ, "app")), ...telas(join(RAIZ, "components"))]
  .map((caminho) => [caminho.slice(RAIZ.length + 1), semComentario(readFileSync(caminho, "utf8"))] as const);

describe("os marcos da página", () => {
  it("só o layout raiz cria <main>", () => {
    const criam = FONTES
      /* `global-error.tsx` desenha o documento inteiro sozinho quando o layout raiz falhou, então o `<main>`
         dela é o único da página naquele momento. É exceção pelo mesmo motivo que ela não importa nada do
         produto. */
      .filter(([nome]) => nome !== "app/global-error.tsx")
      .filter(([, fonte]) => /<main[\s>]/.test(fonte))
      .map(([nome]) => nome);
    expect(criam, "cada `<main>` a mais é um destino a mais para o mesmo atalho do leitor de tela")
      .toEqual(["app/layout.tsx"]);
  });

  it("o alvo do atalho existe uma vez só", () => {
    const alvos = FONTES.filter(([, fonte]) => /id="conteudo"/.test(fonte)).map(([nome]) => nome);
    expect(alvos).toEqual(["app/layout.tsx"]);
  });

  it("todo atalho aponta para um alvo que existe", () => {
    const ids = new Set(FONTES.flatMap(([, fonte]) => [...fonte.matchAll(/id="([a-z-]+)"/g)].map((m) => m[1])));
    const destinos = FONTES.flatMap(([nome, fonte]) =>
      [...fonte.matchAll(/href="#([a-z-]+)"/g)].map((m) => [nome, m[1]] as const));
    const quebrados = destinos.filter(([, alvo]) => !ids.has(alvo));
    expect(quebrados, "atalho que aponta para id inexistente não leva a lugar nenhum e não avisa")
      .toEqual([]);
  });
});
