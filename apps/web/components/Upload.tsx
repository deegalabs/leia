"use client";
import { useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ExternalLink, FileUp } from "lucide-react";
import { clientLinkUrl, createTask } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, m } from "@/lib/i18n";
import { AppHeader, Button, Card, CopyButton, Field, LinkButton, Page, inputClass } from "./ui";
import { AuthNav, RequireAuth } from "./Session";

export function Upload() {
  return (
    <Page>
      <AppHeader right={<AuthNav />} />
      <RequireAuth next="/enviar"><UploadBody /></RequireAuth>
    </Page>
  );
}

function UploadBody() {
  const { isCitizen } = useAuth();
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [titulo, setTitulo] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ id: number; hash: string } | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (!file) { setError(m.upload.needFile); return; }
    if (file.type !== "application/pdf" && !/\.pdf$/i.test(file.name)) { setError(m.upload.notPdf); return; }
    setBusy(true); setError(null);
    try {
      const r = await createTask(titulo.trim() || file.name.replace(/\.pdf$/i, ""), file);
      if (isCitizen) { router.push(`/t/${r.hash}`); return; }
      setDone(r);
    } catch { setError(m.common.systemError); }
    finally { setBusy(false); }
  }

  if (done) {
    const link = clientLinkUrl(done.hash);
    return (
      <>
        <h1 className="mb-2 text-[1.5rem]">{m.upload.doneTitle}</h1>
        <p className="mb-4">{m.upload.doneLawyer}</p>
        <Card>
          <h2 className="mb-1 text-[1.15rem]">{m.panel.detail.clientLink}</h2>
          <code className="block break-all font-mono text-[0.95rem]">{link}</code>
          <div className="mt-2"><CopyButton text={link} label={m.panel.copyClientLink} /></div>
        </Card>
        <div className="mt-4 grid gap-2">
          <LinkButton href={`/t/${done.hash}`}><ExternalLink size={20} aria-hidden /> {m.panel.openAsClient}</LinkButton>
          <LinkButton href={`/painel/${done.id}`} variant="secondary">{m.upload.openInPanel}</LinkButton>
          <Button variant="ghost" onClick={() => { setDone(null); setTitulo(""); setFile(null); }}>{m.upload.sendAnother}</Button>
        </div>
      </>
    );
  }

  return (
    <>
      <h1 className="mb-2 text-[1.5rem]">{isCitizen ? m.upload.titleCitizen : m.upload.title}</h1>
      <p className="mb-4 text-ink-2">{m.upload.intro}</p>
      <Card>
        <form onSubmit={submit} className="grid gap-4" noValidate>
          <Field id="titulo" label={m.upload.docTitle}>
            <input id="titulo" className={inputClass} value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder={m.upload.docTitlePlaceholder} />
          </Field>
          <Field id="pdf" label={m.upload.file} hint={m.upload.fileHint}>
            <input id="pdf" ref={fileRef} type="file" tabIndex={-1} accept="application/pdf,.pdf" className="sr-only" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setError(null); }} />
            <Button type="button" variant="secondary" onClick={() => fileRef.current?.click()}><FileUp size={20} aria-hidden /> {m.upload.choose}</Button>
            {file && <p className="text-[0.95rem]" aria-live="polite">{fmt(m.upload.chosen, { name: file.name })}</p>}
          </Field>
          {error && <p role="alert" className="text-danger">{error}</p>}
          <Button type="submit" disabled={busy || !file}>{busy ? m.upload.submitting : m.upload.submit}</Button>
        </form>
      </Card>
    </>
  );
}
