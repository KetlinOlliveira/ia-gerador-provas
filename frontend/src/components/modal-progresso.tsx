import { Check, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { avancar, ESTAGIOS, estagioAtivo, faixaDePorcentagem, type FaseGeracao } from "@/lib/progresso";

import { Button } from "./ui-button";

interface Props {
  fase: FaseGeracao;
  aoFechar: () => void;
  aoVerProva: () => void;
  aoTentarNovamente: () => void;
}

/** O mesmo modal do protótipo, agora movido pelo progresso real da geração. */
export function ModalProgresso({ fase, aoFechar, aoVerProva, aoTentarNovamente }: Props) {
  const [progresso, setProgresso] = useState(0);
  const faseRef = useRef(fase);
  faseRef.current = fase;

  // Mesmo ritmo do protótipo (um passo a cada 180 ms), mas com destino real.
  useEffect(() => {
    const intervalo = window.setInterval(() => {
      const { alvo, teto } = faixaDePorcentagem(faseRef.current);
      setProgresso((atual) => avancar(atual, alvo, teto));
    }, 180);
    return () => window.clearInterval(intervalo);
  }, []);

  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") aoFechar();
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [aoFechar]);

  const concluida = fase.tipo === "concluida";
  const falhou = fase.tipo === "falhou";
  const exibido = Math.round(progresso);
  const ativo = estagioAtivo(fase);

  const titulo = concluida ? "Sua prova está pronta" : falhou ? "Não foi possível gerar a prova" : "Gerando sua prova";
  const descricao = concluida
    ? "Sua avaliação foi preparada com base nas preferências selecionadas."
    : falhou
      ? fase.mensagem
      : "A IA está analisando o conteúdo e construindo as questões.";

  const detalheDoEstagio = (indice: number, padrao: string) => {
    if (fase.tipo !== "gerando" || indice !== 2 || fase.progresso.etapa !== "geracao") return padrao;
    const { concluidas, total } = fase.progresso;
    return `${concluidas} de ${total} ${total === 1 ? "questão pronta" : "questões prontas"}, cada uma com base nos trechos do seu material.`;
  };

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(evento) => {
        if (evento.target === evento.currentTarget) aoFechar();
      }}
    >
      <section className="progress-modal" role="dialog" aria-modal="true" aria-labelledby="progress-title">
        <Button variant="ghost" className="modal-close" onClick={aoFechar} aria-label="Fechar">
          <X size={18} />
        </Button>
        <span className="sparkle-mark">✧</span>
        <h2 id="progress-title">{titulo}</h2>
        <p className={falhou ? "progress-error" : undefined}>{descricao}</p>
        <div className="progress-body">
          <div
            className="progress-visual"
            aria-label={`Progresso: ${exibido}%`}
            role="progressbar"
            aria-valuenow={exibido}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <svg viewBox="0 0 300 300" aria-hidden="true">
              <defs>
                <linearGradient id="progressGradient">
                  <stop stopColor="var(--coral)" />
                  <stop offset=".5" stopColor="var(--pink)" />
                  <stop offset="1" stopColor="var(--violet)" />
                </linearGradient>
              </defs>
              <circle className="progress-track" cx="150" cy="150" r="116" strokeDasharray="600 730" />
              <circle
                className="progress-arc"
                cx="150"
                cy="150"
                r="116"
                style={{ strokeDasharray: `${Math.max(5, progresso * 5.1)} 730` }}
              />
              <circle className="progress-arc-inner" cx="150" cy="150" r="93" />
              <circle className="progress-arc-third" cx="150" cy="150" r="70" />
            </svg>
            <span className="progress-percent">{exibido}%</span>
          </div>
          <div className="progress-stages">
            {ESTAGIOS.map(([nome, detalhe], indice) => (
              <div
                key={nome}
                className={`progress-stage ${indice < ativo ? "is-done" : ""} ${indice === ativo ? "is-current" : ""}`}
              >
                <span className="stage-marker">{indice < ativo && <Check size={15} />}</span>
                <div className="stage-text">
                  <strong>{nome}</strong>
                  <span>{detalheDoEstagio(indice, detalhe)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="progress-line">
          <span style={{ width: `${progresso}%` }} />
        </div>
        <div className="modal-footer">
          <Sparkles size={16} />
          <span>
            {concluida
              ? "Concluído."
              : falhou
                ? "Nada foi perdido: seu material continua salvo."
                : "Isso pode levar alguns segundos. Você pode fechar esta janela: a prova continua sendo gerada."}
          </span>
          {concluida && (
            <Button variant="primary" className="modal-action" onClick={aoVerProva}>
              Ver prova
            </Button>
          )}
          {falhou && (
            <Button variant="primary" className="modal-action" onClick={aoTentarNovamente}>
              Tentar novamente
            </Button>
          )}
        </div>
      </section>
    </div>
  );
}
