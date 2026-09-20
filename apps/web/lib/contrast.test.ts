/* O contraste do produto, medido a partir do arquivo que o produto usa.
 *
 * Contraste é a única parte da acessibilidade que se decide por conta, sem pessoa nenhuma para testar, e é
 * por isso que ela decai calada: alguém escurece um cinza "só um pouco" para a tela ficar mais leve e
 * ninguém percebe até chegar uma pessoa que não enxerga o texto. Este teste lê os tokens de
 * `app/tokens.css`, não uma cópia, e reprova o par que cair abaixo do piso.
 *
 * Os pisos são os da WCAG 2.2 AA: 4,5:1 para texto corrido, 3:1 para texto grande e para o que delimita um
 * controle (borda, anel de foco). O público deste produto inclui quem lê com esforço, então onde dá para
 * ficar acima do piso sem perder a marca, fica.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const CSS = readFileSync(join(__dirname, "..", "app", "tokens.css"), "utf8");

/** O valor de um token, lido do próprio arquivo. Token que sumir quebra aqui, que é o ponto. */
function token(nome: string): string {
  const m = CSS.match(new RegExp(`--${nome}:\\s*(#[0-9A-Fa-f]{6})`));
  if (!m) throw new Error(`token --${nome} não existe em app/tokens.css`);
  return m[1];
}

/** Luminância relativa da WCAG 2.x, com a correção de gama canal a canal. */
function luminancia(hex: string): number {
  const canais = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = canais.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contraste(frente: string, fundo: string): number {
  const [a, b] = [luminancia(frente), luminancia(fundo)];
  const razao = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
  return Math.round(razao * 100) / 100;
}

/* Cada par com o piso que ele precisa cumprir e onde ele aparece, porque piso sem lugar é número solto. */
const TEXTO: [string, string, string][] = [
  ["ink", "paper-2", "texto da jornada da cidadã"],
  ["ink", "surface", "texto dentro de cartão"],
  ["ink-2", "paper-2", "texto secundário da jornada"],
  ["ink-2", "surface", "texto secundário em cartão"],
  ["ink-3", "surface", "texto de apoio, o mais claro que o produto usa"],
  ["ink-3", "paper-2", "texto de apoio sobre o fundo da jornada, que é onde ele mais aparece"],
  ["teal-deep", "surface", "link e botão fantasma sobre cartão"],
  ["teal-deep", "paper-2", "link sobre o fundo da jornada"],
  ["teal-deep", "teal-soft", "link dentro de trecho destacado"],
  ["ink", "teal-soft", "texto dentro de trecho destacado"],
  ["ok", "ok-soft", "selo de conferido"],
  ["pend", "pend-soft", "selo de pendente"],
  ["danger", "danger-soft", "mensagem de erro"],
  ["paper", "navy", "texto sobre a marca"],
];

/* Não é texto: delimita controle ou estado. Piso 3:1 pela 1.4.11. */
const NAO_TEXTO: [string, string, string][] = [
  ["line-strong", "surface", "borda de campo dentro de cartão"],
  ["line-strong", "paper-2", "borda de campo sobre o fundo da jornada"],
  ["line-strong", "teal-soft", "borda de campo dentro de trecho destacado"],
  ["ink", "paper-2", "anel de foco sobre a jornada"],
];

describe("contraste dos tokens", () => {
  it.each(TEXTO)("%s sobre %s cumpre 4,5:1 (%s)", (frente, fundo, onde) => {
    const razao = contraste(token(`color-${frente}`), token(`color-${fundo}`));
    expect(razao, `${onde}: ${frente} ${token(`color-${frente}`)} sobre ${fundo} ${token(`color-${fundo}`)} deu ${razao}:1`).toBeGreaterThanOrEqual(4.5);
  });

  it.each(NAO_TEXTO)("%s sobre %s cumpre 3:1 (%s)", (frente, fundo, onde) => {
    const razao = contraste(token(`color-${frente}`), token(`color-${fundo}`));
    expect(razao, `${onde}: ${frente} sobre ${fundo} deu ${razao}:1`).toBeGreaterThanOrEqual(3);
  });

  it("o branco sobre o teal de ação cumpre 4,5:1, que é o botão principal do produto", () => {
    expect(contraste("#FFFFFF", token("color-teal-deep"))).toBeGreaterThanOrEqual(4.5);
  });

  it("o divisor é decoração e não pretende identificar controle", () => {
    /* `--color-line` dá 1,34:1 e está certo assim: ele separa cartão de fundo, não delimita nada que a
       pessoa opere. O que delimita controle é `--color-line-strong`, testado acima. Esta linha existe para
       que a distinção fique escrita: alguém que use o divisor numa borda de campo quebra o teste de cima. */
    expect(contraste(token("color-line"), token("color-surface"))).toBeLessThan(3);
  });

  it("o teal de marca continua proibido como fundo de texto branco", () => {
    /* Ele é bonito e não passa: 2,9:1. O token existe para fundo escuro e ícone, e esta linha existe para
       que alguém que o experimente num botão descubra aqui, e não numa pessoa. */
    expect(contraste("#FFFFFF", token("color-teal"))).toBeLessThan(4.5);
  });
});
