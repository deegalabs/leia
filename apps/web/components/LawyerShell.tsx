"use client";
import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { FilePlus2, ListChecks } from "lucide-react";

import { useWide } from "@/lib/wide";
import { AppHeader, Page } from "./ui";

/* A casca do advogado: barra no alto no celular, lateral navy no computador.
 *
 * As duas pessoas deste produto usam aparelhos opostos e por motivos opostos. A cidadã lê um documento no
 * celular, uma vez, com medo. O advogado trabalha numa lista, no computador, todo dia. Dar a mesma coluna
 * estreita aos dois é atender mal aos dois: ela ganha uma tela boa, ele ganha uma tela de celular esticada
 * num monitor de 27 polegadas, com a lista inteira escondida atrás de rolagem.
 *
 * O navy já tem esse papel declarado em `tokens.css` ("lawyer sidebar"), e até agora ele não existia em
 * lugar nenhum além do cabeçalho. */

const LINKS = [
  { href: "/painel", rotulo: "Meus documentos", Icone: ListChecks },
  { href: "/enviar", rotulo: "Enviar documento", Icone: FilePlus2 },
];

export function LawyerShell({ children, right }: { children: ReactNode; right?: ReactNode }) {
  const larga = useWide();
  const caminho = usePathname();

  if (!larga) {
    return <Page wide><AppHeader right={right} />{children}</Page>;
  }
  return (
    <div className="flex min-h-full flex-1">
      {/* `sticky` e não `fixed`: a lateral acompanha a rolagem sem sair do fluxo, então o conteúdo não
          precisa de margem compensatória que alguém esquece de ajustar depois. */}
      <nav aria-label="Navegação do painel"
           className="sticky top-0 flex h-screen w-[240px] flex-none flex-col gap-1 bg-navy px-3 py-4 text-paper">
        <Link href="/" aria-label="LeIA, página inicial" className="mb-4 inline-flex min-h-[44px] items-center px-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo-horizontal-dark.svg" alt="LeIA" className="h-7" />
        </Link>
        {LINKS.map(({ href, rotulo, Icone }) => {
          const aqui = caminho === href || caminho.startsWith(`${href}/`);
          return (
            <Link key={href} href={href} aria-current={aqui ? "page" : undefined}
              className={`flex min-h-[48px] items-center gap-2.5 rounded-button px-3 font-bold ${
                aqui ? "bg-teal-deep text-white" : "text-paper hover:bg-white/10"}`}>
              <Icone size={20} aria-hidden /> {rotulo}
            </Link>
          );
        })}
        <div className="mt-auto px-1">{right}</div>
      </nav>
      <div className="min-w-0 flex-1 px-6 py-5">
        <div className="mx-auto w-full max-w-[1100px]">{children}</div>
      </div>
    </div>
  );
}
