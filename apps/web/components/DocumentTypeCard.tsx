"use client";
import { useState } from "react";
import { CheckCircle2, CircleAlert, Pencil } from "lucide-react";
import { setDocumentType, type DocumentType, type DocumentTypeOption } from "@/lib/api";
import { m } from "@/lib/i18n";
import { Button, Card, StatusChip } from "./ui";

/* LeIA: a espécie do documento na revisão do advogado.
   Ela é a primeira coisa que o motor decide e é o que escolhe as palavras com que todas as etapas seguintes
   nomeiam as partes: num contrato lido como peça de processo, o CONTRATANTE vira "autor" e é assim que a
   cidadã lê. Por isso aparece antes das marcações, com o trecho que a sustenta ao lado, e por isso pode ser
   corrigida. A correção não conserta a explicação que já está na tela, e a tela diz isso: ela vale para a
   próxima rodada, e quem quiser o efeito agora usa "refazer a explicação" no documento. */

export function DocumentTypeCard({ id, tipo, opcoes, onSaved }:
  { id: string; tipo: DocumentType | null | undefined; opcoes: DocumentTypeOption[]; onSaved: (t: DocumentType) => void }) {
  const [editing, setEditing] = useState(false);
  const [escolha, setEscolha] = useState(tipo?.tipo ?? "");
  const [busy, setBusy] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [salvo, setSalvo] = useState(false);
  const t = m.panel.review.docType;

  if (!tipo && opcoes.length === 0) return null;

  async function salvar() {
    if (!escolha || busy) return;
    setBusy(true); setErro(null);
    try {
      const r = await setDocumentType(id, escolha);
      onSaved(r.tipo_documento);
      setEditing(false); setSalvo(true);
    } catch { setErro(t.failed); } finally { setBusy(false); }
  }

  return (
    <Card className="mb-4">
      <h2 className="mb-1 text-[1.15rem]">{t.title}</h2>
      <p className="mb-3 text-[0.95rem] text-ink-2">{t.intro}</p>

      {tipo && (
        <div className="mb-3">
          <p className="text-[0.95rem] text-ink-2">{tipo.revisado_por_advogado ? t.reviewedByYou : t.readAs}</p>
          <p className="flex flex-wrap items-center gap-2 text-[1.15rem] font-bold">
            {tipo.rotulo}
            {tipo.conferido && <StatusChip tone="ok">{m.panel.review.checked}</StatusChip>}
          </p>
          {tipo.trecho
            ? <p className="mt-1.5 text-[0.95rem] text-ink-2">{t.basedOn} <q className="text-ink">{tipo.trecho}</q></p>
            : !tipo.revisado_por_advogado && <p className="mt-1.5 flex items-center gap-1.5 text-[0.95rem] text-ink-2"><CircleAlert size={16} aria-hidden className="flex-none text-pend" />{t.noQuote}</p>}
          {tipo.revisado_por_advogado && tipo.aplicado === false &&
            <p role="status" className="mt-2 rounded-[12px] bg-teal-soft p-2.5 text-[0.95rem]">{t.notAppliedYet}</p>}
        </div>
      )}

      {salvo && !editing && <p role="status" className="mb-2 flex items-center gap-1.5 text-[0.95rem] text-ok"><CheckCircle2 size={16} aria-hidden />{t.saved}</p>}
      {erro && <p role="alert" className="mb-2 text-danger">{erro}</p>}

      {!editing ? (
        <Button variant="secondary" className="!w-auto" onClick={() => { setEditing(true); setSalvo(false); }}>
          <Pencil size={18} aria-hidden /> {t.change}
        </Button>
      ) : (
        <div className="grid gap-2">
          <label htmlFor="doc-type" className="font-bold">{t.chooseLabel}</label>
          <select id="doc-type" value={escolha} onChange={(e) => setEscolha(e.target.value)}
            className="min-h-[48px] rounded-button border-2 border-line-strong bg-surface px-3 text-[1rem] text-ink">
            <option value="" disabled>{t.chooseLabel}</option>
            {opcoes.map((o) => <option key={o.tipo} value={o.tipo}>{o.rotulo}</option>)}
          </select>
          <div className="flex flex-wrap gap-2">
            <Button className="!w-auto" onClick={salvar} disabled={!escolha || busy}>{busy ? t.saving : t.save}</Button>
            <Button variant="secondary" className="!w-auto" onClick={() => { setEditing(false); setEscolha(tipo?.tipo ?? ""); setErro(null); }}>{t.cancel}</Button>
          </div>
        </div>
      )}
    </Card>
  );
}
