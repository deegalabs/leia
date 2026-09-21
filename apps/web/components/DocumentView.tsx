"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getInferences } from "@/lib/api";
import type { Inferences } from "@/lib/inferences";
import { AssistantBanner, Card, Page, StatusChip } from "./ui";
import { InferenceMarks, scrollToMark } from "./InferenceMarks"; /* LeIA: marks shared with the lawyer review */
import { Skeleton } from "./Skeleton";

export function DocumentView({ hash }: { hash: string }) {
  const [data, setData] = useState<Inferences | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    getInferences(hash).then(setData).catch((e: Error & { status?: number }) => setError(e.status === 409 ? "A explicação ainda está sendo preparada. Volte em alguns minutos." : e.status === 404 ? "Documento não encontrado." : e.status === 403 ? e.message : "Deu um problema do nosso lado, não foi você. Tente de novo em instantes."));
  }, [hash]);
  const goTo = (ref: string) => scrollToMark("mark", ref);

  return (
    <Page wide>
      <AssistantBanner />
      <h1 className="mb-2 text-[1.5rem]">O documento e o que a assistente encontrou nele</h1>
      {!data && (error
        ? <p role="status" className="text-ink-2">{error}</p>
        : <Skeleton linhas={6} titulo rotulo="Carregando o documento." />)}
      {data && (
        <>
          <p className="mb-3">Cada marcação mostra de onde veio uma informação usada na explicação. Marcações conferidas foram encontradas palavra por palavra no texto.</p>
          <div className="mb-4 flex flex-wrap gap-2">
            <StatusChip tone="ok">{data.conferidos} conferidas no texto</StatusChip>
            {data.total - data.conferidos > 0 && <StatusChip tone="pending">{data.total - data.conferidos} não localizadas</StatusChip>}
          </div>
          {data.sinteses.length > 0 && (
            <Card className="mb-4">
              <h2 className="mb-2 text-[1.15rem]">O que a assistente concluiu</h2>
              <div className="space-y-3">
                {data.sinteses.map((s, i) => (
                  <div key={i}>
                    <p className="font-bold">{s.rotulo}</p>
                    <p>{s.texto}</p>
                    {s.lastro.length > 0 && <p className="text-[0.9rem] text-ink-2">Baseado em {s.lastro.length} {s.lastro.length === 1 ? "marcação" : "marcações"}: {s.lastro.map((r) => <button key={r} type="button" onClick={() => goTo(r)} className="mr-2 underline underline-offset-2 text-teal-deep">{r}</button>)}</p>}
                  </div>
                ))}
              </div>
            </Card>
          )}
          <InferenceMarks inferences={data} idPrefix="mark" />
          <p className="mt-4"><Link href={`/t/${hash}`} className="font-bold text-teal-deep underline underline-offset-4">Voltar para a explicação</Link></p>
        </>
      )}
    </Page>
  );
}
