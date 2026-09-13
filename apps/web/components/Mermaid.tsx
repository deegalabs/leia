"use client";
import { useEffect, useId, useRef, useState } from "react";
import { Maximize2, Minus, Plus, Scan, X } from "lucide-react";

/* Renders a Mermaid diagram from the documentation in the browser (the library loads only on pages that have one)
   and offers a full-screen view: a modal dialog that also asks the browser for real full screen where supported. */
export function Mermaid({ code, title }: { code: string; title?: string }) {
  const id = useId().replace(/[^a-zA-Z0-9]/g, "");
  const [svg, setSvg] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [zoom, setZoom] = useState(1); // 1 = fit the screen; above 1 the drawing grows and scrolls
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    let alive = true;
    import("mermaid")
      .then(async ({ default: mermaid }) => {
        mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "strict", fontFamily: "Atkinson Hyperlegible, system-ui, sans-serif" });
        const out = await mermaid.render(`mermaid-${id}`, code);
        if (alive) setSvg(out.svg);
      })
      .catch(() => { if (alive) setFailed(true); });
    return () => { alive = false; };
  }, [code, id]);

  function open() {
    const d = dialog.current;
    if (!d) return;
    setZoom(window.innerWidth < 700 ? 2.5 : 1); // a wide sequence diagram is unreadable when squeezed into a phone
    d.showModal();
    d.requestFullscreen?.().catch(() => { /* full screen is optional; the dialog already covers the viewport */ });
  }
  function close() {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    dialog.current?.close();
  }

  const label = title ? `Diagrama: ${title}` : "Diagrama";
  return (
    <figure className="mb-4 rounded-card border border-line bg-surface p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <figcaption className="text-[0.9rem] font-bold text-ink-2">{label}</figcaption>
        {svg && <button type="button" onClick={open} className="inline-flex min-h-[44px] items-center gap-2 rounded-button px-3 font-bold text-teal-deep hover:bg-teal-soft"><Maximize2 size={18} aria-hidden /> Tela cheia</button>}
      </div>
      {svg ? (
        <div className="diagram overflow-x-auto" role="img" aria-label={label} dangerouslySetInnerHTML={{ __html: svg }} />
      ) : (
        <pre className="max-w-full overflow-x-auto rounded-[10px] bg-muted p-3 font-mono text-[0.85rem]"><code>{code}</code></pre>
      )}
      {!svg && <p className="mt-2 text-[0.9rem] text-ink-2">{failed ? "O diagrama não pôde ser desenhado; o texto acima é a fonte." : "Desenhando o diagrama."}</p>}
      <dialog ref={dialog} onCancel={(e) => { e.preventDefault(); close(); }} aria-label={label}
        className="diagram-dialog m-0 h-dvh max-h-none w-screen max-w-none bg-paper-2 p-0 text-ink backdrop:bg-navy/80">
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-2">
            <p className="font-bold">{label}</p>
            <div className="flex items-center gap-1">
              <button type="button" aria-label="Reduzir" onClick={() => setZoom((z) => Math.max(1, +(z - 0.5).toFixed(1)))} className="grid h-11 w-11 place-items-center rounded-button text-teal-deep hover:bg-teal-soft"><Minus size={18} aria-hidden /></button>
              <button type="button" onClick={() => setZoom(1)} className="inline-flex min-h-[44px] items-center gap-1 rounded-button px-2 text-[0.9rem] font-bold text-teal-deep hover:bg-teal-soft"><Scan size={16} aria-hidden /> Ajustar</button>
              <button type="button" aria-label="Ampliar" onClick={() => setZoom((z) => Math.min(5, +(z + 0.5).toFixed(1)))} className="grid h-11 w-11 place-items-center rounded-button text-teal-deep hover:bg-teal-soft"><Plus size={18} aria-hidden /></button>
              <button type="button" onClick={close} className="inline-flex min-h-[44px] items-center gap-2 rounded-button px-3 font-bold text-teal-deep hover:bg-teal-soft"><X size={18} aria-hidden /> Fechar</button>
            </div>
          </div>
          {svg && <div className="diagram diagram-full min-h-0 flex-1 overflow-auto p-3" data-fit={zoom === 1 ? "1" : undefined} style={{ ["--zoom" as string]: zoom }} dangerouslySetInnerHTML={{ __html: svg }} />}
          <p className="border-t border-line px-4 py-1.5 text-[0.85rem] text-ink-2">Zoom {zoom.toFixed(1).replace(".0", "")}x. Arraste para rolar; no celular, a pinça também amplia.</p>
        </div>
      </dialog>
    </figure>
  );
}
