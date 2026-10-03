import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, createRouter, RouterProvider } from "@tanstack/react-router";
import { render } from "@testing-library/react";
import { vi } from "vitest";

import { routeTree } from "@/routeTree.gen";

/** Monta a aplicação inteira (rotas, React Query) começando em `caminho`. */
export function renderizarApp(caminho: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: [caminho] }),
  });
  const resultado = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...resultado, router };
}

type Rota = (requisicao: { url: URL; metodo: string; corpo: unknown }) => unknown;

/** Substitui o fetch por respostas roteirizadas: `"GET /provas": () => ({...})`.
 * Rotas sem resposta devolvem 404; o retorno `{status, corpo}` define status e corpo. */
export function servidorFalso(rotas: Record<string, Rota>) {
  const chamadas: { metodo: string; url: URL; corpo: unknown }[] = [];
  const fetchFalso = vi.fn(async (entrada: RequestInfo | URL, opcoes?: RequestInit) => {
    const url = new URL(String(entrada), "http://localhost");
    const metodo = (opcoes?.method ?? "GET").toUpperCase();
    const corpo = typeof opcoes?.body === "string" ? JSON.parse(opcoes.body) : opcoes?.body;
    chamadas.push({ metodo, url, corpo });
    const chave = `${metodo} ${url.pathname.replace("/api/v1", "")}`;
    const rota = rotas[chave];
    if (!rota) return new Response(JSON.stringify({ erro: { mensagem: `Sem rota: ${chave}` } }), { status: 404 });
    const resultado = rota({ url, metodo, corpo }) as { status?: unknown; corpo?: unknown } | undefined;
    // `{status: <número>, corpo?}` define a resposta; qualquer outro objeto é o próprio corpo
    // (a prova, por exemplo, tem um campo `status` em texto).
    const envelope = !!resultado && typeof resultado.status === "number";
    const status = envelope ? (resultado.status as number) : 200;
    const dados = envelope ? resultado.corpo : resultado;
    if (status === 204) return new Response(null, { status });
    return new Response(JSON.stringify(dados), { status, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchFalso);
  return { chamadas };
}

/** EventSource que o teste controla: `FonteDeEventosFalsa.ultima.emitir("progresso", {...})`. */
export class FonteDeEventosFalsa {
  static ultima: FonteDeEventosFalsa | null = null;
  readonly ouvintes = new Map<string, ((evento: MessageEvent<string>) => void)[]>();
  fechada = false;

  constructor(readonly url: string) {
    FonteDeEventosFalsa.ultima = this;
  }

  addEventListener(nome: string, ouvinte: (evento: MessageEvent<string>) => void) {
    this.ouvintes.set(nome, [...(this.ouvintes.get(nome) ?? []), ouvinte]);
  }

  close() {
    this.fechada = true;
  }

  emitir(nome: string, dados: unknown) {
    const evento = new MessageEvent(nome, { data: JSON.stringify(dados) });
    for (const ouvinte of this.ouvintes.get(nome) ?? []) ouvinte(evento);
  }
}

export const PROVA_RESUMO = {
  id: "prova-1",
  titulo: "Aula de redes",
  documento_id: "doc-1",
  status: "concluida" as const,
  dificuldade: "medio" as const,
  total_questoes: 2,
  criado_em: "2026-10-02T12:00:00Z",
  concluido_em: "2026-10-02T12:01:00Z",
};

export const PROVA_DETALHE = {
  ...PROVA_RESUMO,
  configuracao: { dificuldade: "medio", multipla_escolha: 1, dissertativas: 0, verdadeiro_falso: 1 },
  progresso: { status: "concluida", etapa: "geracao", mensagem: "Prova pronta", concluidas: 2, total: 2, erro: null },
  duracao_segundos: 21.4,
  topicos: [{ titulo: "Métodos HTTP", descricao: "GET, POST, PUT e DELETE." }],
  questoes: [
    {
      numero: 1,
      topico: "Métodos HTTP",
      dificuldade: "medio",
      conteudo: {
        tipo: "multipla_escolha",
        enunciado: "Qual método HTTP cria um recurso?",
        alternativas: ["GET", "POST", "DELETE", "HEAD"],
        resposta_correta: "B",
        justificativa: "POST cria recursos; os demais leem ou removem.",
      },
      fontes: [{ ordem: 0, pagina: 2, texto: "POST (criar), PUT/PATCH (atualizar)." }],
      avaliacao: { nota: 9, fundamentada: true, adequada_a_dificuldade: true, problemas: [], sugestoes: "" },
      aprovada: true,
      tentativas: 1,
    },
    {
      numero: 2,
      topico: "Métodos HTTP",
      dificuldade: "medio",
      conteudo: {
        tipo: "verdadeiro_falso",
        enunciado: "Julgue as afirmativas.",
        afirmativas: [
          { texto: "GET lê um recurso.", verdadeira: true, justificativa: "Conforme o material." },
          { texto: "DELETE cria um recurso.", verdadeira: false, justificativa: "DELETE remove." },
        ],
      },
      fontes: [{ ordem: 0, pagina: 2, texto: "GET (ler) e DELETE (remover)." }],
      avaliacao: {
        nota: 6,
        fundamentada: true,
        adequada_a_dificuldade: true,
        problemas: ["Afirmativa falsa óbvia demais."],
        sugestoes: "",
      },
      aprovada: false,
      tentativas: 2,
    },
  ],
};
