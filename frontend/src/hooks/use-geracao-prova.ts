import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { api, ErroApi } from "@/api/cliente";
import type { ConfiguracaoProva, ProgressoProva } from "@/api/tipos";
import type { FaseGeracao } from "@/lib/progresso";

/** Envia o material, cria a prova e acompanha a geração pelo fluxo de eventos (SSE). */
export function useGeracaoProva() {
  const queryClient = useQueryClient();
  const [fase, setFase] = useState<FaseGeracao | null>(null);
  const [provaId, setProvaId] = useState<string | null>(null);
  const fonteRef = useRef<EventSource | null>(null);
  // Cada início ganha um número; respostas de um início anterior são ignoradas.
  const execucaoRef = useRef(0);

  const parar = useCallback(() => {
    execucaoRef.current++;
    fonteRef.current?.close();
    fonteRef.current = null;
  }, []);

  useEffect(() => parar, [parar]);

  const iniciar = useCallback(
    async (arquivo: File, configuracao: ConfiguracaoProva) => {
      parar();
      const execucao = execucaoRef.current;
      const atual = () => execucao === execucaoRef.current;
      setProvaId(null);
      setFase({ tipo: "enviando" });

      try {
        const documento = await api.enviarDocumento(arquivo);
        if (!atual()) return;
        const prova = await api.criarProva({ documento_id: documento.id, configuracao });
        if (!atual()) return;
        setProvaId(prova.id);
        void queryClient.invalidateQueries({ queryKey: ["provas"] });
        setFase({
          tipo: "gerando",
          progresso: {
            status: prova.status,
            etapa: null,
            mensagem: null,
            concluidas: 0,
            total: prova.total_questoes,
            erro: null,
          },
        });

        const fonte = new EventSource(api.urlEventos(prova.id));
        fonteRef.current = fonte;
        const aplicar = (evento: MessageEvent<string>) => {
          if (!atual()) return;
          const progresso = JSON.parse(evento.data) as ProgressoProva | { status: "excluida" };
          if (progresso.status === "excluida") {
            setFase({ tipo: "falhou", mensagem: "A prova foi excluída durante a geração." });
          } else if (progresso.status === "concluida") {
            setFase({ tipo: "concluida" });
          } else if (progresso.status === "falhou") {
            setFase({ tipo: "falhou", mensagem: progresso.erro ?? "A geração falhou." });
          } else {
            setFase({ tipo: "gerando", progresso });
          }
        };
        fonte.addEventListener("progresso", aplicar);
        fonte.addEventListener("fim", (evento) => {
          aplicar(evento);
          fonte.close();
          void queryClient.invalidateQueries({ queryKey: ["provas"] });
        });
        // Em quedas de conexão o EventSource reconecta sozinho; não há o que fazer aqui.
      } catch (erro) {
        if (!atual()) return;
        setFase({
          tipo: "falhou",
          mensagem: erro instanceof ErroApi ? erro.message : "Erro inesperado ao gerar a prova.",
        });
      }
    },
    [parar, queryClient],
  );

  return { fase, provaId, iniciar, parar };
}
