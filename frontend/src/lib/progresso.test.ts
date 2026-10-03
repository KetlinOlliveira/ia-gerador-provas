import type { ProgressoProva } from "@/api/tipos";

import { avancar, estagioAtivo, faixaDePorcentagem, type FaseGeracao } from "./progresso";

function gerando(parcial: Partial<ProgressoProva>): FaseGeracao {
  return {
    tipo: "gerando",
    progresso: { status: "gerando", etapa: null, mensagem: null, concluidas: 0, total: 4, erro: null, ...parcial },
  };
}

describe("estagioAtivo", () => {
  it("acompanha as etapas reais do backend", () => {
    expect(estagioAtivo({ tipo: "enviando" })).toBe(0);
    expect(estagioAtivo(gerando({ etapa: "planejamento" }))).toBe(1);
    expect(estagioAtivo(gerando({ etapa: "geracao", concluidas: 2 }))).toBe(2);
    expect(estagioAtivo(gerando({ etapa: "geracao", concluidas: 4 }))).toBe(3);
    expect(estagioAtivo({ tipo: "concluida" })).toBe(4);
  });
});

describe("faixaDePorcentagem", () => {
  it("cresce a cada questão pronta e só chega a 100 ao concluir", () => {
    const alvos = [0, 1, 2, 3, 4].map((concluidas) => faixaDePorcentagem(gerando({ etapa: "geracao", concluidas })).alvo);
    expect(alvos).toEqual([...alvos].sort((a, b) => a - b));
    expect(Math.max(...alvos)).toBeLessThan(100);
    expect(faixaDePorcentagem({ tipo: "concluida" }).alvo).toBe(100);
  });

  it("permite avançar devagar dentro da questão atual, sem passar da próxima", () => {
    const atual = faixaDePorcentagem(gerando({ etapa: "geracao", concluidas: 1 }));
    const proxima = faixaDePorcentagem(gerando({ etapa: "geracao", concluidas: 2 }));
    expect(atual.teto).toBeGreaterThan(atual.alvo);
    expect(atual.teto).toBeLessThan(proxima.alvo);
  });
});

describe("avancar", () => {
  it("corre até o alvo, depois anda devagar até o teto e para", () => {
    expect(avancar(10, 20, 30)).toBe(12);
    expect(avancar(20, 20, 30)).toBe(20.25);
    expect(avancar(30, 20, 30)).toBe(30);
  });

  it("acelera até 100 quando a prova termina", () => {
    expect(avancar(98, 100, 100)).toBe(100);
  });
});
