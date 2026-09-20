"use client";
import { useEffect, useRef, useState } from "react";
import { RefreshCw, X } from "lucide-react";

/* Registers the service worker and shows "Nova versão disponível" when a new build is waiting.
   The user chooses when to apply (never yanked out of a journey). Checks for updates every 60 s and when the
   app comes back to the foreground, so an app left open still notices a deploy. */
export function UpdatePrompt() {
  const [waiting, setWaiting] = useState<ServiceWorker | null>(null);
  const [nextBuild, setNextBuild] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const reloading = useRef(false);

  useEffect(() => {
    if (!("serviceWorker" in navigator) || process.env.NODE_ENV !== "production") return;
    let reg: ServiceWorkerRegistration | undefined;
    const track = (sw: ServiceWorker | null) => { if (!sw) return; if (sw.state === "installed" && navigator.serviceWorker.controller) setWaiting(sw); sw.addEventListener("statechange", () => { if (sw.state === "installed" && navigator.serviceWorker.controller) setWaiting(sw); }); };
    navigator.serviceWorker.register("/sw.js").then((r) => {
      reg = r;
      if (r.waiting) setWaiting(r.waiting);
      r.addEventListener("updatefound", () => track(r.installing));
    }).catch(() => { /* installation is optional */ });
    const onControl = () => { if (reloading.current) return; reloading.current = true; window.location.reload(); };
    navigator.serviceWorker.addEventListener("controllerchange", onControl);
    const check = () => { reg?.update().catch(() => {}); };
    const timer = window.setInterval(check, 60_000);
    const onVisible = () => { if (document.visibilityState === "visible") check(); };
    document.addEventListener("visibilitychange", onVisible);
    return () => { window.clearInterval(timer); document.removeEventListener("visibilitychange", onVisible); navigator.serviceWorker.removeEventListener("controllerchange", onControl); };
  }, []);

  useEffect(() => {
    if (!waiting) return;
    try { navigator.vibrate?.(12); } catch { /* no haptics */ }
    /* the waiting worker carries the id of the new build; read it so the prompt can name what is coming */
    fetch("/sw.js", { cache: "no-store" }).then((r) => r.text()).then((t) => { const m = /BUILD_ID = "([^"]+)"/.exec(t); if (m) setNextBuild(m[1].split("-")[0]); }).catch(() => {});
  }, [waiting]);

  if (!waiting) return null;
  const current = process.env.NEXT_PUBLIC_COMMIT_SHA || "dev";
  const version = `v${process.env.NEXT_PUBLIC_APP_VERSION ?? ""} · de ${current} para ${nextBuild ?? "nova build"}`;
  return (
    <div role="status" aria-live="polite" className="fixed inset-x-3 bottom-3 z-50 flex items-center gap-3 rounded-[14px] bg-navy px-4 py-3 text-paper shadow-[0_8px_30px_rgba(8,24,32,.35)] wide:inset-x-auto wide:right-6 wide:w-[420px]">
      <div className="min-w-0 flex-1">
        <p className="font-bold">Nova versão do LeIA disponível.</p>
        <p className="font-mono text-[0.8rem] text-paper/70">{version}</p>
      </div>
      <button type="button" disabled={applying} onClick={() => { setApplying(true); waiting.postMessage({ type: "SKIP_WAITING" }); window.setTimeout(() => { if (!reloading.current) { reloading.current = true; window.location.reload(); } }, 2500); }}
        className="inline-flex min-h-[44px] items-center gap-2 rounded-[10px] bg-teal px-3 font-bold text-navy disabled:opacity-60">
        <RefreshCw size={18} aria-hidden /> {applying ? "Atualizando" : "Atualizar"}
      </button>
      <button type="button" aria-label="Agora não" onClick={() => setWaiting(null)} className="grid h-11 w-11 place-items-center rounded-full text-paper/80 hover:bg-white/10"><X size={20} aria-hidden /></button>
    </div>
  );
}

/* "v1.1.0 · abc1234" for the footer: the version comes from apps/web/package.json, which the release commit
   bumps together with the CHANGELOG; the commit sha is what changes on every deploy. */
export function VersionBadge({ className = "" }: { className?: string }) {
  const sha = process.env.NEXT_PUBLIC_COMMIT_SHA ?? "dev";
  return <span className={`font-mono text-[0.85rem] ${className}`}>LeIA v{process.env.NEXT_PUBLIC_APP_VERSION ?? "0.0.0"} · {sha === "dev" ? sha : <a href={`https://github.com/deegalabs/leia/commit/${sha}`} className="underline underline-offset-2" target="_blank" rel="noreferrer">{sha}</a>}</span>;
}
