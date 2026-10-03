import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { AlertTriangle, ArrowLeft, BookOpenCheck, Download, LoaderCircle, RotateCcw, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { api, ErroApi, gerarNovamente } from "@/api/cliente";
import type { ProvaDetalhe, QuestaoGerada } from "@/api/tipos";
import { OPCOES_EXPORTACAO } from "@/components/menu-exportar";
import { Button } from "@/components/ui-button";
import { dificuldadeDe, rotuloDoTipo } from "@/lib/configuracao-prova";
import { formatarData, formatarDuracao, formatarNota } from "@/lib/formatar";

export const Route = createFileRoute("/provas/$provaId")({
  head: () => ({ meta: [{ title: "Prova | PROVAI" }] }),
  component: PaginaProva,
});

const LETRAS = ["A", "B", "C", "D"];

function PaginaProva() {
  const { provaId } = Route.useParams();
  const [mostrarGabarito, setMostrarGabarito] = useState(false);
  const consulta = useQuery({
    queryKey: ["provas", "detalhe", provaId],
    queryFn: () => api.obterProva(provaId),
    refetchInterval: (estado) => {
      const status = estado.state.data?.status;
      return status === "pendente" || status === "gerando" ? 2000 : false;
    },
  });

  if (consulta.isPending) {
    return (
      <div className="status-page">
        <LoaderCircle size={28} className="spin" />
        <p>Carregando a prova…</p>
      </div>
    );
  }
  if (consulta.isError) {
    const naoExiste = consulta.error instanceof ErroApi && consulta.error.status === 404;
    return (
      <div className="status-page">
        <span className="sparkle-mark">✧</span>
        <h2>{naoExiste ? "Prova não encontrada" : "Não foi possível carregar a prova"}</h2>
        <p>{naoExiste ? "Ela pode ter sido excluída." : consulta.error.message}</p>
        <Link to="/minhas-provas" className="ui-button ui-button--primary status-page-action">
          Ver minhas provas
        </Link>
      </div>
    );
  }

  const prova = consulta.data;
  return (
    <div className="content-layout">
      <AsideDaProva prova={prova} mostrarGabarito={mostrarGabarito} aoAlternarGabarito={setMostrarGabarito} />
      <section className="content-main">
        {prova.status === "concluida" ? (
          <>
            <div className="topic-chips" aria-label="Tópicos identificados pelo planejador">
              {prova.topicos.map((topico) => (
                <span key={topico.titulo} className="topic-chip" title={topico.descricao}>
                  {topico.titulo}
                </span>
              ))}
            </div>
            <div className="question-list">
              {prova.questoes.map((questao) => (
                <CartaoQuestao key={questao.numero} questao={questao} mostrarGabarito={mostrarGabarito} />
              ))}
            </div>
          </>
        ) : prova.status === "falhou" ? (
          <PainelFalha prova={prova} />
        ) : (
          <PainelAndamento prova={prova} />
        )}
      </section>
      <aside className="content-art">
        <div className="orbit-art">
          <BookOpenCheck size={61} strokeWidth={1.5} />
          <span className="orbit-spark one">✦</span>
          <span className="orbit-spark two">✦</span>
        </div>
        <p>Cada questão nasce de um trecho do seu material.</p>
        <span className="art-underline" />
      </aside>
    </div>
  );
}

function AsideDaProva({
  prova,
  mostrarGabarito,
  aoAlternarGabarito,
}: {
  prova: ProvaDetalhe;
  mostrarGabarito: boolean;
  aoAlternarGabarito: (valor: boolean) => void;
}) {
  const dificuldade = dificuldadeDe(prova.dificuldade);
  const concluida = prova.status === "concluida";
  const notas = prova.questoes.map((questao) => questao.avaliacao.nota);
  const media = notas.length ? notas.reduce((soma, nota) => soma + nota, 0) / notas.length : null;
  const aprovadas = prova.questoes.filter((questao) => questao.aprovada).length;
  const duracao = formatarDuracao(prova.duracao_segundos);

  return (
    <aside className="content-aside">
      <Link to="/minhas-provas" className="back-link">
        <ArrowLeft size={14} /> Minhas provas
      </Link>
      <div className="page-label">
        <span className="sparkle-mark">✧</span>Prova
      </div>
      <h1 className="section-title exam-title">{prova.titulo}</h1>
      <div className="exam-meta exam-meta--large">
        <span>{formatarData(prova.criado_em)}</span>
        <span>
          {prova.total_questoes} {prova.total_questoes === 1 ? "questão" : "questões"}
        </span>
        <span className={`difficulty-tag ${dificuldade.classe}`}>{dificuldade.rotulo}</span>
        {duracao && <span>gerada em {duracao}</span>}
      </div>

      {concluida && (
        <>
          <div className="setting-row answer-toggle">
            <div>
              <span className="setting-label">Mostrar gabarito</span>
              <p>Respostas, justificativas e critérios de correção.</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={mostrarGabarito}
              aria-label="Mostrar gabarito"
              className={`switch ${mostrarGabarito ? "is-on" : ""}`}
              onClick={() => aoAlternarGabarito(!mostrarGabarito)}
            >
              <span />
            </button>
          </div>

          <div className="export-panel">
            <span className="setting-label">
              <Download size={13} /> Exportar
            </span>
            <div className="export-grid">
              {OPCOES_EXPORTACAO.map((opcao) => (
                <a
                  key={`${opcao.formato}-${opcao.versao}`}
                  className="ui-button ui-button--outline export-button"
                  href={api.urlExportacao(prova.id, opcao.formato, opcao.versao)}
                  download
                >
                  {opcao.rotulo}
                </a>
              ))}
            </div>
          </div>

          {media !== null && (
            <div className="stat-card">
              <div className="stat-ring">
                <ShieldCheck size={20} />
              </div>
              <div className="stat-value">
                <span>Nota média do revisor</span>
                <strong>{formatarNota(media)}</strong>
              </div>
              <div className="stat-growth">
                {aprovadas}/{prova.questoes.length}
                <span>aprovadas</span>
              </div>
            </div>
          )}
        </>
      )}
    </aside>
  );
}

function CartaoQuestao({ questao, mostrarGabarito }: { questao: QuestaoGerada; mostrarGabarito: boolean }) {
  const { conteudo, avaliacao } = questao;
  return (
    <article className="question-card">
      <header className="question-head">
        <span className="question-number">{String(questao.numero).padStart(2, "0")}</span>
        <div className="question-heading">
          <span className="question-type">{rotuloDoTipo(conteudo.tipo)}</span>
          <span className="question-topic">{questao.topico}</span>
        </div>
        <span
          className={`review-score ${questao.aprovada ? "is-approved" : "is-flagged"}`}
          title={questao.aprovada ? "Aprovada pelo agente revisor" : "O revisor apontou ressalvas"}
        >
          Revisor {avaliacao.nota}/10
        </span>
      </header>

      <p className="question-statement">{conteudo.enunciado}</p>

      {conteudo.tipo === "multipla_escolha" && (
        <>
          <ol className="alternatives">
            {conteudo.alternativas.map((texto, indice) => {
              const letra = LETRAS[indice]!;
              const correta = mostrarGabarito && letra === conteudo.resposta_correta;
              return (
                <li key={letra} className={correta ? "is-correct" : undefined}>
                  <span className="alt-letter">{letra}</span>
                  <span>{texto}</span>
                </li>
              );
            })}
          </ol>
          {mostrarGabarito && (
            <div className="answer-box">
              <strong>Resposta correta: {conteudo.resposta_correta}</strong>
              <p>{conteudo.justificativa}</p>
            </div>
          )}
        </>
      )}

      {conteudo.tipo === "verdadeiro_falso" && (
        <ul className="statements">
          {conteudo.afirmativas.map((afirmativa) => (
            <li key={afirmativa.texto}>
              <span className={`vf-mark ${mostrarGabarito ? (afirmativa.verdadeira ? "is-true" : "is-false") : ""}`}>
                {mostrarGabarito ? (afirmativa.verdadeira ? "V" : "F") : ""}
              </span>
              <div>
                <span>{afirmativa.texto}</span>
                {mostrarGabarito && <small>{afirmativa.justificativa}</small>}
              </div>
            </li>
          ))}
        </ul>
      )}

      {conteudo.tipo === "dissertativa" &&
        (mostrarGabarito ? (
          <div className="answer-box">
            <strong>Resposta esperada</strong>
            <p>{conteudo.resposta_esperada}</p>
            <strong>Critérios de correção</strong>
            <ul className="criteria">
              {conteudo.criterios.map((criterio) => (
                <li key={criterio.descricao}>
                  <span>{criterio.descricao}</span>
                  <span className="criteria-points">{formatarNota(criterio.pontos)} pts</span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="answer-lines" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
        ))}

      <details className="sources">
        <summary>
          Base no material: {questao.fontes.length} {questao.fontes.length === 1 ? "trecho" : "trechos"}
          {questao.tentativas > 1 && ` · refeita ${questao.tentativas - 1}x após a revisão`}
        </summary>
        {questao.fontes.map((fonte) => (
          <blockquote key={fonte.ordem}>
            <span>{fonte.pagina !== null ? `Página ${fonte.pagina}` : `Trecho ${fonte.ordem + 1}`}</span>
            {fonte.texto}
          </blockquote>
        ))}
        {avaliacao.problemas.length > 0 && (
          <div className="review-notes">
            <strong>Observações do revisor</strong>
            <ul>
              {avaliacao.problemas.map((problema) => (
                <li key={problema}>{problema}</li>
              ))}
            </ul>
          </div>
        )}
      </details>
    </article>
  );
}

function PainelAndamento({ prova }: { prova: ProvaDetalhe }) {
  const { concluidas, total, mensagem } = prova.progresso;
  const porcentagem = total ? Math.round((concluidas / total) * 100) : 0;
  return (
    <div className="settings-panel progress-panel">
      <LoaderCircle size={22} className="spin" />
      <h2>Gerando a prova</h2>
      <p className="panel-intro">{mensagem ?? "Na fila para geração"}</p>
      <div className="progress-line">
        <span style={{ width: `${Math.max(4, porcentagem)}%` }} />
      </div>
      <p className="panel-intro">
        {concluidas} de {total} questões prontas. Esta página se atualiza sozinha.
      </p>
    </div>
  );
}

function PainelFalha({ prova }: { prova: ProvaDetalhe }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const regenerar = useMutation({
    mutationFn: () => gerarNovamente(prova.id),
    onSuccess: (nova) => {
      void queryClient.invalidateQueries({ queryKey: ["provas"] });
      void navigate({ to: "/provas/$provaId", params: { provaId: nova.id } });
    },
  });
  return (
    <div className="settings-panel progress-panel">
      <AlertTriangle size={22} />
      <h2>A geração falhou</h2>
      <p className="panel-intro">{prova.progresso.erro ?? "Erro desconhecido."}</p>
      {regenerar.isError && (
        <p className="form-error" role="alert">
          {regenerar.error.message}
        </p>
      )}
      <Button
        variant="primary"
        className="panel-action"
        disabled={!prova.documento_id || regenerar.isPending}
        onClick={() => regenerar.mutate()}
      >
        <RotateCcw size={15} />
        Gerar novamente
      </Button>
    </div>
  );
}
