import { servidorFalso } from "@/test/utilitarios";

import { api, ErroApi, gerarNovamente, mensagemDoCorpo } from "./cliente";

describe("mensagemDoCorpo", () => {
  it("usa a mensagem dos erros da aplicação", () => {
    expect(mensagemDoCorpo({ erro: { codigo: "nao_encontrado", mensagem: "Prova não encontrada." } }, 404)).toEqual({
      mensagem: "Prova não encontrada.",
      codigo: "nao_encontrado",
    });
  });

  it("usa a primeira mensagem dos erros de validação, sem o prefixo do Pydantic", () => {
    const corpo = { detail: [{ msg: "Value error, A prova precisa de pelo menos uma questão." }] };
    expect(mensagemDoCorpo(corpo, 422).mensagem).toBe("A prova precisa de pelo menos uma questão.");
  });

  it("tem uma mensagem genérica para erros sem corpo", () => {
    expect(mensagemDoCorpo(null, 502).mensagem).toMatch(/servidor/);
  });
});

describe("api", () => {
  it("monta a consulta só com os filtros preenchidos", async () => {
    const { chamadas } = servidorFalso({ "GET /provas": () => ({ itens: [], total: 0, pagina: 1, por_pagina: 5 }) });

    await api.listarProvas({ busca: "redes", dificuldade: undefined, pagina: 2 });

    expect(chamadas[0]!.url.search).toBe("?busca=redes&pagina=2");
  });

  it("transforma respostas de erro em ErroApi", async () => {
    servidorFalso({ "GET /provas/x": () => ({ status: 404, corpo: { erro: { codigo: "nao_encontrado", mensagem: "Não achei." } } }) });

    await expect(api.obterProva("x")).rejects.toMatchObject({ status: 404, message: "Não achei." });
  });

  it("explica quando o backend está fora do ar", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(api.saude()).rejects.toBeInstanceOf(ErroApi);
  });

  it("gera novamente com o mesmo material e a mesma configuração", async () => {
    const configuracao = { dificuldade: "facil", multipla_escolha: 3, dissertativas: 0, verdadeiro_falso: 0 };
    const { chamadas } = servidorFalso({
      "GET /provas/p1": () => ({ id: "p1", titulo: "Redes", documento_id: "d1", configuracao }),
      "POST /provas": () => ({ status: 202, corpo: { id: "p2" } }),
    });

    await gerarNovamente("p1");

    expect(chamadas[1]!.corpo).toEqual({ documento_id: "d1", titulo: "Redes", configuracao });
  });
});
