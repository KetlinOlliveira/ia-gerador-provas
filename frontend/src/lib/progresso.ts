import type { ProgressoProva } from "@/api/tipos";

/** Em que ponto está a geração vista pelo modal. */
export type FaseGeracao =
  | { tipo: "enviando" }
  | { tipo: "gerando"; progresso: ProgressoProva }
  | { tipo: "concluida" }
  | { tipo: "falhou"; mensagem: string };

export const ESTAGIOS = [
  ["Conteúdo analisado", "Material enviado, dividido em trechos e vetorizado."],
  ["Conceitos identificados", "O agente planejador mapeia os principais tópicos."],
  ["Questões sendo geradas", "Cada questão nasce dos trechos do seu material."],
  ["Revisão de dificuldade", "O agente revisor confere nível, clareza e fundamentação."],
] as const;

/** Índice do estágio em andamento (0 a 3); 4 quando tudo terminou. */
export function estagioAtivo(fase: FaseGeracao): number {
  switch (fase.tipo) {
    case "enviando":
      return 0;
    case "concluida":
      return 4;
    case "falhou":
      return -1;
    case "gerando": {
      const { etapa, concluidas, total } = fase.progresso;
      if (etapa !== "geracao") return 1;
      return concluidas >= total ? 3 : 2;
    }
  }
}

/** Faixa de porcentagem de cada momento: `alvo` é o que já foi de fato concluído e
 * `teto` é até onde o número pode avançar devagar enquanto a etapa roda, para a tela
 * não parecer travada durante uma chamada longa ao modelo. */
export function faixaDePorcentagem(fase: FaseGeracao): { alvo: number; teto: number } {
  switch (fase.tipo) {
    case "enviando":
      return { alvo: 6, teto: 14 };
    case "concluida":
      return { alvo: 100, teto: 100 };
    case "falhou":
      return { alvo: 0, teto: 0 };
    case "gerando": {
      const { etapa, concluidas, total } = fase.progresso;
      if (etapa !== "geracao") return { alvo: 16, teto: 26 };
      if (concluidas >= total) return { alvo: 96, teto: 99 };
      const porQuestao = 68 / Math.max(total, 1);
      const alvo = 28 + porQuestao * concluidas;
      return { alvo, teto: alvo + porQuestao * 0.85 };
    }
  }
}

/** Próximo valor exibido: corre até o alvo e depois anda devagar até o teto. */
export function avancar(atual: number, alvo: number, teto: number): number {
  if (alvo >= 100) return Math.min(100, atual + 4);
  if (atual < alvo) return Math.min(alvo, atual + 2);
  if (atual < teto) return Math.min(teto, atual + 0.25);
  return atual;
}
