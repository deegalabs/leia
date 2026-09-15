/* O cookie é o único lugar onde o token passa a existir do lado do navegador, e ele precisa ser
   inacessível a script, viajar só em conexão cifrada e não acompanhar requisição vinda de outro site. */
import { afterEach, describe, expect, it, vi } from "vitest";

import { SESSION_COOKIE, clearSessionCookie, sessionCookie, tokenFromRequest } from "./session";

afterEach(() => vi.unstubAllEnvs());

describe("cookie de sessão", () => {
  it("fica fora do alcance de script e não sai do site", () => {
    const c = sessionCookie("tok-123");
    expect(c.startsWith(`${SESSION_COOKIE}=tok-123;`)).toBe(true);
    expect(c).toMatch(/HttpOnly/i);
    expect(c).toMatch(/SameSite=Lax/i);
    expect(c).toMatch(/Path=\//);
    expect(c).toMatch(/Max-Age=\d+/i);
  });

  it("exige conexão cifrada quando não é desenvolvimento", () => {
    vi.stubEnv("NODE_ENV", "production");
    expect(sessionCookie("tok-123")).toMatch(/Secure/i);
  });

  it("lê o token entre outros cookies e ignora o que não é dele", () => {
    const req = new Request("https://leia.test/api/tarefas", {
      headers: { cookie: `outro=1; ${SESSION_COOKIE}=tok-9; mais=2` },
    });
    expect(tokenFromRequest(req)).toBe("tok-9");
  });

  it("devolve nulo quando não há sessão", () => {
    expect(tokenFromRequest(new Request("https://leia.test/api/tarefas"))).toBeNull();
    expect(tokenFromRequest(new Request("https://leia.test/api/tarefas", { headers: { cookie: "outro=1" } }))).toBeNull();
  });

  it("apagar a sessão expira o cookie na hora", () => {
    expect(clearSessionCookie()).toMatch(/Max-Age=0/);
    expect(clearSessionCookie()).toMatch(/HttpOnly/i);
  });
});
