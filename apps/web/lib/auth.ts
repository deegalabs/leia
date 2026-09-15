/* Session for the v3 accounts (docs/API-V3-CONTRACT.md), as the browser sees it: the person, never the token.
   The token is held by this app's server in an HttpOnly cookie (lib/server/session.ts) and attached to the
   service call there. Nothing here writes to browser storage, so a script running on the page has nothing to read. */
import { useEffect, useSyncExternalStore } from "react";

export type Role = "cidadao" | "advogado" | "fornecedor";
export type Usuario = { id: number; nome: string; email: string; papel: Role };
export type ApiError = Error & { status?: number };

type Estado = { usuario: Usuario | null; pronto: boolean };
/* Stable reference: the server render and the first client render must agree. */
const INICIAL: Estado = { usuario: null, pronto: false };

let estado: Estado = INICIAL;
const ouvintes = new Set<() => void>();

function definir(next: Estado) {
  estado = next;
  for (const cb of ouvintes) cb();
}

async function chamar<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, {
    ...init,
    credentials: "same-origin",
    headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers },
    cache: "no-store",
  });
  if (!r.ok) {
    const e: ApiError = new Error(`HTTP ${r.status}`);
    e.status = r.status;
    throw e;
  }
  return r.json() as Promise<T>;
}

export async function login(email: string, senha: string): Promise<Usuario> {
  const { usuario } = await chamar<{ usuario: Usuario }>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, senha }) });
  definir({ usuario, pronto: true });
  return usuario;
}

export async function cadastro(input: { nome: string; email: string; senha: string; papel: "cidadao" | "advogado"; oab?: string }): Promise<Usuario> {
  const { usuario } = await chamar<{ usuario: Usuario }>("/api/auth/cadastro", { method: "POST", body: JSON.stringify(input) });
  definir({ usuario, pronto: true });
  return usuario;
}

export async function logout(): Promise<void> {
  try { await chamar("/api/auth/logout", { method: "POST", body: "{}" }); } catch { /* the cookie is dropped by the server either way */ }
  definir({ usuario: null, pronto: true });
}

/* Asks the server who the cookie belongs to. A session the service no longer accepts comes back empty. */
export async function me(): Promise<Usuario | null> {
  try {
    const { usuario } = await chamar<{ usuario: Usuario }>("/api/auth/me");
    definir({ usuario, pronto: true });
    return usuario;
  } catch {
    definir({ usuario: null, pronto: true });
    return null;
  }
}

let emCurso: Promise<Usuario | null> | null = null;
/* One request per page load, shared by every component that asks. */
export function carregarSessao(): Promise<Usuario | null> {
  if (!emCurso) emCurso = me().finally(() => { emCurso = null; });
  return emCurso;
}

function subscribe(cb: () => void) {
  ouvintes.add(cb);
  return () => { ouvintes.delete(cb); };
}

/* "use client" only. ready=false until the server answers who is signed in, so screens do not redirect early. */
export function useAuth() {
  const s = useSyncExternalStore(subscribe, () => estado, () => INICIAL);
  useEffect(() => { if (!s.pronto) void carregarSessao(); }, [s.pronto]);
  const usuario = s.usuario;
  return { usuario, ready: s.pronto, isLawyer: usuario?.papel === "advogado" || usuario?.papel === "fornecedor", isCitizen: usuario?.papel === "cidadao" };
}
