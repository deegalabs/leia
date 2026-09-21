"use client";
import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

import { assinarProgresso, comecou } from "@/lib/progress";

/* A linha de progresso no topo da janela.
 *
 * Ela responde a uma pergunta que o produto deixava sem resposta: "travou ou está carregando?". Quem lê com
 * esforço, num celular básico e numa conexão ruim, toca um botão e não vê nada mudar por segundos. Sem
 * sinal, a reação natural é tocar de novo.
 *
 * Ela **não** é anunciada por leitor de tela (`aria-hidden`), de propósito: cada tela já tem o seu
 * `role="status"` dizendo "carregando", e anunciar as duas coisas faria a pessoa ouvir o mesmo aviso duas
 * vezes a cada busca. Esta barra é o complemento visual daquele texto, não um segundo aviso.
 *
 * Sobre movimento: `globals.css` desliga transição e animação para quem pede menos movimento, então a barra
 * passa a saltar de largura em vez de deslizar. Ela continua dizendo a mesma coisa, que é o ponto: o sinal
 * está na largura, não no deslizamento. */

const SUMIR_MS = 220;

export function RouteProgress() {
  const pathname = usePathname();
  const [largura, setLargura] = useState(0);
  const [visivel, setVisivel] = useState(false);

  /* Troca de rota: a navegação começou e o componente novo ainda não montou. */
  useEffect(() => {
    const fim = comecou();
    const t = setTimeout(fim, 400);
    return () => { clearTimeout(t); fim(); };
  }, [pathname]);

  /* Em referência e não em estado: a assinatura precisa saber se algo está desenhado sem que isso a faça
     reassinar. Com `largura` nas dependências, o efeito rodava de novo a cada crescimento da barra, e o
     tempo pendente da rodada anterior ficava sem quem o cancelasse. */
  const desenhada = useRef(false);

  useEffect(() => {
    let saida: ReturnType<typeof setTimeout> | undefined;
    const cancelar = assinarProgresso((emCurso) => {
      if (emCurso > 0) {
        clearTimeout(saida);
        desenhada.current = true;
        setVisivel(true);
        /* Cresce depressa até 80% e para: o que falta é o tempo que ninguém sabe medir, e fingir que sabe é
           o que faz uma barra chegar a 99% e ficar lá. */
        setLargura((atual) => (atual < 80 ? Math.min(80, atual + (80 - atual) * 0.4 + 12) : atual));
      } else if (desenhada.current) {
        /* Só desaparece o que apareceu. O assinante recebe o valor atual ao entrar, e sem esta guarda montar
           o componente agendaria o sumiço de algo que nunca foi desenhado. */
        clearTimeout(saida);
        setLargura(100);
        saida = setTimeout(() => { desenhada.current = false; setVisivel(false); setLargura(0); }, SUMIR_MS);
      }
    });
    return () => { clearTimeout(saida); cancelar(); };
  }, []);

  if (!visivel) return null;
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-x-0 top-0 z-[60] h-[5px] bg-transparent">
      <div className="h-full bg-teal-deep transition-[width,opacity] duration-200 ease-out"
           style={{ width: `${largura}%`, opacity: largura === 100 ? 0 : 1 }} />
    </div>
  );
}
