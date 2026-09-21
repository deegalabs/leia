"use client";
import { useSyncExternalStore } from "react";

/* A tela é larga? A mesma pergunta que o CSS responde com `wide:`, respondida em JavaScript.
 *
 * Existe porque esconder com CSS não basta quando o que está escondido **custa**. A zona do documento na
 * jornada busca o texto extraído inteiro, que no agravo real são vinte e cinco mil caracteres; renderizar e
 * esconder isso num celular básico gastaria dados e memória de quem menos os tem, para nada.
 *
 * O número está escrito aqui e no `tokens.css`, e não há como um ler o outro: consulta de mídia não lê
 * variável de CSS, e JavaScript não lê `@theme`. `lib/breakpoint.test.ts` é quem garante que os dois
 * continuam iguais.
 *
 * No servidor a resposta é "estreito". É o padrão certo para este produto: a primeira pintura é a do
 * celular, que é o aparelho da cidadã, e o computador recebe um ajuste depois de montar. */

const CONSULTA = "(min-width: 1024px)";

const assinar = (avisar: () => void) => {
  const mq = window.matchMedia(CONSULTA);
  mq.addEventListener("change", avisar);
  return () => mq.removeEventListener("change", avisar);
};
const noNavegador = () => window.matchMedia(CONSULTA).matches;
const noServidor = () => false;

export function useWide(): boolean {
  return useSyncExternalStore(assinar, noNavegador, noServidor);
}
