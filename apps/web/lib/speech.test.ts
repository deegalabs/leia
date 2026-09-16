import { describe, expect, it } from "vitest";
import { ptBrVoice, spokenText } from "./speech";

describe("o que a voz lê", () => {
  it("não lê asterisco de negrito nem traço de lista", () => {
    const s = spokenText("## O que você paga\n\n- **Vinte por cento** ao final\n- Custas por sua conta");
    expect(s).not.toMatch(/[*#]/);
    expect(s).not.toMatch(/^- /m);
    expect(s).toContain("Vinte por cento ao final");
  });

  it("não lê o nome do emoji do título", () => {
    expect(spokenText("📄 Onde a história está agora")).toBe("Onde a história está agora");
  });

  it("não lê o endereço de um link, só o texto dele", () => {
    expect(spokenText("veja o [comprovante](https://exemplo.test/x)")).toBe("veja o comprovante");
  });

  it("junta linhas soltas em frase, sem deixar espaço dobrado", () => {
    expect(spokenText("Primeira linha\n\n\nSegunda linha")).toBe("Primeira linha. Segunda linha");
  });

  it("aguenta texto vazio", () => {
    expect(spokenText("")).toBe("");
  });
});

describe("achar uma voz em português", () => {
  const v = (lang: string, name = lang) => ({ lang, name }) as SpeechSynthesisVoice;

  it("prefere pt-BR", () => {
    expect(ptBrVoice([v("en-US"), v("pt-PT"), v("pt-BR")])?.lang).toBe("pt-BR");
  });

  it("aceita outro português quando não há pt-BR", () => {
    expect(ptBrVoice([v("en-US"), v("pt-PT")])?.lang).toBe("pt-PT");
  });

  it("devolve nada quando o aparelho não tem português", () => {
    // É o caso do Android básico sem o pacote de voz: hoje o botão falha calado.
    expect(ptBrVoice([v("en-US"), v("es-ES")])).toBeNull();
  });
});
