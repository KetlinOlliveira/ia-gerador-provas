import asyncio

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.agentes.orquestrador import AoProgredir, OrquestradorProva
from app.core.config import Configuracoes
from app.core.excecoes import ErroNaoEncontrado
from app.db.modelos import Documento, Trecho
from app.esquemas.provas import ConfiguracaoProva, Fonte, Prova
from app.llm.cliente import ClienteLLM
from app.rag.busca import buscar_trechos_semelhantes
from app.rag.embeddings import Embedder


class ServicoProvas:
    """Liga os agentes ao banco: lê os trechos do documento e faz a recuperação."""

    def __init__(
        self,
        fabrica_sessao: sessionmaker[Session],
        embedder: Embedder,
        llm: ClienteLLM,
        configuracoes: Configuracoes,
    ) -> None:
        self._fabrica_sessao = fabrica_sessao
        self._embedder = embedder
        self._llm = llm
        self._configuracoes = configuracoes

    async def gerar(
        self,
        documento_id: str,
        configuracao: ConfiguracaoProva,
        ao_progredir: AoProgredir | None = None,
    ) -> Prova:
        trechos = await asyncio.to_thread(self._trechos_do_documento, documento_id)

        async def recuperar(consulta: str, k: int) -> list[Fonte]:
            # Embeddings e banco são síncronos; cada busca roda numa thread com sessão
            # própria, porque sessões do SQLAlchemy não podem ser compartilhadas entre threads.
            return await asyncio.to_thread(self._buscar, documento_id, consulta, k)

        orquestrador = OrquestradorProva(self._llm, recuperar, self._configuracoes)
        return await orquestrador.gerar(documento_id, trechos, configuracao, ao_progredir)

    def _trechos_do_documento(self, documento_id: str) -> list[Fonte]:
        with self._fabrica_sessao() as sessao:
            if sessao.get(Documento, documento_id) is None:
                raise ErroNaoEncontrado("Documento não encontrado.")
            trechos = sessao.scalars(
                select(Trecho).where(Trecho.documento_id == documento_id).order_by(Trecho.ordem)
            )
            return [_para_fonte(trecho) for trecho in trechos]

    def _buscar(self, documento_id: str, consulta: str, k: int) -> list[Fonte]:
        vetor = self._embedder.embutir_consulta(consulta)
        with self._fabrica_sessao() as sessao:
            resultados = buscar_trechos_semelhantes(sessao, documento_id, vetor, k)
            # Na ordem do documento, que é como o conteúdo faz sentido para quem lê.
            fontes = [_para_fonte(resultado.trecho) for resultado in resultados]
        return sorted(fontes, key=lambda fonte: fonte.ordem)


def _para_fonte(trecho: Trecho) -> Fonte:
    return Fonte(ordem=trecho.ordem, pagina=trecho.pagina, texto=trecho.texto)
