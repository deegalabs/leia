/* A sessão é a credencial de quem enviou ou de quem recebeu um documento jurídico.
   Enquanto o token vive no armazenamento do navegador, qualquer script que rode na origem do app
   consegue lê-lo, e a área de documentação aceita contribuição de fora.
   O contrato testado aqui: o cliente conhece a pessoa, nunca o token. */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

let toques: string[];

beforeEach(() => {
  vi.resetModules();
  toques = [];
  const storage = {
    length: 0,
    getItem: (k: string) => { toques.push(`ler ${k}`); return null; },
    setItem: (k: string) => { toques.push(`gravar ${k}`); },
    removeItem: (k: string) => { toques.push(`apagar ${k}`); },
    clear: () => { toques.push("limpar"); },
    key: () => null,
  };
  vi.stubGlobal("localStorage", storage);
  vi.stubGlobal("sessionStorage", storage);
  vi.stubGlobal("window", { localStorage: storage, sessionStorage: storage, addEventListener() {}, removeEventListener() {}, dispatchEvent: () => true });
  vi.stubGlobal("document", { cookie: "" });
});
afterEach(() => vi.unstubAllGlobals());

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const CIDADA = { id: 2, nome: "Cidadã Exemplo", email: "cidada@exemplo.leia", papel: "cidadao" };

describe("sessão no cliente", () => {
  it("entra sem gravar nada no navegador e sem receber o token", async () => {
    const chamadas: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      chamadas.push(String(input));
      return json({ usuario: CIDADA });
    }));

    const { login } = await import("./auth");
    const usuario = await login("cidada@exemplo.leia", "leia1234");

    expect(usuario).toMatchObject({ id: 2, papel: "cidadao" });
    expect(JSON.stringify(usuario)).not.toMatch(/token/i);
    expect(toques).toEqual([]);
    expect(chamadas[0]).toBe("/api/auth/login");
  });

  it("sai sem tocar no armazenamento do navegador", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => json({ ok: true })));
    const { logout } = await import("./auth");
    await logout();
    expect(toques).toEqual([]);
  });

  it("não oferece ao navegador um jeito de montar o cabeçalho de autorização", async () => {
    const mod = await import("./auth");
    expect(Object.keys(mod)).not.toContain("authHeaders");
  });
});
