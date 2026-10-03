import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { BarChart3, CircleEllipsis, FileUp, ListFilter, Minus, Plus, Sparkles } from "lucide-react";
import { useEffect, useRef, useState, type ChangeEvent, type DragEvent } from "react";

import type { Dificuldade, TipoQuestao } from "@/api/tipos";
import { ModalProgresso } from "@/components/modal-progresso";
import { Button } from "@/components/ui-button";
import { useGeracaoProva } from "@/hooks/use-geracao-prova";
import { DIFICULDADES, distribuirQuestoes, limiteDeQuestoes, TIPOS } from "@/lib/configuracao-prova";
import { lerPreferencias } from "@/lib/preferencias";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Criar prova com IA | PROVAI" },
      { name: "description", content: "Crie uma prova personalizada com IA a partir do seu material no PROVAI." },
    ],
  }),
  component: PaginaCriarProva,
});

const EXTENSOES_ACEITAS = /\.(pdf|docx|txt)$/i;

function PaginaCriarProva() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [preferencias] = useState(lerPreferencias);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [arrastando, setArrastando] = useState(false);
  const [dificuldade, setDificuldade] = useState<Dificuldade>(preferencias.dificuldade);
  const [quantidade, setQuantidade] = useState(preferencias.quantidade);
  const [tipos, setTipos] = useState<TipoQuestao[]>(preferencias.tipos);
  const [erro, setErro] = useState("");
  const [modalAberto, setModalAberto] = useState(false);
  const { fase, provaId, iniciar, parar } = useGeracaoProva();

  const limite = Math.max(1, limiteDeQuestoes(tipos));
  useEffect(() => {
    setQuantidade((atual) => Math.min(atual, limite));
  }, [limite]);

  const escolherArquivo = (escolhido?: File) => {
    if (!escolhido) return;
    if (!EXTENSOES_ACEITAS.test(escolhido.name)) {
      setErro("Selecione um arquivo PDF, DOCX ou TXT.");
      return;
    }
    setArquivo(escolhido);
    setErro("");
  };
  const aoSelecionar = (evento: ChangeEvent<HTMLInputElement>) => escolherArquivo(evento.target.files?.[0]);
  const aoSoltar = (evento: DragEvent<HTMLDivElement>) => {
    evento.preventDefault();
    setArrastando(false);
    escolherArquivo(evento.dataTransfer.files[0]);
  };
  const alternarTipo = (tipo: TipoQuestao) =>
    setTipos((antigos) => (antigos.includes(tipo) ? antigos.filter((item) => item !== tipo) : [...antigos, tipo]));

  const gerar = () => {
    if (!arquivo) {
      setErro("Adicione seu conteúdo para gerar a prova.");
      inputRef.current?.focus();
      return;
    }
    if (!tipos.length) {
      setErro("Selecione ao menos um tipo de questão.");
      return;
    }
    setErro("");
    setModalAberto(true);
    void iniciar(arquivo, distribuirQuestoes(quantidade, tipos, dificuldade));
  };

  const fecharModal = () => {
    // A geração continua no servidor; o modal só deixa de acompanhar.
    parar();
    setModalAberto(false);
  };

  return (
    <>
      <div className="create-layout">
        <section className="create-left">
          <span className="sparkle-mark" aria-hidden="true">
            ✧
          </span>
          <h1>
            Crie sua prova
            <br />
            com IA
          </h1>
          <p className="section-description">
            Transforme seu conteúdo em uma avaliação personalizada, rápida e inteligente.
          </p>
          <div
            className={`upload-zone ${arrastando ? "is-dragging" : ""}`}
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(evento) => {
              if (evento.key === "Enter" || evento.key === " ") {
                evento.preventDefault();
                inputRef.current?.click();
              }
            }}
            onDragOver={(evento) => {
              evento.preventDefault();
              setArrastando(true);
            }}
            onDragLeave={() => setArrastando(false)}
            onDrop={aoSoltar}
            aria-label="Selecionar arquivo de conteúdo"
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={aoSelecionar}
              tabIndex={-1}
              data-testid="entrada-arquivo"
            />
            <FileUp size={52} strokeWidth={1.2} />
            <strong>{arquivo ? arquivo.name : "Arraste seu conteúdo aqui"}</strong>
            <span>{arquivo ? "Clique para trocar o arquivo" : "ou clique para selecionar"}</span>
            <small>PDF, DOCX, TXT</small>
          </div>
          <div className="create-footnote">
            <Sparkles size={14} /> Da sua ideia <span>⟶</span> Para uma prova completa
          </div>
        </section>
        <section className="create-right" aria-label="Configurações da prova">
          <div className="steps">
            <div>
              <div className="step-number">01</div>
              <div className="step-caption">Conteúdo</div>
              <div className="step-detail">Faça o upload do material da sua prova.</div>
            </div>
            <span className="step-dash">—</span>
            <div>
              <div className="step-number">02</div>
              <div className="step-caption">Configurações</div>
              <div className="step-detail">Personalize como você quer sua prova.</div>
            </div>
          </div>
          <div className="form-block">
            <div className="form-heading">
              <BarChart3 size={20} />
              <div>
                <strong>Dificuldade</strong>
                <span>Escolha o nível de complexidade das questões.</span>
              </div>
            </div>
            <div className="difficulty-options">
              {DIFICULDADES.map((item) => (
                <Button
                  key={item.valor}
                  className={`choice-button ${dificuldade === item.valor ? "selected" : ""}`}
                  onClick={() => setDificuldade(item.valor)}
                  aria-pressed={dificuldade === item.valor}
                >
                  <span className="choice-dot" />
                  {item.rotulo}
                  {dificuldade === item.valor && <span className="choice-arrow">‹</span>}
                </Button>
              ))}
            </div>
          </div>
          <div className="form-block">
            <div className="form-heading">
              <CircleEllipsis size={20} />
              <div>
                <strong>Quantidade</strong>
                <span>Defina o número de questões (até {limite} com os tipos escolhidos).</span>
              </div>
            </div>
            <div className="quantity-control">
              <Button
                variant="ghost"
                onClick={() => setQuantidade((atual) => Math.max(1, atual - 1))}
                aria-label="Diminuir quantidade"
              >
                <Minus size={18} />
              </Button>
              <span aria-live="polite">{quantidade}</span>
              <Button
                variant="ghost"
                onClick={() => setQuantidade((atual) => Math.min(limite, atual + 1))}
                disabled={quantidade >= limite}
                aria-label="Aumentar quantidade"
              >
                <Plus size={18} />
              </Button>
            </div>
          </div>
          <div className="form-block">
            <div className="form-heading">
              <ListFilter size={20} />
              <div>
                <strong>Tipos de questão</strong>
                <span>Selecione os tipos que deseja incluir.</span>
              </div>
            </div>
            <div className="type-options">
              {TIPOS.map((tipo) => (
                <label className="check-option" key={tipo.valor}>
                  <input
                    type="checkbox"
                    checked={tipos.includes(tipo.valor)}
                    onChange={() => alternarTipo(tipo.valor)}
                  />
                  {tipo.rotulo}
                </label>
              ))}
            </div>
          </div>
          {erro && (
            <p className="form-error" role="alert">
              {erro}
            </p>
          )}
          <Button variant="primary" className="generate-button" onClick={gerar}>
            <Sparkles size={17} />
            Gerar prova
          </Button>
        </section>
      </div>
      {modalAberto && fase && (
        <ModalProgresso
          fase={fase}
          aoFechar={fecharModal}
          aoVerProva={() => {
            setModalAberto(false);
            if (provaId) void navigate({ to: "/provas/$provaId", params: { provaId } });
          }}
          aoTentarNovamente={gerar}
        />
      )}
    </>
  );
}
