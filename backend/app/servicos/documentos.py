import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Configuracoes
from app.core.excecoes import ErroNaoEncontrado
from app.db.modelos import Documento, Trecho
from app.ingestao.divisor import dividir_em_trechos
from app.ingestao.extratores import extrair_texto, identificar_tipo
from app.rag.busca import ResultadoBusca, buscar_trechos_semelhantes
from app.rag.embeddings import Embedder

logger = logging.getLogger(__name__)


class ServicoDocumentos:
    def __init__(self, sessao: Session, embedder: Embedder, configuracoes: Configuracoes) -> None:
        self._sessao = sessao
        self._embedder = embedder
        self._configuracoes = configuracoes

    def ingerir(self, nome_arquivo: str, conteudo: bytes) -> tuple[Documento, bool]:
        """Extrai, divide, vetoriza e indexa o arquivo.

        Devolve o documento e se ele foi criado agora. Reenviar um arquivo com o
        mesmo conteúdo devolve o documento já indexado, sem refazer o trabalho.
        """
        tipo = identificar_tipo(nome_arquivo)
        hash_sha256 = hashlib.sha256(conteudo).hexdigest()

        existente = self._buscar_por_hash(hash_sha256)
        if existente is not None:
            return existente, False

        extraido = extrair_texto(conteudo, tipo)
        divididos = dividir_em_trechos(
            extraido,
            tamanho=self._configuracoes.tamanho_trecho,
            sobreposicao=self._configuracoes.sobreposicao_trecho,
        )
        vetores = self._embedder.embutir_trechos([dividido.texto for dividido in divididos])

        documento = Documento(
            nome_arquivo=nome_arquivo,
            tipo=tipo,
            tamanho_bytes=len(conteudo),
            hash_sha256=hash_sha256,
            total_caracteres=sum(len(pagina) for pagina in extraido.paginas),
            total_trechos=len(divididos),
            total_paginas=len(extraido.paginas) if extraido.paginado else None,
            trechos=[
                Trecho(
                    ordem=dividido.ordem,
                    pagina=dividido.pagina,
                    texto=dividido.texto,
                    embedding=vetor,
                )
                for dividido, vetor in zip(divididos, vetores, strict=True)
            ],
        )
        # Documento e vetores entram na mesma transação: ou tudo é gravado, ou nada.
        self._sessao.add(documento)
        try:
            self._sessao.commit()
        except IntegrityError:
            # Outro envio do mesmo arquivo terminou primeiro; o dele vale.
            self._sessao.rollback()
            existente = self._buscar_por_hash(hash_sha256)
            if existente is None:
                raise
            return existente, False

        logger.info("Documento %s indexado em %d trechos", documento.id, len(divididos))
        return documento, True

    def listar(self) -> list[Documento]:
        return list(self._sessao.scalars(select(Documento).order_by(Documento.criado_em.desc())))

    def obter(self, documento_id: str) -> Documento:
        documento = self._sessao.get(Documento, documento_id)
        if documento is None:
            raise ErroNaoEncontrado("Documento não encontrado.")
        return documento

    def excluir(self, documento_id: str) -> None:
        # Os trechos saem junto, pelo ON DELETE CASCADE da chave estrangeira.
        self._sessao.delete(self.obter(documento_id))
        self._sessao.commit()

    def buscar(self, documento_id: str, consulta: str, k: int) -> list[ResultadoBusca]:
        documento = self.obter(documento_id)
        vetor = self._embedder.embutir_consulta(consulta)
        return buscar_trechos_semelhantes(self._sessao, documento.id, vetor, k)

    def _buscar_por_hash(self, hash_sha256: str) -> Documento | None:
        return self._sessao.scalar(select(Documento).where(Documento.hash_sha256 == hash_sha256))
