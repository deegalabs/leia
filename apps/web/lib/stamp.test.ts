/* The screen promised "the stamp arrives in a few minutes" for every receipt without a proof, including the
   ones nobody was stamping. That promise only holds while a calendar still owes an answer, so the sentence is
   chosen by the state the service reports, never by the absence of the .ots file. */
import { describe, expect, it } from "vitest";

import { stampView } from "./stamp";

const base = { otsPresent: false, otsState: "ausente" as const, otsBlockHeight: null, otsLastAttempt: null };

describe("o que a tela pode dizer sobre o carimbo", () => {
  it("sem carimbo, diz a verdade e não promete prazo", () => {
    const v = stampView(base);
    expect(v.state).toBe("ausente");
    expect(v.tone).toBe("neutral");
    expect(v.text).not.toMatch(/minutos?/i);
    expect(v.text).toMatch(/ainda não/i);
  });

  it("carimbo em andamento, aí sim diz que está sendo carimbado", () => {
    const v = stampView({ ...base, otsPresent: true, otsState: "pendente", otsLastAttempt: "2026-09-17T20:37:42Z" });
    expect(v.state).toBe("pendente");
    expect(v.tone).toBe("pending");
    expect(v.text).toMatch(/sendo feito/i);
  });

  it("carimbo confirmado, diz desde quando a prova existe", () => {
    const v = stampView({ ...base, otsPresent: true, otsState: "confirmado", otsBlockHeight: 912345 });
    expect(v.state).toBe("confirmado");
    expect(v.tone).toBe("ok");
    expect(v.text).toContain("912345");
  });

  it("confirmado sem a altura do bloco, não deixa o espaço em branco na frase", () => {
    const v = stampView({ ...base, otsPresent: true, otsState: "confirmado" });
    expect(v.text).not.toContain("{");
    expect(v.text).toMatch(/Bitcoin/);
  });

  it("resposta antiga, só com otsPresent, não inventa confirmação", () => {
    /* otsPresent === (otsState !== "ausente"): alone it cannot tell a promise from a proof in a block */
    expect(stampView({ otsPresent: true }).state).toBe("pendente");
    expect(stampView({ otsPresent: false }).state).toBe("ausente");
  });

  it("estado desconhecido não vira promessa", () => {
    expect(stampView({ otsPresent: false, otsState: "carimbando" }).state).toBe("ausente");
  });

  it("a prova só é oferecida para baixar quando existe", () => {
    expect(stampView(base).hasProof).toBe(false);
    expect(stampView({ ...base, otsPresent: true, otsState: "pendente" }).hasProof).toBe(true);
    expect(stampView({ ...base, otsPresent: true, otsState: "confirmado" }).hasProof).toBe(true);
  });

  it("nenhuma frase usa travessão", () => {
    for (const s of ["ausente", "pendente", "confirmado"] as const) {
      const v = stampView({ otsPresent: s !== "ausente", otsState: s, otsBlockHeight: 912345 });
      expect(v.text).not.toMatch(/[—–]/);
      expect(v.chip).not.toMatch(/[—–]/);
    }
  });
});
