import type { ConfiguracaoProva, Dificuldade, TipoQuestao } from "@/api/tipos";

export const DIFICULDADES: { valor: Dificuldade; rotulo: string; classe: string }[] = [
  { valor: "facil", rotulo: "Fácil", classe: "facil" },
  { valor: "medio", rotulo: "Média", classe: "media" },
  { valor: "dificil", rotulo: "Difícil", classe: "dificil" },
];

export const TIPOS: { valor: TipoQuestao; rotulo: string }[] = [
  { valor: "multipla_escolha", rotulo: "Múltipla escolha" },
  { valor: "verdadeiro_falso", rotulo: "Verdadeiro ou falso" },
  { valor: "dissertativa", rotulo: "Dissertativa" },
];

// Os mesmos limites por tipo que o backend valida (ConfiguracaoProva).
export const LIMITE_POR_TIPO: Record<TipoQuestao, number> = {
  multipla_escolha: 20,
  dissertativa: 10,
  verdadeiro_falso: 10,
};

// Teto da interface: no plano gratuito da Groq, provas maiores passam de alguns minutos.
export const LIMITE_TOTAL = 20;

export function dificuldadeDe(valor: Dificuldade) {
  return DIFICULDADES.find((item) => item.valor === valor) ?? DIFICULDADES[1]!;
}

export function rotuloDoTipo(tipo: TipoQuestao): string {
  return TIPOS.find((item) => item.valor === tipo)?.rotulo ?? tipo;
}

/** Quantas questões cabem com os tipos escolhidos. */
export function limiteDeQuestoes(tipos: TipoQuestao[]): number {
  const soma = tipos.reduce((total, tipo) => total + LIMITE_POR_TIPO[tipo], 0);
  return Math.min(soma, LIMITE_TOTAL);
}

/** Reparte o total entre os tipos escolhidos, um de cada vez, na ordem da tela,
 * pulando os tipos que já chegaram ao limite. 10 questões em 3 tipos viram 4, 3 e 3. */
export function distribuirQuestoes(
  total: number,
  tipos: TipoQuestao[],
  dificuldade: Dificuldade,
): ConfiguracaoProva {
  const ordenados = TIPOS.map((item) => item.valor).filter((tipo) => tipos.includes(tipo));
  const contagem: Record<TipoQuestao, number> = { multipla_escolha: 0, dissertativa: 0, verdadeiro_falso: 0 };
  const alvo = Math.min(total, limiteDeQuestoes(ordenados));

  let distribuidas = 0;
  for (let indice = 0; distribuidas < alvo; indice++) {
    const tipo = ordenados[indice % ordenados.length]!;
    if (contagem[tipo] < LIMITE_POR_TIPO[tipo]) {
      contagem[tipo]++;
      distribuidas++;
    }
  }

  return {
    dificuldade,
    multipla_escolha: contagem.multipla_escolha,
    dissertativas: contagem.dissertativa,
    verdadeiro_falso: contagem.verdadeiro_falso,
  };
}
