"use client";
import { useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { cadastro, login, useAuth, type ApiError } from "@/lib/auth";
import { m } from "@/lib/i18n";
import { AppHeader, Button, Card, Field, Page, inputClass } from "./ui";

type Mode = "entrar" | "cadastro";
const safeNext = (n: string | null) => (n && n.startsWith("/") && !n.startsWith("//") ? n : "/painel");

export function AuthForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNext(params.get("next"));
  const { usuario, ready } = useAuth();
  const [mode, setMode] = useState<Mode>(params.get("modo") === "cadastro" ? "cadastro" : "entrar");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [papel, setPapel] = useState<"cidadao" | "advogado">("cidadao");
  const [oab, setOab] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (!email.trim() || !senha || (mode === "cadastro" && !nome.trim())) { setError(m.auth.errors.required); return; }
    setBusy(true); setError(null);
    try {
      if (mode === "entrar") await login(email.trim(), senha);
      else await cadastro({ nome: nome.trim(), email: email.trim(), senha, papel, oab: papel === "advogado" && oab.trim() ? oab.trim() : undefined });
      router.push(next);
    } catch (err) {
      const s = (err as ApiError).status;
      setError(s === 401 ? m.auth.errors.invalid : s === 409 ? m.auth.errors.exists : s === 403 ? m.auth.errors.notAllowed : m.auth.errors.generic);
    } finally { setBusy(false); }
  }

  const tab = (value: Mode, label: string) => (
    <button type="button" role="tab" aria-selected={mode === value} onClick={() => { setMode(value); setError(null); }}
      className={`min-h-[48px] flex-1 rounded-button font-bold ${mode === value ? "bg-teal-deep text-white" : "text-teal-deep hover:bg-teal-soft"}`}>{label}</button>
  );

  return (
    <Page>
      <AppHeader />
      <h1 className="mb-1 text-[1.5rem]">{mode === "entrar" ? m.auth.signIn : m.auth.signUp}</h1>
      <p className="mb-4 text-ink-2">{mode === "entrar" ? m.auth.signInHint : m.auth.signUpHint}</p>
      {ready && usuario && <p className="mb-3 text-[0.95rem] text-ink-2">Você já está com a conta de {usuario.nome} aberta. Entrar de novo troca de conta.</p>}
      <Card>
        <div role="tablist" aria-label="Entrar ou criar conta" className="mb-4 flex gap-1 rounded-button border-2 border-line p-1">
          {tab("entrar", m.auth.signIn)}{tab("cadastro", m.auth.signUp)}
        </div>
        <form onSubmit={submit} className="grid gap-4" noValidate>
          {mode === "cadastro" && (
            <Field id="nome" label={m.auth.name}><input id="nome" className={inputClass} value={nome} onChange={(e) => setNome(e.target.value)} autoComplete="name" /></Field>
          )}
          <Field id="email" label={m.auth.email}><input id="email" type="email" className={inputClass} value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" inputMode="email" /></Field>
          <Field id="senha" label={m.auth.password}><input id="senha" type="password" className={inputClass} value={senha} onChange={(e) => setSenha(e.target.value)} autoComplete={mode === "entrar" ? "current-password" : "new-password"} /></Field>
          {mode === "cadastro" && (
            <fieldset className="grid gap-2">
              <legend className="mb-1 font-bold">{m.auth.role}</legend>
              {([["cidadao", m.auth.roleCitizen], ["advogado", m.auth.roleLawyer]] as const).map(([value, label]) => (
                <label key={value} className={`flex min-h-[52px] cursor-pointer items-center gap-3 rounded-button border-2 px-3.5 ${papel === value ? "border-teal-deep bg-[#F1F8F8]" : "border-line"}`}>
                  <input type="radio" name="papel" value={value} checked={papel === value} onChange={() => setPapel(value)} className="h-5 w-5 accent-teal-deep" />
                  <span className="text-[1.05rem]">{label}</span>
                </label>
              ))}
              {papel === "advogado" && (
                <Field id="oab" label={m.auth.oabOptional}><input id="oab" className={inputClass} value={oab} onChange={(e) => setOab(e.target.value)} placeholder="PR 123456" /></Field>
              )}
            </fieldset>
          )}
          {error && <p role="alert" className="text-danger">{error}</p>}
          <Button type="submit" disabled={busy}>{busy ? m.common.loading : mode === "entrar" ? m.auth.submitSignIn : m.auth.submitSignUp}</Button>
        </form>
      </Card>
    </Page>
  );
}
