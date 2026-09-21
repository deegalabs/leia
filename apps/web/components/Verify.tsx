"use client";
import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { formatDateTime, getVerify, proofUrl, type VerifyResult } from "@/lib/api";
import { Card, CopyButton, HashDisplay, Page, StatusChip } from "./ui";
import { m } from "@/lib/i18n";
import { stampView } from "@/lib/stamp";
import { SkeletonCard } from "./Skeleton";

export function Verify({ attempt }: { attempt: string }) {
  const [data, setData] = useState<VerifyResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    getVerify(attempt).then(setData).catch((e: Error & { status?: number }) => setError(e.status === 404 ? "Registro não encontrado." : "Deu um problema do nosso lado. Tente de novo em instantes."));
  }, [attempt]);

  const stamp = data && stampView(data);

  function download() {
    if (!data) return;
    const blob = new Blob([data.canonical], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "registro.json"; a.click(); URL.revokeObjectURL(a.href);
  }

  return (
    <Page wide>
      <header className="-mx-4 mb-5 flex items-center justify-between bg-navy px-4 py-3 text-paper">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo-horizontal-dark.svg" alt="LeIA" className="h-7" />
        <span className="text-[0.95rem] text-paper/85">Verificação pública</span>
      </header>
      <h1 className="mb-3 text-[1.5rem]">Registro de entendimento</h1>
      {!data && (error
        ? <p role="status" className="text-ink-2">{error}</p>
        : <SkeletonCard linhas={4} rotulo="Carregando o registro." />)}
      {data && stamp && (
        <div className="space-y-3">
          <StatusChip tone={stamp.tone}>{stamp.chip}</StatusChip>
          <Card><h2 className="mb-1 text-[1.15rem]">O que esta página mostra</h2><p>Esta página mostra um código e o carimbo de tempo dele. Ela não mostra nome, documento nem respostas.</p></Card>
          <Card>
            <h2 className="mb-2 text-[1.15rem]">Código do registro (SHA-256)</h2>
            <HashDisplay value={data.payloadHash} />
            <p className="mt-2 text-[0.95rem] text-ink-2">O registro diz ter sido criado em {formatDateTime(data.payload.createdAt)}.</p>
          </Card>
          <Card>
            <h2 className="mb-1 text-[1.15rem]">Carimbo de tempo público</h2>
            <p className="mb-2">{m.stamp.network}</p>
            <p className={`mb-2 ${stamp.tone === "pending" ? "text-pend" : "text-ink-2"}`}>{stamp.text}</p>
            {stamp.hasProof && <a className="inline-flex min-h-[44px] items-center gap-2 font-bold text-teal-deep underline underline-offset-4" href={proofUrl(attempt)}><Download size={18} aria-hidden /> {m.stamp.download}</a>}
          </Card>
          <Card>
            <details>
              <summary className="min-h-[44px] cursor-pointer list-none font-bold text-teal-deep">Ver JSON canônico</summary>
              <p className="mb-2 mt-2 text-[0.95rem] text-ink-2">Este é o texto exato que gerou o código. Qualquer espaço a mais muda o resultado.</p>
              <pre className="overflow-x-auto rounded-[12px] bg-muted p-3 font-mono text-[0.85rem] whitespace-pre-wrap break-all">{data.canonical}</pre>
              <div className="mt-2 flex flex-wrap gap-2">
                <CopyButton text={data.canonical} label="Copiar JSON" />
                <button type="button" onClick={download} className="inline-flex min-h-[44px] items-center gap-2 px-4 font-bold text-teal-deep underline underline-offset-4"><Download size={18} aria-hidden /> Baixar registro.json</button>
              </div>
            </details>
          </Card>
          <Card>
            <h2 className="mb-2 text-[1.15rem]">Como conferir por conta própria</h2>
            <ol className="list-decimal space-y-2 pl-5">
              <li>Baixe o arquivo registro.json. Não abra e salve de novo: isso pode mudar os bytes.</li>
              <li>No terminal, rode: <code className="font-mono">sha256sum registro.json</code></li>
              <li>Compare o resultado com o código do registro acima. Precisa ser igual, caractere por caractere.</li>
              <li>Com a prova .ots: <code className="font-mono">ots verify -f registro.json registro.ots</code> mostra a data carimbada.</li>
            </ol>
            <p className="mt-2 text-[0.9rem] text-ink-2">No Windows: certutil -hashfile registro.json SHA256. No macOS: shasum -a 256 registro.json.</p>
          </Card>
          <footer className="space-y-2 text-[0.95rem] text-ink-2">
            {/* the record dates itself, so only the stamp proves the code existed before that moment */}
            <p><strong>O que este registro prova:</strong> que este código foi gerado a partir do JSON acima, que descreve uma sessão de entendimento (tentativa, perguntas respondidas e resultado){stamp.hasProof ? ", e que ele já existia na data do carimbo" : ". Sem carimbo, a data acima é a que o próprio registro declara"}.</p>
            <p><strong>O que não prova:</strong> não é a assinatura do contrato, não diz quem respondeu, não mostra o conteúdo do documento e não substitui a conversa com o advogado.</p>
          </footer>
        </div>
      )}
    </Page>
  );
}
