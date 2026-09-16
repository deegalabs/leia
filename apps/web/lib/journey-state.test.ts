import { describe, expect, it } from "vitest";
import { firstUnanswered, keptAfterRetry, restore } from "./journey-state";

const b = { topics: 6, questions: 3 };

describe("o lugar dela na jornada", () => {
  it("devolve a pessoa ao ponto onde estava", () => {
    const r = restore(JSON.stringify({ answers: {}, result: null, step: { kind: "topic", n: 3 } }), b);
    expect(r.step).toEqual({ kind: "topic", n: 3 });
  });

  it("aceita o formato antigo, sem etapa gravada", () => {
    const r = restore(JSON.stringify({ answers: { "1": 2 }, result: null }), b);
    expect(r.answers).toEqual({ "1": 2 });
    expect(r.step).toBeUndefined();
  });

  it("não manda para um ponto que o documento não tem mais", () => {
    expect(restore(JSON.stringify({ step: { kind: "topic", n: 40 } }), b).step).toBeUndefined();
    expect(restore(JSON.stringify({ step: { kind: "question", k: 9 } }), b).step).toBeUndefined();
  });

  it("só reabre no comprovante quando ele foi aprovado", () => {
    expect(restore(JSON.stringify({ result: { aprovado: true } }), b).step).toEqual({ kind: "result" });
    expect(restore(JSON.stringify({ result: { aprovado: false }, step: { kind: "topic", n: 1 } }), b).step).toEqual({ kind: "topic", n: 1 });
  });

  it("não quebra com lixo gravado", () => {
    expect(restore("{{{", b)).toEqual({});
    expect(restore(null, b)).toEqual({});
  });
});

describe("errar uma pergunta", () => {
  it("preserva o que ela acertou", () => {
    expect(keptAfterRetry({ "1": 0, "2": 1, "3": 2 }, [{ id: 2 }])).toEqual({ "1": 0, "3": 2 });
  });

  it("devolve ela para a pergunta que falta, não para a primeira", () => {
    const qs = [{ id: 1 }, { id: 2 }, { id: 3 }];
    expect(firstUnanswered(qs, { "1": 0, "3": 2 })).toBe(1);
  });

  it("volta ao começo quando não falta nenhuma", () => {
    expect(firstUnanswered([{ id: 1 }], { "1": 0 })).toBe(0);
  });
});
