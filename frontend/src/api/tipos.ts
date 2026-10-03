// Espelham os esquemas Pydantic do backend (app/esquemas). A documentação interativa
// em /docs do backend é a referência quando algum campo mudar.

export type Dificuldade = "facil" | "medio" | "dificil";
export type TipoQuestao = "multipla_escolha" | "dissertativa" | "verdadeiro_falso";
export type StatusProva = "pendente" | "gerando" | "concluida" | "falhou";

export interface Documento {
  id: string;
  nome_arquivo: string;
  tipo: string;
  total_trechos: number;
  total_paginas: number | null;
  criado_em: string;
}

export interface ConfiguracaoProva {
  dificuldade: Dificuldade;
  multipla_escolha: number;
  dissertativas: number;
  verdadeiro_falso: number;
}

export interface CriarProvaRequisicao {
  documento_id: string;
  titulo?: string;
  configuracao: ConfiguracaoProva;
}

export interface ProgressoProva {
  status: StatusProva;
  etapa: "planejamento" | "geracao" | null;
  mensagem: string | null;
  concluidas: number;
  total: number;
  erro: string | null;
}

export interface ProvaResumo {
  id: string;
  titulo: string;
  documento_id: string | null;
  status: StatusProva;
  dificuldade: Dificuldade;
  total_questoes: number;
  criado_em: string;
  concluido_em: string | null;
}

export interface Topico {
  titulo: string;
  descricao: string;
}

export interface Fonte {
  ordem: number;
  pagina: number | null;
  texto: string;
}

export interface Avaliacao {
  nota: number;
  fundamentada: boolean;
  adequada_a_dificuldade: boolean;
  problemas: string[];
  sugestoes: string;
}

export interface QuestaoMultiplaEscolha {
  tipo: "multipla_escolha";
  enunciado: string;
  alternativas: string[];
  resposta_correta: "A" | "B" | "C" | "D";
  justificativa: string;
}

export interface QuestaoDissertativa {
  tipo: "dissertativa";
  enunciado: string;
  resposta_esperada: string;
  criterios: { descricao: string; pontos: number }[];
}

export interface QuestaoVerdadeiroFalso {
  tipo: "verdadeiro_falso";
  enunciado: string;
  afirmativas: { texto: string; verdadeira: boolean; justificativa: string }[];
}

export type ConteudoQuestao = QuestaoMultiplaEscolha | QuestaoDissertativa | QuestaoVerdadeiroFalso;

export interface QuestaoGerada {
  numero: number;
  topico: string;
  dificuldade: Dificuldade;
  conteudo: ConteudoQuestao;
  fontes: Fonte[];
  avaliacao: Avaliacao;
  aprovada: boolean;
  tentativas: number;
}

export interface ProvaDetalhe extends ProvaResumo {
  configuracao: ConfiguracaoProva;
  progresso: ProgressoProva;
  duracao_segundos: number | null;
  topicos: Topico[];
  questoes: QuestaoGerada[];
}

export interface PaginaProvas {
  itens: ProvaResumo[];
  total: number;
  pagina: number;
  por_pagina: number;
}

export interface EstatisticasProvas {
  total: number;
  este_mes: number;
}

export interface FiltrosProvas {
  busca?: string;
  dificuldade?: Dificuldade;
  ordem?: "recentes" | "antigas";
  pagina?: number;
  por_pagina?: number;
}

export interface Saude {
  status: string;
  versao: string;
  llm_configurado: boolean;
}

export interface InformacoesSistema {
  modelos: { planejador: string; gerador: string; revisor: string };
  modelo_embeddings: string;
  tamanho_trecho: number;
  trechos_por_topico: number;
  nota_minima_revisao: number;
  max_tentativas_por_questao: number;
  tamanho_max_upload_mb: number;
}

export type FormatoExportacao = "pdf" | "docx" | "md";
export type VersaoExportacao = "aluno" | "professor";
