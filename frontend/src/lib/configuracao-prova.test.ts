import { distribuirQuestoes, LIMITE_TOTAL, limiteDeQuestoes } from "./configuracao-prova";

describe("distribuirQuestoes", () => {
  it("reparte o total entre os tipos, começando pela ordem da tela", () => {
    expect(distribuirQuestoes(10, ["multipla_escolha", "verdadeiro_falso", "dissertativa"], "medio")).toEqual({
      dificuldade: "medio",
      multipla_escolha: 4,
      verdadeiro_falso: 3,
      dissertativas: 3,
    });
  });

  it("ignora a ordem em que os tipos foram marcados", () => {
    const configuracao = distribuirQuestoes(3, ["dissertativa", "multipla_escolha"], "facil");
    expect(configuracao.multipla_escolha).toBe(2);
    expect(configuracao.dissertativas).toBe(1);
  });

  it("respeita o limite de cada tipo e passa o excedente aos outros", () => {
    const configuracao = distribuirQuestoes(20, ["dissertativa", "verdadeiro_falso"], "dificil");
    expect(configuracao.dissertativas).toBe(10);
    expect(configuracao.verdadeiro_falso).toBe(10);
  });

  it("nunca passa do que os tipos escolhidos comportam", () => {
    expect(distribuirQuestoes(50, ["dissertativa"], "medio").dissertativas).toBe(10);
  });
});

describe("limiteDeQuestoes", () => {
  it("soma os limites dos tipos, até o teto da interface", () => {
    expect(limiteDeQuestoes(["dissertativa"])).toBe(10);
    expect(limiteDeQuestoes(["multipla_escolha", "dissertativa", "verdadeiro_falso"])).toBe(LIMITE_TOTAL);
    expect(limiteDeQuestoes([])).toBe(0);
  });
});
