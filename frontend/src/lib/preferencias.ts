import type { Dificuldade, TipoQuestao } from "@/api/tipos";

import { LIMITE_TOTAL } from "./configuracao-prova";

export interface Preferencias {
  dificuldade: Dificuldade;
  quantidade: number;
  tipos: TipoQuestao[];
}

const CHAVE = "provai-preferencias";

export const PREFERENCIAS_PADRAO: Preferencias = {
  dificuldade: "medio",
  quantidade: 10,
  tipos: ["multipla_escolha", "verdadeiro_falso"],
};

// Ficam no navegador: sem login, não há a quem associá-las no servidor. Qualquer
// falha de leitura (modo privado, valor corrompido) volta ao padrão.
export function lerPreferencias(): Preferencias {
  try {
    const salvo = JSON.parse(localStorage.getItem(CHAVE) ?? "null") as Partial<Preferencias> | null;
    if (!salvo) return PREFERENCIAS_PADRAO;
    const quantidade = Number(salvo.quantidade);
    return {
      dificuldade: ["facil", "medio", "dificil"].includes(salvo.dificuldade as string)
        ? (salvo.dificuldade as Dificuldade)
        : PREFERENCIAS_PADRAO.dificuldade,
      quantidade:
        Number.isInteger(quantidade) && quantidade >= 1 && quantidade <= LIMITE_TOTAL
          ? quantidade
          : PREFERENCIAS_PADRAO.quantidade,
      tipos: Array.isArray(salvo.tipos) && salvo.tipos.length ? salvo.tipos : PREFERENCIAS_PADRAO.tipos,
    };
  } catch {
    return PREFERENCIAS_PADRAO;
  }
}

export function salvarPreferencias(preferencias: Preferencias): boolean {
  try {
    localStorage.setItem(CHAVE, JSON.stringify(preferencias));
    return true;
  } catch {
    return false;
  }
}
