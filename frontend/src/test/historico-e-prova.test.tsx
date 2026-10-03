import { fireEvent, screen, waitFor, within } from "@testing-library/react";

import { PROVA_DETALHE, PROVA_RESUMO, renderizarApp, servidorFalso } from "./utilitarios";

describe("Minhas provas", () => {
  it("lista as provas do backend com estado, estatísticas e busca", async () => {
    const { chamadas } = servidorFalso({
      "GET /health": () => ({ status: "ok", versao: "0.1.0", llm_configurado: true }),
      "GET /provas/estatisticas": () => ({ total: 7, este_mes: 3 }),
      "GET /provas": () => ({
        itens: [
          PROVA_RESUMO,
          { ...PROVA_RESUMO, id: "prova-2", titulo: "Aula de banco", status: "gerando", dificuldade: "facil" },
          { ...PROVA_RESUMO, id: "prova-3", titulo: "Aula de SO", status: "falhou", dificuldade: "dificil" },
        ],
        total: 3,
        pagina: 1,
        por_pagina: 5,
      }),
    });
    renderizarApp("/minhas-provas");

    expect(await screen.findByText("Aula de redes")).toBeInTheDocument();
    expect(screen.getByText("Gerando…")).toBeInTheDocument();
    expect(screen.getByText("Falhou")).toBeInTheDocument();
    expect(await screen.findByText("7")).toBeInTheDocument();
    expect(screen.getByText("Mostrando 1–3 de 3 provas")).toBeInTheDocument();
    // Só a prova concluída pode ser baixada.
    expect(screen.getByRole("button", { name: "Baixar Aula de redes" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Baixar Aula de banco" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Buscar provas"), { target: { value: "redes" } });
    await waitFor(() =>
      expect(chamadas.some((chamada) => chamada.url.searchParams.get("busca") === "redes")).toBe(true),
    );
  });

  it("oferece as exportações da prova", async () => {
    servidorFalso({
      "GET /provas/estatisticas": () => ({ total: 1, este_mes: 1 }),
      "GET /provas": () => ({ itens: [PROVA_RESUMO], total: 1, pagina: 1, por_pagina: 5 }),
    });
    renderizarApp("/minhas-provas");

    fireEvent.click(await screen.findByRole("button", { name: "Baixar Aula de redes" }));

    const menu = screen.getByRole("menu");
    expect(within(menu).getByRole("menuitem", { name: "PDF com gabarito" })).toHaveAttribute(
      "href",
      "/api/v1/provas/prova-1/exportar?formato=pdf&versao=professor",
    );
  });

  it("pede confirmação antes de excluir", async () => {
    const { chamadas } = servidorFalso({
      "GET /provas/estatisticas": () => ({ total: 1, este_mes: 1 }),
      "GET /provas": () => ({ itens: [PROVA_RESUMO], total: 1, pagina: 1, por_pagina: 5 }),
      "DELETE /provas/prova-1": () => ({ status: 204 }),
    });
    renderizarApp("/minhas-provas");

    fireEvent.click(await screen.findByRole("button", { name: "Mais opções para Aula de redes" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Excluir" }));
    expect(chamadas.some((chamada) => chamada.metodo === "DELETE")).toBe(false);

    fireEvent.click(screen.getByRole("menuitem", { name: "Confirmar exclusão" }));
    await waitFor(() => expect(chamadas.some((chamada) => chamada.metodo === "DELETE")).toBe(true));
  });

  it("mostra um convite quando ainda não há provas", async () => {
    servidorFalso({
      "GET /provas/estatisticas": () => ({ total: 0, este_mes: 0 }),
      "GET /provas": () => ({ itens: [], total: 0, pagina: 1, por_pagina: 5 }),
    });
    renderizarApp("/minhas-provas");

    expect(await screen.findByText("Nenhuma prova por aqui ainda")).toBeInTheDocument();
  });
});

describe("Visualizar prova", () => {
  it("esconde o gabarito até ser pedido e mostra fontes e revisão", async () => {
    servidorFalso({ "GET /provas/prova-1": () => PROVA_DETALHE });
    renderizarApp("/provas/prova-1");

    expect(await screen.findByText("Qual método HTTP cria um recurso?")).toBeInTheDocument();
    expect(screen.queryByText("Resposta correta: B")).not.toBeInTheDocument();
    expect(screen.getByText("Revisor 6/10")).toHaveClass("is-flagged");
    expect(screen.getByText(/refeita 1x após a revisão/)).toBeInTheDocument();
    expect(screen.getByText("Afirmativa falsa óbvia demais.")).toBeInTheDocument();
    expect(screen.getByText("7,5")).toBeInTheDocument(); // média do revisor

    fireEvent.click(screen.getByRole("switch", { name: "Mostrar gabarito" }));

    expect(screen.getByText("Resposta correta: B")).toBeInTheDocument();
    expect(screen.getByText("POST cria recursos; os demais leem ou removem.")).toBeInTheDocument();
  });

  it("mostra o andamento de uma prova que ainda está sendo gerada", async () => {
    servidorFalso({
      "GET /provas/prova-1": () => ({
        ...PROVA_DETALHE,
        status: "gerando",
        questoes: [],
        progresso: { ...PROVA_DETALHE.progresso, status: "gerando", concluidas: 1, mensagem: "Questão 1 de 2 pronta" },
      }),
    });
    renderizarApp("/provas/prova-1");

    expect(await screen.findByText("Questão 1 de 2 pronta")).toBeInTheDocument();
    expect(screen.getByText(/1 de 2 questões prontas/)).toBeInTheDocument();
  });

  it("avisa quando a prova não existe", async () => {
    servidorFalso({});
    renderizarApp("/provas/nao-existe");

    expect(await screen.findByText("Prova não encontrada")).toBeInTheDocument();
  });
});
