"use client";

/* O contorno do que está por vir, no lugar da palavra "Carregando".
 *
 * A palavra sozinha não diz quanto nem o quê. O contorno diz: são três parágrafos, é um cartão, é uma
 * lista. Para quem lê com esforço isso muda a decisão de esperar ou sair, e é a diferença entre uma tela
 * que parece travada e uma que parece trabalhando.
 *
 * O `role="status"` e o texto continuam existindo, escondidos: quem navega ouvindo precisa da palavra, não
 * do contorno. Trocar um pelo outro teria consertado a tela de quem enxerga e piorado a de quem não.
 *
 * Sem animação de brilho. Ela é enfeite, custa bateria em celular básico e some de todo jeito para quem
 * pede menos movimento; o contorno sozinho já comunica. */

export function Skeleton({ linhas = 3, titulo = false, rotulo = "Carregando" }:
  { linhas?: number; titulo?: boolean; rotulo?: string }) {
  return (
    <div role="status" aria-busy="true" className="grid gap-2.5">
      <span className="sr-only">{rotulo}</span>
      {titulo && <div aria-hidden className="h-7 w-2/3 rounded-[8px] bg-muted" />}
      {Array.from({ length: linhas }, (_, i) => (
        <div key={i} aria-hidden
             className={`h-4 rounded-[6px] bg-muted ${i === linhas - 1 ? "w-3/5" : "w-full"}`} />
      ))}
    </div>
  );
}

/** O mesmo, dentro de um cartão, para as telas que carregam um bloco e não um texto corrido. */
export function SkeletonCard({ linhas = 3, rotulo = "Carregando" }: { linhas?: number; rotulo?: string }) {
  return (
    <div className="rounded-card border border-line bg-surface p-4">
      <Skeleton linhas={linhas} titulo rotulo={rotulo} />
    </div>
  );
}
