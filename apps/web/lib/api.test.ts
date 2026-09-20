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

/* LeIA (E12-T09): a consulta é a diferença entre responder de memória e responder relendo o documento.
   Ela entra no hash da tentativa, do lado do serviço, e por isso precisa sair daqui junto das respostas:
   número que circula ao lado da prova sem estar dentro dela é número que qualquer um troca depois. */
describe("o que o app manda ao conferir", () => {
  it("manda as consultas junto com as respostas", async () => {
    const enviado: RequestInit[] = [];
    vi.stubGlobal("fetch", vi.fn(async (_url: string, init: RequestInit) => {
      enviado.push(init);
      return resposta(200, { aprovado: true, acertos: 6, total: 6, hash_imutavel: "h", erros: [] });
    }));
    const { submitQuiz } = await import("./api");
    await submitQuiz("abc", { "1": 0 }, { "1": 2 });
    const corpo = JSON.parse(String(enviado[0]?.body));
    expect(corpo).toEqual({ respostas: { "1": 0 }, consultas: { "1": 2 } });
  });

  it("manda consultas vazias quando ela respondeu sem reabrir nada", async () => {
    const enviado: RequestInit[] = [];
    vi.stubGlobal("fetch", vi.fn(async (_url: string, init: RequestInit) => {
      enviado.push(init);
      return resposta(200, { aprovado: true, acertos: 6, total: 6, hash_imutavel: "h", erros: [] });
    }));
    const { submitQuiz } = await import("./api");
    await submitQuiz("abc", { "1": 0 });
    expect(JSON.parse(String(enviado[0]?.body)).consultas).toEqual({});
  });
});
