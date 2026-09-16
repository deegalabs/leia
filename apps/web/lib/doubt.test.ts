import { describe, expect, it } from "vitest";
import { CONTEXT_TURNS, doubtPayload } from "./doubt";

const conversa = [
  { role: "bot" as const, text: "Pode perguntar com suas palavras." },
  { role: "user" as const, text: "Quanto eu pago se perder?" },
  { role: "bot" as const, text: "A cláusula 3 diz que você paga as custas." },
  { role: "user" as const, text: "E se eu desistir?" },
  { role: "bot" as const, text: "Não está escrito no documento." },
];

describe("o que sai do aparelho quando ela encaminha a dúvida", () => {
  it("manda só a pergunta dela, por padrão", () => {
    // A tela promete que a conversa é dela. Então o padrão tem que ser o que a promessa diz,
    // e não o contrário com um aviso em letra pequena.
    const p = doubtPayload(conversa, false);
    expect(p).not.toBeNull();
    expect(p!.texto).toBe("E se eu desistir?");
    expect(p!.contexto).toEqual([]);
  });

  it("manda a conversa junto quando ela escolhe", () => {
    const p = doubtPayload(conversa, true);
    expect(p!.contexto.length).toBe(4);
    expect(p!.contexto[0].text).toBe("Quanto eu pago se perder?");
    expect(p!.contexto.some((x) => x.text.includes("Pode perguntar"))).toBe(false);
  });

  it("não manda mais do que os últimos turnos combinados", () => {
    const longa = [conversa[0], ...Array.from({ length: 40 }, (_, i) => ({ role: (i % 2 ? "bot" : "user") as "user" | "bot", text: `t${i}` }))];
    expect(doubtPayload(longa, true)!.contexto.length).toBe(CONTEXT_TURNS);
  });

  it("não deixa encaminhar sem pergunta nenhuma", () => {
    expect(doubtPayload([conversa[0]], true)).toBeNull();
  });

  it("encaminha a última pergunta, não a primeira", () => {
    expect(doubtPayload(conversa, false)!.texto).toBe("E se eu desistir?");
  });
});
