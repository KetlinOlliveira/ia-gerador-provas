import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  AlertTriangle,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Eye,
  FileText,
  LoaderCircle,
  MoreHorizontal,
  Search,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";

import { api, ErroApi, gerarNovamente } from "@/api/cliente";
import type { Dificuldade, ProvaResumo } from "@/api/tipos";
import { MenuExportar } from "@/components/menu-exportar";
import { Button } from "@/components/ui-button";
import { useFecharAoClicarFora, useValorComAtraso } from "@/hooks/use-utilitarios";
import { DIFICULDADES, dificuldadeDe } from "@/lib/configuracao-prova";
import { formatarData } from "@/lib/formatar";

export const Route = createFileRoute("/minhas-provas")({
  head: () => ({
    meta: [
      { title: "Minhas provas | PROVAI" },
      { name: "description", content: "Consulte e organize o histórico de provas geradas no PROVAI." },
    ],
  }),
  component: PaginaHistorico,
});

const POR_PAGINA = 5;
const EM_ANDAMENTO = new Set(["pendente", "gerando"]);

function PaginaHistorico() {
  const [busca, setBusca] = useState("");
  const [dificuldade, setDificuldade] = useState<Dificuldade | "">("");
  const [ordem, setOrdem] = useState<"recentes" | "antigas">("recentes");
  const [pagina, setPagina] = useState(1);
  const buscaAtrasada = useValorComAtraso(busca.trim());

  useEffect(() => setPagina(1), [buscaAtrasada, dificuldade, ordem]);

  const lista = useQuery({
    queryKey: ["provas", "lista", { buscaAtrasada, dificuldade, ordem, pagina }],
    queryFn: () =>
      api.listarProvas({
        busca: buscaAtrasada,
        dificuldade: dificuldade || undefined,
        ordem,
        pagina,
        por_pagina: POR_PAGINA,
      }),
    placeholderData: keepPreviousData,
    // Enquanto alguma prova da página está sendo gerada, a lista se atualiza sozinha.
    refetchInterval: (consulta) =>
      consulta.state.data?.itens.some((prova) => EM_ANDAMENTO.has(prova.status)) ? 3000 : false,
  });
  const estatisticas = useQuery({ queryKey: ["provas", "estatisticas"], queryFn: api.estatisticas });

  const total = lista.data?.total ?? 0;
  const itens = lista.data?.itens ?? [];
  const totalDePaginas = Math.max(1, Math.ceil(total / POR_PAGINA));
  const semFiltros = !buscaAtrasada && !dificuldade;

  return (
    <div className="content-layout">
      <aside className="content-aside">
        <div className="page-label">
          <span className="sparkle-mark">✧</span>Minhas provas
        </div>
        <h1 className="section-title">
          Suas provas,
          <br />
          sempre <span className="gradient-text">disponíveis</span>
        </h1>
        <p className="section-description">
          Acesse, visualize, exporte ou gere novamente suas provas criadas com inteligência artificial.
        </p>
        <div className="stat-card">
          <div className="stat-ring">
            <Sparkles size={20} />
          </div>
          <div className="stat-value">
            <span>Total de provas</span>
            <strong>{estatisticas.data?.total ?? "–"}</strong>
          </div>
          <div className="stat-growth">
            ↑ {estatisticas.data?.este_mes ?? 0}
            <span>este mês</span>
          </div>
        </div>
      </aside>
      <section className="content-main">
        <div className="history-toolbar">
          <div className="search-wrap">
            <input
              value={busca}
              onChange={(evento) => setBusca(evento.target.value)}
              placeholder="Buscar por nome da prova..."
              aria-label="Buscar provas"
            />
            <Search size={15} />
          </div>
          <div className="filters">
            <select
              className="filter-select"
              value={dificuldade}
              onChange={(evento) => setDificuldade(evento.target.value as Dificuldade | "")}
              aria-label="Filtrar dificuldade"
            >
              <option value="">Todas as dificuldades</option>
              {DIFICULDADES.map((item) => (
                <option key={item.valor} value={item.valor}>
                  {item.rotulo}
                </option>
              ))}
            </select>
            <select
              className="filter-select"
              value={ordem}
              onChange={(evento) => setOrdem(evento.target.value as "recentes" | "antigas")}
              aria-label="Ordenar provas"
            >
              <option value="recentes">Mais recentes</option>
              <option value="antigas">Mais antigas</option>
            </select>
          </div>
        </div>

        <div className="exam-list">
          {lista.isPending ? (
            <div className="empty-state">
              <LoaderCircle size={24} className="spin" />
              <strong>Carregando suas provas</strong>
            </div>
          ) : lista.isError ? (
            <div className="empty-state">
              <AlertTriangle size={24} />
              <strong>Não foi possível carregar as provas</strong>
              <span>{lista.error.message}</span>
            </div>
          ) : itens.length ? (
            itens.map((prova) => <LinhaProva key={prova.id} prova={prova} />)
          ) : semFiltros ? (
            <div className="empty-state">
              <FileText size={24} />
              <strong>Nenhuma prova por aqui ainda</strong>
              <span>
                <Link to="/" className="inline-link">
                  Crie sua primeira prova
                </Link>{" "}
                a partir de um material de aula.
              </span>
            </div>
          ) : (
            <div className="empty-state">
              <Search size={24} />
              <strong>Nenhuma prova encontrada</strong>
              <span>Tente ajustar a busca ou os filtros.</span>
            </div>
          )}
        </div>

        <div className="pagination">
          <span>
            Mostrando {itens.length ? (pagina - 1) * POR_PAGINA + 1 : 0}–{(pagina - 1) * POR_PAGINA + itens.length} de{" "}
            {total} {total === 1 ? "prova" : "provas"}
          </span>
          <div className="page-controls">
            <Button
              variant="ghost"
              onClick={() => setPagina((atual) => Math.max(1, atual - 1))}
              disabled={pagina === 1}
              aria-label="Página anterior"
            >
              <ChevronLeft size={15} />
            </Button>
            {Array.from({ length: totalDePaginas }, (_, indice) => indice + 1).map((numero) => (
              <Button
                key={numero}
                className={pagina === numero ? "is-current" : ""}
                onClick={() => setPagina(numero)}
                aria-current={pagina === numero ? "page" : undefined}
              >
                {numero}
              </Button>
            ))}
            <Button
              variant="ghost"
              onClick={() => setPagina((atual) => Math.min(totalDePaginas, atual + 1))}
              disabled={pagina === totalDePaginas}
              aria-label="Próxima página"
            >
              <ChevronRight size={15} />
            </Button>
          </div>
        </div>
      </section>
      <aside className="content-art">
        <div className="orbit-art">
          <FileText size={61} strokeWidth={1.5} />
          <span className="orbit-spark one">✦</span>
          <span className="orbit-spark two">✦</span>
        </div>
        <p>Cada prova é um passo para um aprendizado mais inteligente.</p>
        <span className="art-underline" />
      </aside>
    </div>
  );
}

function LinhaProva({ prova }: { prova: ProvaResumo }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [menuAberto, setMenuAberto] = useState(false);
  const [confirmandoExclusao, setConfirmandoExclusao] = useState(false);
  const [erro, setErro] = useState("");
  const fecharMenu = () => {
    setMenuAberto(false);
    setConfirmandoExclusao(false);
  };
  const menuRef = useFecharAoClicarFora<HTMLDivElement>(menuAberto, fecharMenu);

  const atualizarLista = () => queryClient.invalidateQueries({ queryKey: ["provas"] });
  const excluir = useMutation({
    mutationFn: () => api.excluirProva(prova.id),
    onSuccess: atualizarLista,
    onError: (falha) => setErro(falha instanceof ErroApi ? falha.message : "Não foi possível excluir."),
  });
  const regenerar = useMutation({
    mutationFn: () => gerarNovamente(prova.id),
    onSuccess: atualizarLista,
    onError: (falha) => setErro(falha instanceof ErroApi ? falha.message : "Não foi possível gerar de novo."),
  });

  const dificuldade = dificuldadeDe(prova.dificuldade);
  const andamento = EM_ANDAMENTO.has(prova.status);
  const falhou = prova.status === "falhou";

  return (
    <article className="exam-row">
      <div className="exam-avatar">
        {andamento ? (
          <LoaderCircle size={18} className="spin" />
        ) : falhou ? (
          <AlertTriangle size={18} />
        ) : (
          <FileText size={18} />
        )}
      </div>
      <div className="exam-info">
        <strong>{prova.titulo}</strong>
        <div className="exam-meta">
          <span>
            <CalendarDays size={11} />
            {formatarData(prova.criado_em)}
          </span>
          <span>
            <FileText size={11} />
            {prova.total_questoes} {prova.total_questoes === 1 ? "questão" : "questões"}
          </span>
          <span className={`difficulty-tag ${dificuldade.classe}`}>{dificuldade.rotulo}</span>
          {andamento && <span className="status-tag gerando">Gerando…</span>}
          {falhou && <span className="status-tag falhou">Falhou</span>}
        </div>
        {erro && (
          <p className="row-error" role="alert">
            {erro}
          </p>
        )}
      </div>
      <div className="exam-actions">
        <Button
          variant="icon"
          onClick={() => void navigate({ to: "/provas/$provaId", params: { provaId: prova.id } })}
          aria-label={`Visualizar ${prova.titulo}`}
          title="Visualizar"
        >
          <Eye size={15} />
        </Button>
        <MenuExportar provaId={prova.id} titulo={prova.titulo} disponivel={prova.status === "concluida"} />
        <div className="exam-menu" ref={menuRef}>
          <Button
            variant="icon"
            onClick={() => (menuAberto ? fecharMenu() : setMenuAberto(true))}
            aria-label={`Mais opções para ${prova.titulo}`}
            aria-expanded={menuAberto}
            title="Mais opções"
          >
            <MoreHorizontal size={15} />
          </Button>
          {menuAberto && (
            <div className="exam-menu-popover" role="menu">
              <Button
                variant="ghost"
                role="menuitem"
                disabled={!prova.documento_id || regenerar.isPending}
                title={prova.documento_id ? undefined : "O material desta prova foi excluído"}
                onClick={() => {
                  setErro("");
                  regenerar.mutate();
                  fecharMenu();
                }}
              >
                Gerar novamente
              </Button>
              <Button
                variant="ghost"
                role="menuitem"
                className={confirmandoExclusao ? "is-danger" : ""}
                disabled={excluir.isPending}
                onClick={() => {
                  if (!confirmandoExclusao) {
                    setConfirmandoExclusao(true);
                    return;
                  }
                  setErro("");
                  excluir.mutate();
                  fecharMenu();
                }}
              >
                {confirmandoExclusao ? "Confirmar exclusão" : "Excluir"}
              </Button>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
