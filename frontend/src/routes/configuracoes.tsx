import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { BrainCircuit, CircleUserRound, Cpu, Save, Settings, Sparkles } from "lucide-react";
import { useState, type ReactNode } from "react";

import { api } from "@/api/cliente";
import type { Dificuldade, TipoQuestao } from "@/api/tipos";
import { Button } from "@/components/ui-button";
import { DIFICULDADES, LIMITE_TOTAL, TIPOS } from "@/lib/configuracao-prova";
import { lerPreferencias, salvarPreferencias } from "@/lib/preferencias";

export const Route = createFileRoute("/configuracoes")({
  head: () => ({
    meta: [
      { title: "Configurações | PROVAI" },
      { name: "description", content: "Personalize suas preferências e veja como a IA gera suas provas." },
    ],
  }),
  component: PaginaConfiguracoes,
});

type Aba = "geral" | "ia" | "conta";

const ABAS: { valor: Aba; rotulo: string; icone: ReactNode }[] = [
  { valor: "geral", rotulo: "Geral", icone: <Settings size={16} /> },
  { valor: "ia", rotulo: "IA e geração", icone: <Sparkles size={16} /> },
  { valor: "conta", rotulo: "Conta", icone: <CircleUserRound size={16} /> },
];

function PaginaConfiguracoes() {
  const [aba, setAba] = useState<Aba>("geral");
  return (
    <div className="content-layout">
      <aside className="content-aside">
        <div className="page-label">
          <span className="sparkle-mark">✧</span>Configurações
        </div>
        <h1 className="section-title">
          Personalize
          <br />
          sua <span className="gradient-text">experiência</span>
        </h1>
        <p className="section-description">
          Ajuste as preferências de geração e conheça como a inteligência artificial monta as suas provas.
        </p>
        <div className="settings-sidebar" role="tablist" aria-label="Seções das configurações">
          {ABAS.map((item) => (
            <Button
              key={item.valor}
              variant="tab"
              role="tab"
              aria-selected={aba === item.valor}
              className={aba === item.valor ? "is-active" : ""}
              onClick={() => setAba(item.valor)}
            >
              {item.icone}
              {item.rotulo}
            </Button>
          ))}
        </div>
      </aside>
      <section className="content-main">
        <div className="settings-grid">
          {aba === "geral" && <PainelPreferencias />}
          {aba === "ia" && <PainelPipeline />}
          {aba === "conta" && <PainelConta />}
          <div className="settings-side-panels">
            <PainelSobreIa />
            <PainelStatus />
          </div>
        </div>
      </section>
      <aside className="content-art">
        <div className="orbit-art">
          <BrainCircuit size={67} strokeWidth={1.4} />
          <span className="orbit-spark one">✦</span>
          <span className="orbit-spark two">✦</span>
        </div>
        <p>A tecnologia certa para potencializar o seu ensino.</p>
        <span className="art-underline" />
      </aside>
    </div>
  );
}

function PainelPreferencias() {
  const [inicial] = useState(lerPreferencias);
  const [dificuldade, setDificuldade] = useState<Dificuldade>(inicial.dificuldade);
  const [quantidade, setQuantidade] = useState(inicial.quantidade);
  const [tipos, setTipos] = useState<TipoQuestao[]>(inicial.tipos);
  const [situacao, setSituacao] = useState<"editando" | "salvo" | "erro">("editando");

  const alterar = <T,>(definir: (valor: T) => void) => (valor: T) => {
    definir(valor);
    setSituacao("editando");
  };
  const alternarTipo = (tipo: TipoQuestao) =>
    alterar(setTipos)(tipos.includes(tipo) ? tipos.filter((item) => item !== tipo) : [...tipos, tipo]);

  const salvar = () => {
    const ok = salvarPreferencias({
      dificuldade,
      quantidade: Math.min(LIMITE_TOTAL, Math.max(1, quantidade || 1)),
      tipos: tipos.length ? tipos : ["multipla_escolha"],
    });
    setSituacao(ok ? "salvo" : "erro");
  };

  return (
    <div className="settings-panel">
      <h2>Preferências de geração</h2>
      <p className="panel-intro">Valores que já vêm preenchidos ao criar uma nova prova.</p>
      <div className="fields-grid">
        <div className="field">
          <label htmlFor="dificuldade">Dificuldade padrão</label>
          <select
            id="dificuldade"
            value={dificuldade}
            onChange={(evento) => alterar(setDificuldade)(evento.target.value as Dificuldade)}
          >
            {DIFICULDADES.map((item) => (
              <option key={item.valor} value={item.valor}>
                {item.rotulo}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="quantidade">Quantidade padrão</label>
          <input
            id="quantidade"
            type="number"
            min={1}
            max={LIMITE_TOTAL}
            value={quantidade}
            onChange={(evento) => alterar(setQuantidade)(Number(evento.target.value))}
          />
        </div>
      </div>
      <div className="storage-block">
        <strong>Tipos de questão padrão</strong>
        <p>Os tipos marcados aparecem selecionados na criação da prova.</p>
        <div className="type-options">
          {TIPOS.map((tipo) => (
            <label className="check-option" key={tipo.valor}>
              <input type="checkbox" checked={tipos.includes(tipo.valor)} onChange={() => alternarTipo(tipo.valor)} />
              {tipo.rotulo}
            </label>
          ))}
        </div>
      </div>
      <div className="settings-save">
        {situacao === "erro" && <span className="form-error">O navegador bloqueou o salvamento.</span>}
        <Button variant="primary" onClick={salvar}>
          <Save size={15} />
          {situacao === "salvo" ? "Alterações salvas" : "Salvar alterações"}
        </Button>
      </div>
    </div>
  );
}

function PainelPipeline() {
  const sistema = useQuery({ queryKey: ["sistema"], queryFn: api.sistema });
  const dados = sistema.data;
  return (
    <div className="settings-panel">
      <h2>Como a prova é gerada</h2>
      <p className="panel-intro">O pipeline de agentes que transforma o seu material em questões.</p>
      <ol className="pipeline-steps">
        <li>
          <strong>Indexação (RAG)</strong>
          <span>
            O material é dividido em trechos de até {dados?.tamanho_trecho ?? "…"} caracteres e cada trecho vira um
            vetor com o modelo <code>{dados?.modelo_embeddings ?? "…"}</code>, guardado no Postgres com pgvector.
          </span>
        </li>
        <li>
          <strong>Planejador</strong>
          <span>Lê uma amostra do documento inteiro e define os tópicos que a prova vai cobrir.</span>
        </li>
        <li>
          <strong>Recuperação</strong>
          <span>
            Para cada tópico, a busca semântica traz os {dados?.trechos_por_topico ?? "…"} trechos mais relevantes do
            material.
          </span>
        </li>
        <li>
          <strong>Gerador</strong>
          <span>Escreve a questão e o gabarito só com esses trechos, e informa quais usou.</span>
        </li>
        <li>
          <strong>Revisor</strong>
          <span>
            Avalia clareza, dificuldade e fundamentação. Abaixo de nota {dados?.nota_minima_revisao ?? "…"} ou sem base
            no material, a questão é refeita com as críticas (até {dados?.max_tentativas_por_questao ?? "…"} versões).
          </span>
        </li>
      </ol>
      {sistema.isError && <p className="form-error">Não foi possível consultar o servidor.</p>}
    </div>
  );
}

function PainelConta() {
  return (
    <div className="settings-panel">
      <h2>Conta</h2>
      <p className="panel-intro">O login ainda não está disponível.</p>
      <p className="panel-text">
        Por enquanto, todas as provas ficam salvas neste servidor, sem separação por usuário, e as preferências ficam
        guardadas neste navegador. Contas individuais estão nos próximos passos do projeto.
      </p>
    </div>
  );
}

function PainelSobreIa() {
  const sistema = useQuery({ queryKey: ["sistema"], queryFn: api.sistema });
  const modelos = sistema.data?.modelos;
  return (
    <div className="settings-panel">
      <h2>Sobre a IA</h2>
      <p className="panel-intro">Os modelos usados por cada agente, servidos pela Groq.</p>
      <dl className="info-list">
        <div>
          <dt>Planejador</dt>
          <dd>{modelos?.planejador ?? "…"}</dd>
        </div>
        <div>
          <dt>Gerador</dt>
          <dd>{modelos?.gerador ?? "…"}</dd>
        </div>
        <div>
          <dt>Revisor</dt>
          <dd>{modelos?.revisor ?? "…"}</dd>
        </div>
      </dl>
    </div>
  );
}

function PainelStatus() {
  const saude = useQuery({ queryKey: ["saude"], queryFn: api.saude, retry: false });
  const situacao = saude.isError
    ? { rotulo: "API indisponível", classe: "falhou" }
    : saude.data && !saude.data.llm_configurado
      ? { rotulo: "Sem chave da Groq", classe: "falhou" }
      : saude.data
        ? { rotulo: "Tudo funcionando", classe: "ok" }
        : { rotulo: "Verificando…", classe: "" };
  return (
    <div className="settings-panel">
      <h2>
        <Cpu size={15} /> Status do serviço
      </h2>
      <p className="panel-intro">Conexão com a API e com o modelo de linguagem.</p>
      <span className={`status-tag ${situacao.classe}`}>{situacao.rotulo}</span>
      {saude.data && <p className="panel-text">Versão da API: {saude.data.versao}</p>}
    </div>
  );
}
