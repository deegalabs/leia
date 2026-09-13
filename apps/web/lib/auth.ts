/* Session for the v3 accounts (docs/API-V3-CONTRACT.md): Bearer token plus user, kept in localStorage under
   "leia:auth". Same origin rules as lib/api.ts: NEXT_PUBLIC_API_BASE empty means the in-app mock. */
import { useMemo, useSyncExternalStore } from "react";
import { API_BASE } from "./api";

export type Role = "cidadao" | "advogado" | "fornecedor";
export type Usuario = { id: number; nome: string; email: string; papel: Role };
export type Auth = { token: string; usuario: Usuario };
export type ApiError = Error & { status?: number };

export const AUTH_KEY = "leia:auth";
const CHANGE_EVENT = "leia:auth-change";

function readRaw(): string | null {
  try { return typeof window === "undefined" ? null : localStorage.getItem(AUTH_KEY); } catch { return null; }
}
function parse(raw: string | null): Auth | null {
  if (!raw) return null;
  try {
    const a = JSON.parse(raw);
    return a && typeof a.token === "string" && a.usuario && typeof a.usuario.id === "number" ? (a as Auth) : null;
  } catch { return null; }
}
function write(auth: Auth | null) {
  try { if (auth) localStorage.setItem(AUTH_KEY, JSON.stringify(auth)); else localStorage.removeItem(AUTH_KEY); } catch { /* storage unavailable */ }
  if (typeof window !== "undefined") window.dispatchEvent(new Event(CHANGE_EVENT));
}

export const getAuth = (): Auth | null => parse(readRaw());
export function authHeaders(): Record<string, string> {
  const a = getAuth();
  return a ? { Authorization: `Bearer ${a.token}` } : {};
}

async function post<T>(path: string, body: unknown, withAuth = false): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json", ...(withAuth ? authHeaders() : {}) }, body: JSON.stringify(body),
  });
  if (!r.ok) {
    const e: ApiError = new Error(`HTTP ${r.status}`); e.status = r.status;
    throw e;
  }
  return r.json();
}

export async function login(email: string, senha: string): Promise<Auth> {
  const a = await post<Auth>("/api/auth/login", { email, senha });
  write(a);
  return a;
}
export async function cadastro(input: { nome: string; email: string; senha: string; papel: "cidadao" | "advogado"; oab?: string }): Promise<Auth> {
  const a = await post<Auth>("/api/auth/cadastro", input);
  write(a);
  return a;
}
export async function logout(): Promise<void> {
  try { if (getAuth()) await post("/api/auth/logout", {}, true); } catch { /* the token is dropped locally anyway */ }
  write(null);
}
/* Confirms the stored token with the service; a 401 clears the local session. */
export async function me(): Promise<Usuario | null> {
  const a = getAuth();
  if (!a) return null;
  const r = await fetch(`${API_BASE}/api/auth/me`, { headers: { Accept: "application/json", ...authHeaders() }, cache: "no-store" });
  if (r.status === 401) { write(null); return null; }
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const { usuario } = (await r.json()) as { usuario: Usuario };
  write({ token: a.token, usuario });
  return usuario;
}

function subscribe(cb: () => void) {
  window.addEventListener(CHANGE_EVENT, cb);
  window.addEventListener("storage", cb);
  return () => { window.removeEventListener(CHANGE_EVENT, cb); window.removeEventListener("storage", cb); };
}

/* "use client" only. ready=false while hydrating, so screens do not redirect before the session is read. */
export function useAuth() {
  const raw = useSyncExternalStore(subscribe, readRaw, () => null);
  const ready = useSyncExternalStore(() => () => {}, () => true, () => false);
  const auth = useMemo(() => parse(raw), [raw]);
  const usuario = auth?.usuario ?? null;
  return { auth, usuario, ready, isLawyer: usuario?.papel === "advogado" || usuario?.papel === "fornecedor", isCitizen: usuario?.papel === "cidadao" };
}
