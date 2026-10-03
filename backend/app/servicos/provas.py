import asyncio
import logging
from datetime import UTC, datetime
from pathlib import PurePath

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.agentes.orquestrador import EventoProgresso
from app.core.excecoes import ErroAplicacao, ErroNaoEncontrado
from app.db.modelos import Documento, Prova
from app.esquemas.provas import (
    ConfiguracaoProva,
    CriarProvaRequisicao,
    Dificuldade,
    EstatisticasProvas,
    PaginaProvas,
    ProgressoProva,
    ProvaDetalhe,
    ProvaResumo,
    StatusProva,
)
from app.esquemas.provas import (
    Prova as ProvaGerada,
)
from app.servicos.geracao import GeradorDeProvas

logger = logging.getLogger(__name__)

MENSAGEM_INTERROMPIDA = (
    "A geração foi interrompida porque o servidor reiniciou. Gere a prova novamente."
)


class ServicoProvas:
    """Ciclo de vida das provas: criação, geração em segundo plano e histórico.

    Cada operação abre a própria sessão, porque a geração roda depois que a
    requisição que a pediu já terminou.
    """

    def __init__(self, fabrica_sessao: sessionmaker[Session], gerador: GeradorDeProvas) -> None:
        self._fabrica_sessao = fabrica_sessao
        self._gerador = gerador

    # ---------- Criação e geração ----------

    def criar(self, requisicao: CriarProvaRequisicao) -> ProvaResumo:
        with self._fabrica_sessao() as sessao:
            documento = sessao.get(Documento, requisicao.documento_id)
            if documento is None:
                raise ErroNaoEncontrado("Documento não encontrado.")
            configuracao = requisicao.configuracao
            prova = Prova(
                documento_id=documento.id,
                titulo=(requisicao.titulo or "").strip() or _titulo_do_arquivo(documento),
                dificuldade=configuracao.dificuldade,
                total_questoes=configuracao.total,
                configuracao=configuracao.model_dump(mode="json"),
                status=StatusProva.PENDENTE,
                mensagem="Na fila para geração",
            )
            sessao.add(prova)
            sessao.commit()
            return _resumo(prova)

    async def executar(self, prova_id: str) -> None:
        """Gera a prova e grava o resultado. Nunca levanta: falhas viram status."""
        try:
            documento_id, configuracao = await asyncio.to_thread(self._iniciar, prova_id)
            resultado = await self._gerador.gerar(
                documento_id,
                configuracao,
                lambda evento: self._salvar_progresso(prova_id, evento),
            )
        except Exception as erro:
            logger.exception("Falha ao gerar a prova %s", prova_id)
            mensagem = (
                erro.mensagem
                if isinstance(erro, ErroAplicacao)
                else "Erro inesperado ao gerar a prova. Tente novamente."
            )
            await asyncio.to_thread(self._finalizar_com_falha, prova_id, mensagem)
            return
        await asyncio.to_thread(self._finalizar_com_sucesso, prova_id, resultado)

    def _iniciar(self, prova_id: str) -> tuple[str, ConfiguracaoProva]:
        with self._fabrica_sessao() as sessao:
            prova = sessao.get(Prova, prova_id)
            if prova is None:
                raise ErroNaoEncontrado("Prova não encontrada.")
            if prova.documento_id is None:
                raise ErroNaoEncontrado("O material desta prova foi excluído.")
            prova.status = StatusProva.GERANDO
            prova.mensagem = "Iniciando"
            sessao.commit()
            return prova.documento_id, ConfiguracaoProva.model_validate(prova.configuracao)

    def _salvar_progresso(self, prova_id: str, evento: EventoProgresso) -> None:
        # Chamado de dentro do event loop, de forma síncrona. É uma escrita curta,
        # feita poucas vezes por prova; não compensa a complexidade de uma fila.
        with self._fabrica_sessao() as sessao:
            sessao.execute(
                update(Prova)
                .where(Prova.id == prova_id)
                .values(
                    etapa=evento.etapa,
                    mensagem=evento.mensagem[:255],
                    questoes_concluidas=evento.concluidas,
                )
            )
            sessao.commit()

    def _finalizar_com_sucesso(self, prova_id: str, resultado: ProvaGerada) -> None:
        with self._fabrica_sessao() as sessao:
            prova = sessao.get(Prova, prova_id)
            if prova is None:  # excluída enquanto era gerada
                return
            prova.status = StatusProva.CONCLUIDA
            prova.mensagem = "Prova pronta"
            prova.questoes_concluidas = len(resultado.questoes)
            prova.resultado = resultado.model_dump(mode="json", include={"topicos", "questoes"})
            prova.duracao_segundos = resultado.duracao_segundos
            prova.concluido_em = datetime.now(UTC)
            sessao.commit()

    def _finalizar_com_falha(self, prova_id: str, mensagem: str) -> None:
        with self._fabrica_sessao() as sessao:
            sessao.execute(
                update(Prova)
                .where(Prova.id == prova_id)
                .values(
                    status=StatusProva.FALHOU,
                    erro=mensagem,
                    mensagem="Falha na geração",
                    concluido_em=datetime.now(UTC),
                )
            )
            sessao.commit()

    # ---------- Consulta ----------

    def listar(
        self,
        *,
        busca: str | None,
        dificuldade: Dificuldade | None,
        mais_antigas_primeiro: bool,
        pagina: int,
        por_pagina: int,
    ) -> PaginaProvas:
        filtros = []
        if busca:
            filtros.append(Prova.titulo.ilike(f"%{_escapar_like(busca.strip())}%", escape="\\"))
        if dificuldade:
            filtros.append(Prova.dificuldade == dificuldade)
        ordem = Prova.criado_em.asc() if mais_antigas_primeiro else Prova.criado_em.desc()

        with self._fabrica_sessao() as sessao:
            total = sessao.scalar(select(func.count()).select_from(Prova).where(*filtros))
            provas = sessao.scalars(
                select(Prova)
                .where(*filtros)
                .order_by(ordem, Prova.id)
                .offset((pagina - 1) * por_pagina)
                .limit(por_pagina)
            )
            return PaginaProvas(
                itens=[_resumo(prova) for prova in provas],
                total=total or 0,
                pagina=pagina,
                por_pagina=por_pagina,
            )

    def estatisticas(self) -> EstatisticasProvas:
        inicio_do_mes = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        with self._fabrica_sessao() as sessao:
            total = sessao.scalar(select(func.count()).select_from(Prova))
            este_mes = sessao.scalar(
                select(func.count()).select_from(Prova).where(Prova.criado_em >= inicio_do_mes)
            )
            return EstatisticasProvas(total=total or 0, este_mes=este_mes or 0)

    def obter(self, prova_id: str) -> ProvaDetalhe:
        with self._fabrica_sessao() as sessao:
            return _detalhe(self._carregar(sessao, prova_id))

    def obter_progresso(self, prova_id: str) -> ProgressoProva:
        with self._fabrica_sessao() as sessao:
            return _progresso(self._carregar(sessao, prova_id))

    def excluir(self, prova_id: str) -> None:
        with self._fabrica_sessao() as sessao:
            sessao.delete(self._carregar(sessao, prova_id))
            sessao.commit()

    @staticmethod
    def _carregar(sessao: Session, prova_id: str) -> Prova:
        prova = sessao.get(Prova, prova_id)
        if prova is None:
            raise ErroNaoEncontrado("Prova não encontrada.")
        return prova


def marcar_provas_interrompidas(fabrica_sessao: sessionmaker[Session]) -> int:
    """Na subida do servidor, nenhuma geração está de fato rodando: as que
    ficaram pendentes ou em andamento morreram com o processo anterior.

    Pressupõe um único processo da API; com vários, cada um derrubaria as
    gerações dos outros, e o certo seria uma fila de tarefas dedicada.
    """
    with fabrica_sessao() as sessao:
        resultado = sessao.execute(
            update(Prova)
            .where(Prova.status.in_([StatusProva.PENDENTE, StatusProva.GERANDO]))
            .values(
                status=StatusProva.FALHOU,
                erro=MENSAGEM_INTERROMPIDA,
                mensagem="Falha na geração",
                concluido_em=datetime.now(UTC),
            )
        )
        sessao.commit()
        return resultado.rowcount


def _titulo_do_arquivo(documento: Documento) -> str:
    nome = PurePath(documento.nome_arquivo).stem.replace("_", " ").replace("-", " ")
    return " ".join(nome.split()) or "Prova sem título"


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _resumo(prova: Prova) -> ProvaResumo:
    return ProvaResumo(
        id=prova.id,
        titulo=prova.titulo,
        documento_id=prova.documento_id,
        status=StatusProva(prova.status),
        dificuldade=Dificuldade(prova.dificuldade),
        total_questoes=prova.total_questoes,
        criado_em=prova.criado_em,
        concluido_em=prova.concluido_em,
    )


def _progresso(prova: Prova) -> ProgressoProva:
    return ProgressoProva(
        status=StatusProva(prova.status),
        etapa=prova.etapa,
        mensagem=prova.mensagem,
        concluidas=prova.questoes_concluidas,
        total=prova.total_questoes,
        erro=prova.erro,
    )


def _detalhe(prova: Prova) -> ProvaDetalhe:
    resultado = prova.resultado or {}
    return ProvaDetalhe(
        **_resumo(prova).model_dump(),
        configuracao=ConfiguracaoProva.model_validate(prova.configuracao),
        progresso=_progresso(prova),
        duracao_segundos=prova.duracao_segundos,
        topicos=resultado.get("topicos", []),
        questoes=resultado.get("questoes", []),
    )
