/* O número da OAB só vale se atravessar inteiro: do campo do cadastro até a tela que a cidadã lê.
 *
 * Ele existia no formulário, viajava no pedido e sumia na chegada, o que é pior do que não perguntar:
 * promete uma conferência que nada consegue fazer. Aqui o número é seguido pelo lado do mock, que é o que
 * a demonstração roda; o lado do serviço é seguido por `test_oab_survives_the_signup` em `tests_v3.py`, e
 * os dois precisam dizer a mesma coisa, senão a tela funciona só num deles. */
import { beforeEach, describe, expect, it, vi } from "vitest";

beforeEach(() => vi.resetModules());

const mock = () => import("./mock");

describe("número da OAB no mock", () => {
  it("fica guardado no cadastro do advogado e volta na conta", async () => {
    const { register } = await mock();
    const { usuario } = register({ nome: "Dr. Ruy", email: "ruy@exemplo.leia", senha: "leia1234",
                                   papel: "advogado", oab: " PR 12.345 " });
    expect(usuario.oab).toBe("PR 12.345");
  });

  it("não guarda número em conta de cidadã, e a chave continua lá", async () => {
    const { register } = await mock();
    const { usuario } = register({ nome: "Joana", email: "joana@exemplo.leia", senha: "leia1234",
                                   papel: "cidadao", oab: "PR 999" });
    expect(usuario).toHaveProperty("oab", null);
  });

  it("chega à cidadã junto do nome de quem enviou", async () => {
    const { publicTaskFor } = await mock();
    expect(publicTaskFor("demo")?.advogado).toEqual({ nome: "Advogada Exemplo", oab: "PR 000000" });
  });
});
