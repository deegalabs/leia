"use client";
import { useEffect, useState } from "react";
import { Check } from "lucide-react";

import { getInferences, type Topic } from "@/lib/api";
import type { Inferences } from "@/lib/inferences";
import { MarkedText } from "./InferenceMarks";
import { Skeleton } from "./Skeleton";
import { cleanTitle } from "./Inline";

/* As duas zonas laterais da jornada, que só existem no computador.
 *
 * No celular a jornada é uma coisa de cada vez, e isso é deliberado: a pessoa lê um ponto, entende, segue.
 * No computador há espaço para os três ao mesmo tempo, e aí a pergunta muda — ela quer ver onde está na
 * lista e conferir o documento sem perder o lugar da explicação.
 *
 * Cada zona rola por conta. Sem isso, rolar o documento levaria a explicação junto, que é exatamente o que
 * torna a conferência cansativa: a pessoa perde a linha que estava lendo toda vez que confere um trecho. */

export function TopicRail({ topics, atual, onIr }:
  { topics: Topic[]; atual: number; onIr: (n: number) => void }) {
  return (
    <nav aria-label="Pontos da explicação" className="grid gap-1">
      {topics.map((t, n) => {
        const aqui = n === atual;
        return (
          <button key={t.id} type="button" onClick={() => onIr(n)} aria-current={aqui ? "step" : undefined}
            className={`flex min-h-[44px] items-start gap-2 rounded-button px-2.5 py-2 text-left text-[0.95rem] ${
              aqui ? "bg-teal-soft font-bold text-ink" : "text-ink-2 hover:bg-muted"}`}>
            <span aria-hidden className={`mt-0.5 grid h-5 w-5 flex-none place-items-center rounded-full text-[0.7rem] font-bold ${
              n < atual ? "bg-ok text-white" : aqui ? "bg-teal-deep text-white" : "border-2 border-line"}`}>
              {n < atual ? <Check size={12} aria-hidden /> : n + 1}
            </span>
            <span className="flex-1">{cleanTitle(t.titulo)}</span>
          </button>
        );
      })}
    </nav>
  );
}

/* A zona do documento. Ela busca as inferências por conta, e só é montada quando a tela é larga: o texto
   extraído do agravo real tem vinte e cinco mil caracteres, e trazer isso para um celular básico só para
   escondê-lo com CSS gastaria dados e memória de quem menos os tem. */
export function DocumentRail({ hash }: { hash: string }) {
  const [dados, setDados] = useState<Inferences | null>(null);
  const [falhou, setFalhou] = useState(false);

  useEffect(() => {
    let vivo = true;
    getInferences(hash)
      .then((d) => { if (vivo) setDados(d); })
      .catch(() => { if (vivo) setFalhou(true); });
    return () => { vivo = false; };
  }, [hash]);

  /* Falha aqui não vira mensagem de erro: esta zona é um apoio, e a jornada inteira continua funcionando
     sem ela. Uma tarja vermelha ao lado da explicação assustaria por um problema que não é da pessoa e que
     não a impede de nada. A rota `/t/{hash}/documento` continua sendo o caminho completo. */
  if (falhou) return null;
  if (!dados) return <Skeleton linhas={12} rotulo="Carregando o documento." />;

  const itens = dados.classes.flatMap((c) => c.itens);
  return (
    <div>
      <h2 className="mb-2 text-[1.05rem]">O seu documento</h2>
      <p className="mb-3 text-[0.9rem] text-ink-2">
        As marcações mostram de onde veio cada informação da explicação.
      </p>
      <MarkedText texto={dados.texto} items={itens} idPrefix="trilho" />
    </div>
  );
}
