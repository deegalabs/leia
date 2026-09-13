"use client";
import { useEffect, useRef, useState } from "react";
import { Send, X } from "lucide-react";
import { chat, sendDoubt } from "@/lib/api";
import { m } from "@/lib/i18n";
import { Button } from "./ui";
import { Inline } from "./Inline";

type Msg = { role: "user" | "bot"; text: string };
const EXAMPLES = ["Quanto eu pago se perder?", "Posso desistir depois?", "Quem paga as despesas?"];

/* LeIA: v3. temAdvogado shows "send this doubt to the lawyer": the last question goes to the panel with the chat as context. */
export function ChatSheet({ hash, open, onClose, temAdvogado = false }: { hash: string; open: boolean; onClose: () => void; temAdvogado?: boolean }) {
  const [msgs, setMsgs] = useState<Msg[]>([{ role: "bot", text: "Pode perguntar com suas palavras. Eu respondo só com o que está neste documento. Se não estiver escrito, eu aviso." }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [forward, setForward] = useState<{ state: "idle" | "sending" | "sent" | "failed"; count: number }>({ state: "idle", count: 0 });
  const lastQuestion = [...msgs].reverse().find((x) => x.role === "user") ?? null;
  const userTurns = msgs.filter((x) => x.role === "user").length;
  const alreadySent = forward.state === "sent" && forward.count === userTurns;

  async function forwardToLawyer() {
    if (!lastQuestion || forward.state === "sending" || alreadySent) return;
    setForward({ state: "sending", count: userTurns });
    try { await sendDoubt(hash, lastQuestion.text, msgs.slice(1).slice(-10)); setForward({ state: "sent", count: userTurns }); }
    catch { setForward({ state: "failed", count: userTurns }); }
  }
  const bodyRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { if (open) setTimeout(() => inputRef.current?.focus(), 150); }, [open]);
  useEffect(() => { bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight }); }, [msgs]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey); return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function send(text: string) {
    const q = text.trim(); if (!q || busy) return;
    setInput(""); setBusy(true);
    setMsgs((m) => [...m, { role: "user", text: q }, { role: "bot", text: "Estou lendo o documento." }]);
    const update = (t: string) => setMsgs((m) => { const c = [...m]; c[c.length - 1] = { role: "bot", text: t }; return c; });
    try { await chat(hash, q, update); }
    catch { update("Deu um problema do nosso lado, não foi você. Tente perguntar de novo."); }
    finally { setBusy(false); }
  }

  return (
    <>
      <div className={`fixed inset-0 z-20 bg-navy/45 transition-opacity ${open ? "opacity-100" : "pointer-events-none opacity-0"}`} onClick={onClose} aria-hidden="true" />
      <div role="dialog" aria-modal="true" aria-label="Tirar dúvida com a assistente" aria-hidden={!open}
        className={`fixed inset-x-0 bottom-0 z-30 flex max-h-[85vh] flex-col rounded-t-[18px] bg-surface shadow-[0_-8px_30px_rgba(8,24,32,.25)] transition-transform md:inset-x-auto md:right-6 md:w-[440px] ${open ? "translate-y-0" : "translate-y-[105%]"}`}>
        <header className="flex items-center justify-between border-b border-line px-4 py-3">
          <h2 className="text-[1.15rem]">Tenho uma dúvida</h2>
          <Button variant="secondary" className="!w-auto !min-h-[44px]" onClick={onClose}><X size={18} aria-hidden /> Fechar</Button>
        </header>
        <div ref={bodyRef} className="flex flex-1 flex-col gap-2.5 overflow-auto px-4 py-3">
          {msgs.map((x, i) => (
            <p key={i} className={`max-w-[90%] whitespace-pre-wrap rounded-[14px] px-3.5 py-3 ${x.role === "user" ? "self-end bg-navy text-paper" : "self-start bg-muted text-ink"}`}>{x.role === "bot" ? <Inline text={x.text} /> : x.text}</p>
          ))}
          {msgs.length === 1 && (
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((e) => <button key={e} type="button" onClick={() => send(e)} className="min-h-[44px] rounded-full border-2 border-line px-3 text-[0.95rem] hover:bg-teal-soft">{e}</button>)}
            </div>
          )}
        </div>
        {temAdvogado && lastQuestion && !busy && (
          <div className="border-t border-line px-4 py-2.5">
            {alreadySent ? <p role="status" className="text-[0.95rem] text-ok">{m.doubt.sent}</p> : (
              <Button variant="secondary" className="!min-h-[44px]" disabled={forward.state === "sending"} onClick={forwardToLawyer}>
                <Send size={18} aria-hidden /> {forward.state === "sending" ? m.doubt.sending : m.doubt.sendToLawyer}
              </Button>
            )}
            {forward.state === "failed" && forward.count === userTurns && <p role="alert" className="mt-1 text-[0.95rem] text-danger">{m.doubt.sendFailed}</p>}
          </div>
        )}
        <form className="flex gap-2 border-t border-line px-4 py-3" onSubmit={(e) => { e.preventDefault(); send(input); }}>
          <label htmlFor="chat-input" className="sr-only">Sua dúvida</label>
          <input id="chat-input" ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} autoComplete="off" placeholder="Fale ou escreva sua dúvida aqui"
            className="min-h-[48px] flex-1 rounded-button border-2 border-line px-3 text-[1.05rem]" />
          <Button className="!w-auto !min-h-[48px]" disabled={busy || !input.trim()} type="submit">Enviar</Button>
        </form>
      </div>
    </>
  );
}
