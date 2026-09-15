/* A rota de entrada é onde o token nasce para o navegador. Ele tem que ficar no cookie e nunca no corpo,
   senão o cookie é só decoração e o token continua ao alcance de qualquer script da página. */
import { describe, expect, it } from "vitest";

import { SESSION_COOKIE } from "@/lib/server/session";
import { POST } from "./route";

const pedido = (body: unknown) =>
  new Request("https://leia.test/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

describe("entrar", () => {
  it("guarda o token no cookie e devolve só a pessoa", async () => {
    const r = await POST(pedido({ email: "cidada@exemplo.leia", senha: "leia1234" }));
    expect(r.status).toBe(200);

    const cookie = r.headers.get("set-cookie") ?? "";
    expect(cookie).toContain(`${SESSION_COOKIE}=`);
    expect(cookie).toMatch(/HttpOnly/i);

    const token = cookie.split(";")[0].split("=")[1];
    expect(token.length).toBeGreaterThan(8);

    const body = (await r.json()) as Record<string, unknown>;
    expect((body.usuario as { email: string }).email).toBe("cidada@exemplo.leia");
    expect(body.token).toBeUndefined();
    expect(JSON.stringify(body)).not.toContain(token);
  });

  it("recusa senha errada sem abrir sessão", async () => {
    const r = await POST(pedido({ email: "cidada@exemplo.leia", senha: "errada" }));
    expect(r.status).toBe(401);
    expect(r.headers.get("set-cookie")).toBeNull();
  });
});
