/* A mensagem que ela manda para si mesma leva o endereço do documento e nada mais.
 *
 * A tentação é caprichar e pôr o título junto, para ficar claro do que se trata. Mas a mensagem vai parar
 * na conversa de alguém, e o título de um documento jurídico costuma ser o pior pedaço dele: "execução de
 * alimentos", "ação de despejo", "inventário". Quem lê por cima do ombro dela na fila do ônibus não precisa
 * saber disso, e o endereço sozinho já faz o trabalho inteiro, porque é ele que reabre o documento. */
import { describe, expect, it } from "vitest";

import { resumeMessage, whatsappLink } from "./resume";

const URL_DOC = "https://leia.exemplo/t/abc123";

describe("mensagem de retomada", () => {
  it("leva o endereço do documento", () => {
    expect(resumeMessage(URL_DOC)).toContain(URL_DOC);
  });

  it("não leva nada do conteúdo do documento", () => {
    const titulo = "Execução de alimentos";
    expect(resumeMessage(URL_DOC, titulo)).not.toContain(titulo);
    expect(resumeMessage(URL_DOC, titulo).toLowerCase()).not.toContain("alimentos");
  });

  it("vira link de WhatsApp com a mensagem codificada e sem número de destino", () => {
    const link = whatsappLink(resumeMessage(URL_DOC));
    expect(link.startsWith("https://wa.me/?text=")).toBe(true);
    // Sem número: quem escolhe para quem mandar é ela, na tela do próprio WhatsApp.
    expect(link).not.toMatch(/wa\.me\/\d/);
    expect(decodeURIComponent(link.slice("https://wa.me/?text=".length))).toContain(URL_DOC);
  });
});
