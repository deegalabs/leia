"use client";
import { useEffect } from "react";
import { AlertCircle } from "lucide-react";

import { AssistantBanner, Button, Card, LinkButton, Page } from "@/components/ui";
import { fmt, m } from "@/lib/i18n";

/* A tela de quando o servidor falha dentro de uma rota.
 *
 * Até aqui ela não existia: só havia `not-found.tsx`, e qualquer exceção caía na tela branca do Next, que
 * em produção é uma página sem texto nenhum. Quem está do outro lado é alguém com medo de um documento
 * jurídico, e a tela branca é a pior resposta possível: ela não diz se o problema foi dela, se o documento
 * se perdeu, nem o que fazer.
 *
 * A mensagem crua da exceção não aparece. Ela é escrita para quem mantém o serviço, não para quem o usa, e
 * costuma carregar caminho de arquivo, nome de coluna e pedaço de consulta. O `digest` aparece, porque é um
 * resumo que o Next gera justamente para ligar o que a pessoa viu ao que ficou no log do servidor. */

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    /* No console de quem desenvolve, e no relatório de quem monitorar depois. Nunca na tela. */
    console.error(error);
  }, [error]);

  return (
    <Page>
      <AssistantBanner />
      <Card tone="pending">
        <h1 className="mb-2 flex items-center gap-2 text-[1.5rem]">
          <AlertCircle size={26} aria-hidden className="flex-none text-pend" />
          {m.error.title}
        </h1>
        <p>{m.error.body}</p>
        <p className="mt-3 text-[0.95rem] text-ink-2">
          {error.digest ? fmt(m.error.code, { codigo: error.digest }) : m.error.codeMissing}
        </p>
      </Card>

      <div className="mt-4 grid gap-2">
        <Button onClick={reset}>{m.error.retry}</Button>
        <LinkButton href="/" variant="secondary">{m.error.home}</LinkButton>
        <LinkButton href="/painel" variant="ghost">{m.error.panel}</LinkButton>
      </div>
    </Page>
  );
}
