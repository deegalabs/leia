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

/* A conta criada pela confirmação de nome é a que mais precisa desta regra. Ela nasce sem e-mail e sem
   senha, então o token **é** a conta inteira: quem o lê vira a pessoa, e não há senha para trocar depois.
   Se ele voltasse no corpo, qualquer script rodando na origem do app o alcançaria, inclusive um que tenha
   entrado pela área de documentação, que aceita contribuição de fora. */
describe("confirmação de nome pela rota do app", () => {
  it("devolve a pessoa no corpo e o token só no cookie HttpOnly", async () => {
    vi.unstubAllGlobals();   // a rota roda no servidor: precisa do fetch e do storage de verdade
    const { issueInvite, login } = await import("./mock");
    const advogada = login({ email: "advogada@exemplo.leia", senha: "leia1234" });
    const { POST } = await import("@/app/api/t/[hash]/confirm-name/route");

    const { userFromRequest } = await import("./mock");
    const conta = userFromRequest(new Request("http://t/", { headers: { cookie: `leia_session=${advogada.token}` } }))!;
    issueInvite(conta, 1, { nome: "Maria Souza" });

    const res = await POST(new Request("http://t/api/t/demo/confirm-name", { method: "POST" }),
                           { params: Promise.resolve({ hash: "demo" }) });
    const corpo = await res.clone().json();

    expect(res.status).toBe(200);
    expect(corpo).not.toHaveProperty("token");
    expect(JSON.stringify(corpo)).not.toMatch(/token/i);

    const cookie = res.headers.get("set-cookie") ?? "";
    expect(cookie).toContain("leia_session=");
    expect(cookie).toContain("HttpOnly");
  });
});
