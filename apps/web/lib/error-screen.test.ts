/* As duas telas de erro, e a regra que não pode se perder nelas.
 *
 * Não há renderizador de DOM neste projeto, então isto lê o código-fonte. É uma aproximação, e vale dizer o
 * que ela prova e o que não prova: ela **não** garante que a tela renderiza bonito, e **garante** que
 * ninguém colocou a mensagem crua da exceção nela, que é a regressão que importa. A mensagem da exceção é
 * escrita para quem mantém o serviço e costuma carregar caminho de arquivo, nome de coluna e pedaço de
 * consulta; quem lê essa tela é alguém com medo de um documento jurídico.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const APP = join(__dirname, "..", "app");
const ler = (nome: string) => readFileSync(join(APP, nome), "utf8");

describe("as telas de erro", () => {
  it.each(["error.tsx", "global-error.tsx"])("%s não mostra a mensagem crua da exceção", (arquivo) => {
    const fonte = ler(arquivo);
    expect(fonte, "a mensagem da exceção é para o log, nunca para a tela")
      .not.toMatch(/error\.message/);
    /* O `digest` pode e deve aparecer: é um resumo que o Next gera para ligar o que a pessoa viu ao que
       ficou no log do servidor, e é o que ela informa se precisar falar com alguém. */
    expect(fonte).toMatch(/error\.digest/);
  });

  it.each(["error.tsx", "global-error.tsx"])("%s oferece tentar de novo e uma saída", (arquivo) => {
    const fonte = ler(arquivo);
    expect(fonte, "sem `reset` a pessoa fica presa na tela de erro").toMatch(/reset\b/);
    expect(fonte, "sem saída para o início, o único caminho é o botão de voltar do navegador")
      .toMatch(/href="\/"/);
  });

  it("global-error.tsx não depende de nada do produto", () => {
    /* Ela substitui o layout raiz. Se o que quebrou foi o layout, a fonte ou o CSS global, importar o kit
       de componentes aqui é pedir para a tela de erro quebrar junto com o erro que ela veio explicar. */
    const fonte = ler("global-error.tsx");
    expect(fonte, "importar do produto aqui é apostar que o produto está de pé, que é justamente a dúvida")
      .not.toMatch(/from "@\//);
    expect(fonte, "ela desenha o documento inteiro, então precisa de <html> e <body>").toMatch(/<html/);
    expect(fonte).toMatch(/<body/);
  });
});
