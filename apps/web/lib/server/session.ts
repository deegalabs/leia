/* The session token of the cognitive service, kept where page scripts cannot reach it.
   The browser only ever sees the person; the token travels between this app and the service. */

export const SESSION_COOKIE = "leia_session";
/* Same window the service gives a token. Shorter is a better default than "until the browser closes". */
const MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

const secure = () => process.env.NODE_ENV === "production";

function serialize(value: string, maxAge: number): string {
  const parts = [`${SESSION_COOKIE}=${value}`, "Path=/", "HttpOnly", "SameSite=Lax", `Max-Age=${maxAge}`];
  if (secure()) parts.push("Secure");
  return parts.join("; ");
}

export const sessionCookie = (token: string) => serialize(token, MAX_AGE_SECONDS);
export const clearSessionCookie = () => serialize("", 0);

export function tokenFromRequest(req: Request): string | null {
  const header = req.headers.get("cookie");
  if (!header) return null;
  for (const part of header.split(";")) {
    const i = part.indexOf("=");
    if (i < 0) continue;
    if (part.slice(0, i).trim() !== SESSION_COOKIE) continue;
    const value = part.slice(i + 1).trim();
    return value || null;
  }
  return null;
}

/* The service still speaks Bearer; the translation from cookie to header happens here and nowhere else. */
export function authHeader(req: Request): Record<string, string> {
  const token = tokenFromRequest(req);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function withSession(res: Response, token: string): Response {
  res.headers.append("Set-Cookie", sessionCookie(token));
  return res;
}

export function withoutSession(res: Response): Response {
  res.headers.append("Set-Cookie", clearSessionCookie());
  return res;
}
