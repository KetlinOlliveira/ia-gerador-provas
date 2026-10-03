import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";

import { FonteDeEventosFalsa, PROVA_DETALHE, renderizarApp, servidorFalso } from "./utilitarios";

const progresso = (parcial: object) => ({
  status: "gerando",
  etapa: "geracao",
  mensagem: null,
  concluidas: 0,
  total: 2,
  erro: null,
  ...parcial,
});

function prepararServidor() {
  return servidorFalso({
    "GET /health": () => ({ status: "ok", versao: "0.1.0", llm_configurado: true }),
    "POST /documentos": () => ({ status: 201, corpo: { id: "doc-1", nome_arquivo: "aula.txt" } }),
    "POST /provas": () => ({
      status: 202,
      corpo: { id: "prova-1", status: "pendente", total_questoes: 2, titulo: "aula" },
    }),
    "GET /provas/prova-1": () => PROVA_DETALHE,
  });
}

async function escolherArquivoEGerar() {
  const entrada = await screen.findByTestId("entrada-arquivo");
  fireEvent.change(entrada, { target: { files: [new File(["REST e HTTP"], "aula.txt", { type: "text/plain" })] } });
  fireEvent.click(screen.getByRole("button", { name: /Gerar prova/ }));
}

describe("Criar prova", () => {
  beforeEach(() => {
    FonteDeEventosFalsa.ultima = null;
    vi.stubGlobal("EventSource", FonteDeEventosFalsa);
  });

  it("envia o material, acompanha a geração pelo SSE e abre a prova pronta", async () => {
    const { chamadas } = prepararServidor();
    const { router } = renderizarApp("/");

    await escolherArquivoEGerar();

    const modal = await screen.findByRole("dialog");
    expect(within(modal).getByText("Gerando sua prova")).toBeInTheDocument();
    await waitFor(() => expect(FonteDeEventosFalsa.ultima?.url).toBe("/api/v1/provas/prova-1/eventos"));

    const criacao = chamadas.find((chamada) => chamada.metodo === "POST" && chamada.url.pathname.endsWith("/provas"));
    expect(criacao?.corpo).toEqual({
      documento_id: "doc-1",
      configuracao: { dificuldade: "medio", multipla_escolha: 5, verdadeiro_falso: 5, dissertativas: 0 },
    });

    act(() => FonteDeEventosFalsa.ultima!.emitir("progresso", progresso({ concluidas: 1 })));
    expect(await within(modal).findByText(/1 de 2 questões prontas/)).toBeInTheDocument();

    act(() => FonteDeEventosFalsa.ultima!.emitir("fim", progresso({ status: "concluida", concluidas: 2 })));
    expect(await within(modal).findByText("Sua prova está pronta")).toBeInTheDocument();
    expect(FonteDeEventosFalsa.ultima!.fechada).toBe(true);

    fireEvent.click(within(modal).getByRole("button", { name: "Ver prova" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/provas/prova-1"));
    expect(await screen.findByText("Qual método HTTP cria um recurso?")).toBeInTheDocument();
  });

  it("mostra o erro da geração e permite tentar de novo", async () => {
    prepararServidor();
    renderizarApp("/");

    await escolherArquivoEGerar();
    await waitFor(() => expect(FonteDeEventosFalsa.ultima).not.toBeNull());
    act(() =>
      FonteDeEventosFalsa.ultima!.emitir("fim", progresso({ status: "falhou", erro: "Limite de uso da IA atingido." })),
    );

    const modal = screen.getByRole("dialog");
    expect(await within(modal).findByText("Não foi possível gerar a prova")).toBeInTheDocument();
    expect(within(modal).getByText("Limite de uso da IA atingido.")).toBeInTheDocument();
    expect(within(modal).getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });

  it("explica o erro quando o arquivo é recusado pelo backend", async () => {
    servidorFalso({
      "POST /documentos": () => ({
        status: 422,
        corpo: { erro: { codigo: "documento_sem_texto", mensagem: "Não foi possível extrair texto do arquivo." } },
      }),
    });
    renderizarApp("/");

    await escolherArquivoEGerar();

    expect(await screen.findByText("Não foi possível extrair texto do arquivo.")).toBeInTheDocument();
  });

  it("pede o arquivo e ao menos um tipo antes de gerar", async () => {
    servidorFalso({});
    renderizarApp("/");

    fireEvent.click(await screen.findByRole("button", { name: /Gerar prova/ }));
    expect(screen.getByRole("alert")).toHaveTextContent("Adicione seu conteúdo");

    fireEvent.change(screen.getByTestId("entrada-arquivo"), {
      target: { files: [new File(["x"], "slides.pptx")] },
    });
    expect(screen.getByRole("alert")).toHaveTextContent("PDF, DOCX ou TXT");
  });

  it("usa as preferências salvas nas configurações", async () => {
    localStorage.setItem(
      "provai-preferencias",
      JSON.stringify({ dificuldade: "dificil", quantidade: 4, tipos: ["dissertativa"] }),
    );
    const { chamadas } = prepararServidor();
    renderizarApp("/");

    expect(await screen.findByRole("button", { name: /Difícil/ })).toHaveAttribute("aria-pressed", "true");
    await escolherArquivoEGerar();

    await waitFor(() =>
      expect(chamadas.find((chamada) => chamada.url.pathname.endsWith("/provas"))?.corpo).toMatchObject({
        configuracao: { dificuldade: "dificil", dissertativas: 4, multipla_escolha: 0, verdadeiro_falso: 0 },
      }),
    );
  });
});
