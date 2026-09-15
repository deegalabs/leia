"use client";
import { useEffect, useState } from "react";
import { formatDateTime, getVerify, type VerifyResult } from "@/lib/api";
import { AssistantBanner, BottomActionBar, Button, Card, HashDisplay, LinkButton, Page, SpeakButton, StatusChip } from "./ui";
import { QrCode } from "./QrCode";
import { m } from "@/lib/i18n";

export function Receipt({ attempt }: { attempt: string }) {
  const [data, setData] = useState<VerifyResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    const run = () => getVerify(attempt).then((d) => { if (alive) { setData(d); setError(null); } })
      .catch((e: Error & { status?: number }) => { if (alive) setError(e.status === 404 ? "Comprovante não encontrado." : "Deu um problema do nosso lado, não foi você. Estamos tentando de novo."); });
    run();
    const id = setInterval(run, 30000);   /* the stamp arrives minutes later; keep refreshing while open */
    return () => { alive = false; clearInterval(id); };
  }, [attempt]);

  const verifyPath = `/verify/${attempt}`;
  return (
    <Page>
      <AssistantBanner />
      <h1 className="mb-3 text-[1.5rem]">{m.c6.title}</h1>
      {!data && <p role="status" className="text-ink-2">{error ?? "Carregando seu comprovante."}</p>}
      {data && (
        <>
          <StatusChip tone={data.otsPresent ? "ok" : "pending"}>{data.otsPresent ? m.status.registered : m.status.stampPending}</StatusChip>
          <Card className="mt-3">
            <p className="mb-1">{data.payload.understood ? "Você entendeu o documento" : "Registro da sua tentativa"}: {formatDateTime(data.payload.createdAt)}</p>
            <p className="mb-4 text-[0.95rem] text-ink-2">Tentativa {data.payload.attemptRound}, {data.payload.answered} perguntas respondidas.</p>
            <QrCode value={verifyPath} label="QR para conferir o registro nesta mesma página de verificação" />
            <p className="mb-4 mt-2 text-center text-[0.95rem] text-ink-2">Aponte a câmera para conferir</p>
            <p className="mb-1 text-[0.95rem] text-ink-2">Código do registro</p>
            <HashDisplay value={data.payloadHash} />
            {!data.otsPresent && <p className="mt-3 text-[0.95rem] text-pend">{data.demo ? "Nesta demonstração o carimbo público não é gravado. No serviço completo, ele chega em alguns minutos e fica na página de verificação." : m.c6.stampPending}</p>}
          </Card>
          <Card tone="soft" className="mt-3">
            <h2 className="mb-2 text-[1.15rem]">O que este comprovante prova</h2>
            <p>{m.c6.proves} {m.c6.doesNotContain}</p>
            <SpeakButton text={`${m.c6.proves} ${m.c6.doesNotContain}`} label="Ouvir explicação" />
          </Card>
          <BottomActionBar>
            <Button onClick={() => window.print()}>{m.c6.save}</Button>
            <LinkButton href={`/verify/${attempt}`} variant="secondary">{m.c6.verifyLink}</LinkButton>
          </BottomActionBar>
        </>
      )}
    </Page>
  );
}
