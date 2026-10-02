import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Configuracoes
from app.core.excecoes import ErroNaoEncontrado
from app.db.modelos import Documento
from app.ingestao.divisor import dividir_em_trechos
from app.ingestao.extratores import extrair_texto, identificar_tipo
from app.rag.banco_vetorial import BancoVetorial, ResultadoBusca
from app.rag.embeddings import Embedder

logger = logging.getLogger(__name__)


class ServicoDocumentos:
    def __init__(
        self,
        sessao: Session,
        embedder: Embedder,
        banco_vetorial: BancoVetorial,
        configuracoes: Configuracoes,
    ) -> None:
        self._sessao = sessao
        self._embedder = embedder
        self._banco_vetorial = banco_vetorial
        self._configuracoes = configuracoes

    def ingerir(self, nome_arquivo: str, conteudo: bytes) -> tuple[Documento, bool]:
        """Extrai, divide, vetoriza e indexa o arquivo.

        Devolve o documento e se ele foi criado agora. Reenviar um arquivo com o
        mesmo conteúdo devolve o documento já indexado, sem refazer o trabalho.
        """
        tipo = identificar_tipo(nome_arquivo)
        hash_sha256 = hashlib.sha256(conteudo).hexdigest()

        existente = self._sessao.scalar(
            select(Documento).where(Documento.hash_sha256 == hash_sha256)
        )
        if existente is not None:
            return existente, False

        extraido = extrair_texto(conteudo, tipo)
        trechos = dividir_em_trechos(
            extraido,
            tamanho=self._configuracoes.tamanho_trecho,
            sobreposicao=self._configuracoes.sobreposicao_trecho,
        )
        vetores = self._embedder.embutir_trechos([trecho.texto for trecho in trechos])

        documento = Documento(
            nome_arquivo=nome_arquivo,
            tipo=tipo,
            tamanho_bytes=len(conteudo),
            hash_sha256=hash_sha256,
            total_caracteres=sum(len(pagina) for pagina in extraido.paginas),
            total_trechos=len(trechos),
            total_paginas=len(extraido.paginas) if extraido.paginado else None,
        )
        self._sessao.add(documento)
        self._sessao.flush()  # gera o id usado para marcar os vetores

        # Os dois bancos não compartilham transação: se o commit falhar depois de
        # os vetores entrarem, eles são removidos para não ficarem órfãos.
        self._banco_vetorial.adicionar(documento.id, trechos, vetores)
        try:
            self._sessao.commit()
        except Exception:
            self._sessao.rollback()
            self._banco_vetorial.remover(documento.id)
            raise

        logger.info("Documento %s indexado em %d trechos", documento.id, len(trechos))
        return documento, True

    def listar(self) -> list[Documento]:
        return list(self._sessao.scalars(select(Documento).order_by(Documento.criado_em.desc())))

    def obter(self, documento_id: str) -> Documento:
        documento = self._sessao.get(Documento, documento_id)
        if documento is None:
            raise ErroNaoEncontrado("Documento não encontrado.")
        return documento

    def excluir(self, documento_id: str) -> None:
        documento = self.obter(documento_id)
        # Vetores primeiro: se algo falhar aqui, o documento continua listado e a
        # exclusão pode ser repetida. Na ordem inversa sobrariam vetores sem dono.
        self._banco_vetorial.remover(documento.id)
        self._sessao.delete(documento)
        self._sessao.commit()

    def buscar(self, documento_id: str, consulta: str, k: int) -> list[ResultadoBusca]:
        documento = self.obter(documento_id)
        vetor = self._embedder.embutir_consulta(consulta)
        return self._banco_vetorial.buscar(documento.id, vetor, k)
