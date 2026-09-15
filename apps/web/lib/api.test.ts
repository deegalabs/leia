/* Quando o serviço recusa, ele diz por quê. Se a recusa chegar ao app como "HTTP 403" e mais nada,
   a tela cai no texto genérico de erro e fica tentando de novo para sempre, e a pessoa nunca descobre
   que o link foi cancelado ou que o documento é de outra pessoa. */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getTask } from "./api";

type ErroApi = Error & { status?: number };

const resposta = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

beforeEach(() => vi.resetModules());
afterEach(() => vi.unstubAllGlobals());

describe("erro vindo do serviço", () => {
  it("chega com o código e com o motivo escrito pelo serviço", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => resposta(403, { detail: "Este link foi cancelado por quem enviou o documento." })));
    const erro = await getTask("abc").then(() => null, (e: ErroApi) => e);
    expect(erro?.status).toBe(403);
    expect(erro?.message).toBe("Este link foi cancelado por quem enviou o documento.");
  });

  it("sem motivo no corpo, ainda diz o código", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("", { status: 500 })));
    const erro = await getTask("abc").then(() => null, (e: ErroApi) => e);
    expect(erro?.status).toBe(500);
    expect(erro?.message).toContain("500");
  });
});
