import type {
  CriarProvaRequisicao,
  Documento,
  EstatisticasProvas,
  FiltrosProvas,
  FormatoExportacao,
  InformacoesSistema,
  PaginaProvas,
  ProvaDetalhe,
  ProvaResumo,
  Saude,
  VersaoExportacao,
} from "./tipos";

const BASE = "/api/v1";

export class ErroApi extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly codigo?: string,
  ) {
    super(message);
    this.name = "ErroApi";
  }
}

/** Extrai uma mensagem legível dos dois formatos de erro do backend:
 * `{erro: {codigo, mensagem}}` (erros da aplicação) e `{detail: [...]}` (validação). */
export function mensagemDoCorpo(corpo: unknown, status: number): { mensagem: string; codigo?: string } {
  if (corpo && typeof corpo === "object") {
    const { erro, detail } = corpo as {
      erro?: { codigo?: string; mensagem?: string };
      detail?: unknown;
    };
    if (erro?.mensagem) return { mensagem: erro.mensagem, codigo: erro.codigo };
    if (Array.isArray(detail) && detail.length) {
      const primeiro = detail[0] as { msg?: string };
      if (primeiro.msg) return { mensagem: primeiro.msg.replace(/^Value error, /, "") };
    }
  }
  if (status >= 500) return { mensagem: "O servidor encontrou um erro. Tente novamente." };
  return { mensagem: `Falha na requisição (${status}).` };
}

async function requisitar<T>(caminho: string, opcoes?: RequestInit): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(`${BASE}${caminho}`, opcoes);
  } catch {
    throw new ErroApi("Não foi possível conectar ao servidor. Verifique se o backend está no ar.", 0);
  }
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => null);
    const { mensagem, codigo } = mensagemDoCorpo(corpo, resposta.status);
    throw new ErroApi(mensagem, resposta.status, codigo);
  }
  if (resposta.status === 204) return undefined as T;
  return (await resposta.json()) as T;
}

function json(metodo: string, corpo: unknown): RequestInit {
  return { method: metodo, headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) };
}

function consulta(filtros: FiltrosProvas): string {
  const parametros = new URLSearchParams();
  for (const [chave, valor] of Object.entries(filtros)) {
    if (valor !== undefined && valor !== "") parametros.set(chave, String(valor));
  }
  const texto = parametros.toString();
  return texto ? `?${texto}` : "";
}

export const api = {
  enviarDocumento(arquivo: File): Promise<Documento> {
    const formulario = new FormData();
    formulario.append("arquivo", arquivo);
    return requisitar("/documentos", { method: "POST", body: formulario });
  },
  criarProva(requisicao: CriarProvaRequisicao): Promise<ProvaResumo> {
    return requisitar("/provas", json("POST", requisicao));
  },
  listarProvas(filtros: FiltrosProvas): Promise<PaginaProvas> {
    return requisitar(`/provas${consulta(filtros)}`);
  },
  estatisticas(): Promise<EstatisticasProvas> {
    return requisitar("/provas/estatisticas");
  },
  obterProva(id: string): Promise<ProvaDetalhe> {
    return requisitar(`/provas/${id}`);
  },
  excluirProva(id: string): Promise<void> {
    return requisitar(`/provas/${id}`, { method: "DELETE" });
  },
  saude(): Promise<Saude> {
    return requisitar("/health");
  },
  sistema(): Promise<InformacoesSistema> {
    return requisitar("/sistema");
  },
  urlEventos(id: string): string {
    return `${BASE}/provas/${id}/eventos`;
  },
  urlExportacao(id: string, formato: FormatoExportacao, versao: VersaoExportacao): string {
    return `${BASE}/provas/${id}/exportar?formato=${formato}&versao=${versao}`;
  },
};

/** Gera a prova de novo com o mesmo material e a mesma configuração. */
export async function gerarNovamente(id: string): Promise<ProvaResumo> {
  const prova = await api.obterProva(id);
  if (!prova.documento_id) {
    throw new ErroApi("O material desta prova foi excluído, então ela não pode ser gerada de novo.", 409);
  }
  return api.criarProva({
    documento_id: prova.documento_id,
    titulo: prova.titulo,
    configuracao: prova.configuracao,
  });
}
