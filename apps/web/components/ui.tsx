"use client";
import { useEffect, useState, useSyncExternalStore, type ButtonHTMLAttributes, type ReactNode } from "react";
import Link from "next/link";
import { Check, Copy, Volume2, Square } from "lucide-react";

type Variant = "primary" | "secondary" | "ghost";
const base = "inline-flex w-full items-center justify-center gap-2 rounded-button px-4 font-bold text-[1.05rem] transition-colors disabled:opacity-55 disabled:cursor-default";
const variants: Record<Variant, string> = {
  primary: "min-h-[52px] bg-teal-deep text-white hover:bg-[#195C5C]",
  secondary: "min-h-[48px] border-2 border-ink text-ink bg-transparent hover:bg-teal-soft",
  ghost: "min-h-[44px] text-teal-deep underline underline-offset-4 hover:bg-teal-soft",
};

export function Button({ variant = "primary", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button type="button" {...props} className={`${base} ${variants[variant]} ${className}`} />;
}

export function LinkButton({ href, variant = "primary", children, className = "", external = false }: { href: string; variant?: Variant; children: ReactNode; className?: string; external?: boolean }) {
  const cls = `${base} ${variants[variant]} ${className}`;
  return external ? <a href={href} className={cls}>{children}</a> : <Link href={href} className={cls}>{children}</Link>;
}

export function Card({ children, className = "", tone = "surface" }: { children: ReactNode; className?: string; tone?: "surface" | "soft" | "pending" }) {
  const tones = { surface: "bg-surface border border-line", soft: "bg-teal-soft", pending: "bg-pend-soft" };
  return <section className={`rounded-card p-5 ${tones[tone]} ${className}`}>{children}</section>;
}

export function BottomActionBar({ children }: { children: ReactNode }) {
  return (
    <div className="no-print sticky bottom-0 -mx-4 mt-6 border-t border-line bg-paper-2/95 px-4 pb-[max(12px,env(safe-area-inset-bottom))] pt-3 backdrop-blur">
      <div className="mx-auto grid max-w-[560px] gap-2 md:max-w-[680px]">{children}</div>
    </div>
  );
}

export function ProgressSteps({ total, current, label }: { total: number; current: number; label: string }) {
  return (
    <nav aria-label={label} className="mb-4">
      <p className="mb-2 text-[0.95rem] text-ink-2">{label}</p>
      <div className="flex gap-1.5" aria-hidden="true">
        {Array.from({ length: total }, (_, i) => <i key={i} className={`h-2 flex-1 rounded ${i <= current ? "bg-teal-deep" : "bg-line"}`} />)}
      </div>
    </nav>
  );
}

export function StatusChip({ tone, children }: { tone: "ok" | "pending" | "neutral" | "danger"; children: ReactNode }) {
  /* LeIA: "danger" only for a failed pipeline, never for the citizen's answers */
  const tones = { ok: "bg-ok-soft text-ok", pending: "bg-pend-soft text-pend", neutral: "bg-muted text-ink-2", danger: "bg-danger-soft text-danger" };
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[1rem] font-bold ${tones[tone]}`}>{children}</span>;
}

export function AssistantBanner() {
  return (
    <header className="no-print -mx-4 mb-4 flex items-center justify-between gap-3 bg-navy px-4 py-3 text-paper">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/logo-horizontal-dark.svg" alt="LeIA" className="h-7" />
      <p className="text-right text-[0.9rem] leading-tight text-paper/85">Assistente automática. Explica o que está escrito. Não dá conselho jurídico.</p>
    </header>
  );
}

export function HashDisplay({ value }: { value: string }) {
  const groups = value.match(/.{1,8}/g) ?? [value];
  return (
    <div className="flex flex-wrap items-start gap-3">
      <code className="font-mono text-[0.95rem] leading-relaxed text-ink-2 break-all">{groups.join(" ")}</code>
      <CopyButton text={value} label="Copiar código" />
    </div>
  );
}

export function CopyButton({ text, label }: { text: string; label: string }) {
  const [done, setDone] = useState(false);
  return (
    <Button variant="ghost" className="!w-auto" onClick={async () => { try { await navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 2000); } catch { /* clipboard unavailable */ } }}>
      {done ? <Check size={18} aria-hidden /> : <Copy size={18} aria-hidden />} {done ? "Copiado" : label}
    </Button>
  );
}

/* Read aloud with the device voice (Web Speech API), pt-BR, no external service. */
export function SpeakButton({ text, label = "Ouvir" }: { text: string; label?: string }) {
  const [speaking, setSpeaking] = useState(false);
  const supported = useSyncExternalStore(() => () => {}, () => "speechSynthesis" in window, () => false);
  useEffect(() => () => { if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel(); }, []);
  if (!supported) return null;
  return (
    <Button variant="ghost" aria-pressed={speaking} onClick={() => {
      if (speaking) { window.speechSynthesis.cancel(); setSpeaking(false); return; }
      const u = new SpeechSynthesisUtterance(text); u.lang = "pt-BR"; u.rate = 0.95;
      u.onend = () => setSpeaking(false); u.onerror = () => setSpeaking(false);
      setSpeaking(true); window.speechSynthesis.speak(u);
    }}>
      {speaking ? <Square size={18} aria-hidden /> : <Volume2 size={18} aria-hidden />} {speaking ? "Pausar" : label}
    </Button>
  );
}

/* LeIA: v3 accounts. Navy bar for the signed-in screens: logo, who is signed in, panel and sign-out links. */
export function AppHeader({ right }: { right?: ReactNode }) {
  return (
    <header className="no-print -mx-4 mb-4 flex min-h-[56px] items-center justify-between gap-3 bg-navy px-4 py-2 text-paper">
      <Link href="/" aria-label="LeIA, página inicial" className="inline-flex min-h-[44px] items-center">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo-horizontal-dark.svg" alt="LeIA" className="h-7" />
      </Link>
      {right}
    </header>
  );
}

export function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="grid gap-1.5">
      <label htmlFor={id} className="font-bold">{label}</label>
      {children}
      {hint && <p className="text-[0.95rem] text-ink-2">{hint}</p>}
    </div>
  );
}
export const inputClass = "min-h-[48px] w-full rounded-button border-2 border-line bg-surface px-3 text-[1.05rem] focus:border-teal-deep";

export function Page({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return <main className={`mx-auto w-full flex-1 px-4 pb-6 ${wide ? "max-w-[760px]" : "max-w-[560px] md:max-w-[680px]"}`}>{children}</main>;
}
