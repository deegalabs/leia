/* The app talks to the cognitive service; the browser talks only to the app.
   That is what lets the session live in a cookie the page cannot read: a cookie does not cross origins,
   so the call has to leave from this side. SERVICE_URL is server only and never reaches the bundle.
   With no service configured the app answers from the in-app mock (lib/mock.ts), which is the hosted demo. */
import { authHeader } from "./session";

export const serviceBase = () =>
  (process.env.SERVICE_URL ?? process.env.NEXT_PUBLIC_API_BASE ?? "").replace(/\/$/, "");

export const hasService = () => serviceBase() !== "";

/* Hop-by-hop and browser-owned headers never go upstream. The cookie in particular: it belongs to this
   origin, and forwarding it would hand the service a credential it did not issue. */
const DROP = new Set(["host", "connection", "cookie", "content-length", "authorization", "accept-encoding"]);

function upstreamHeaders(req: Request): Headers {
  const h = new Headers();
  req.headers.forEach((value, key) => { if (!DROP.has(key.toLowerCase())) h.set(key, value); });
  for (const [key, value] of Object.entries(authHeader(req))) h.set(key, value);
  return h;
}

/* Streaming responses (the chat is server-sent events) must not be buffered here. */
function downstreamHeaders(from: Headers): Headers {
  const h = new Headers();
  for (const key of ["content-type", "content-disposition", "cache-control"]) {
    const v = from.get(key);
    if (v) h.set(key, v);
  }
  if (!h.has("cache-control")) h.set("cache-control", "no-store");
  return h;
}

/* Forwards the request as it came, to the same path on the service unless one is given.
   Returns null when there is no service, so the caller falls back to the mock. */
export async function viaService(req: Request, path?: string): Promise<Response | null> {
  if (!hasService()) return null;
  const from = new URL(req.url);
  const target = new URL(serviceBase() + (path ?? from.pathname));
  if (!path) target.search = from.search;

  const method = req.method.toUpperCase();
  const init: RequestInit & { duplex?: "half" } = { method, headers: upstreamHeaders(req), redirect: "manual" };
  if (method !== "GET" && method !== "HEAD") { init.body = req.body; init.duplex = "half"; }

  const upstream = await fetch(target, init);
  return new Response(upstream.body, { status: upstream.status, headers: downstreamHeaders(upstream.headers) });
}

/* Same as viaService, but reads the body as JSON so the caller can act on it (the session routes do). */
export async function callService(req: Request, path: string, body: unknown): Promise<{ status: number; data: Record<string, unknown> }> {
  const r = await fetch(serviceBase() + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json", ...authHeader(req) },
    body: JSON.stringify(body ?? {}),
  });
  const data = (await r.json().catch(() => ({}))) as Record<string, unknown>;
  return { status: r.status, data };
}

export async function getService(req: Request, path: string): Promise<{ status: number; data: Record<string, unknown> }> {
  const r = await fetch(serviceBase() + path, {
    headers: { Accept: "application/json", ...authHeader(req) },
    cache: "no-store",
  });
  const data = (await r.json().catch(() => ({}))) as Record<string, unknown>;
  return { status: r.status, data };
}
