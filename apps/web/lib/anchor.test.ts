/* A jornada mostra o trecho ao lado da explicação e afirma que ele foi copiado do documento.
   Essa frase é a promessa central do produto, então ela só pode aparecer quando houve conferência,
   e precisa dizer a verdade sobre como a conferência foi feita. */
import { describe, expect, it } from "vitest";

import { anchorClaim } from "./inferences";

describe("o que a tela pode afirmar sobre o trecho", () => {
  it("sem conferência, não afirma nada", () => {
    expect(anchorClaim(undefined)).toBeNull();
    expect(anchorClaim(null)).toBeNull();
  });

  it("achado igualzinho, pode dizer que é cópia exata", () => {
    const frase = anchorClaim({ metodo: "exato", score: 1 });
    expect(frase).toContain("exatamente");
  });

  it("achado com espaçamento diferente, ainda é cópia exata do que está escrito", () => {
    expect(anchorClaim({ metodo: "normalizado", score: 1 })).toContain("exatamente");
  });

  it("achado por semelhança, não pode dizer que é exato", () => {
    const frase = anchorClaim({ metodo: "aproximado", score: 0.91 });
    expect(frase).not.toBeNull();
    expect(frase).not.toContain("exatamente");
    expect(frase?.toLowerCase()).toContain("pequenas diferenças");
  });
});
