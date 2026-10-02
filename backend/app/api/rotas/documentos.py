from typing import Annotated

from fastapi import APIRouter, Depends, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import Configuracoes, obter_configuracoes
from app.core.excecoes import ErroArquivoGrande
from app.db.base import obter_sessao
from app.esquemas.documentos import BuscaRequisicao, DocumentoResposta, TrechoEncontrado
from app.rag.banco_vetorial import BancoVetorial, obter_banco_vetorial
from app.rag.embeddings import Embedder, obter_embedder
from app.servicos.documentos import ServicoDocumentos

roteador = APIRouter(prefix="/documentos", tags=["documentos"])


def obter_servico(
    sessao: Annotated[Session, Depends(obter_sessao)],
    embedder: Annotated[Embedder, Depends(obter_embedder)],
    banco_vetorial: Annotated[BancoVetorial, Depends(obter_banco_vetorial)],
    configuracoes: Annotated[Configuracoes, Depends(obter_configuracoes)],
) -> ServicoDocumentos:
    return ServicoDocumentos(sessao, embedder, banco_vetorial, configuracoes)


Servico = Annotated[ServicoDocumentos, Depends(obter_servico)]

# As rotas são síncronas de propósito: extração e embeddings são trabalho de CPU,
# e o FastAPI roda funções `def` em um pool de threads, sem travar o event loop.


@roteador.post("", status_code=status.HTTP_201_CREATED)
def enviar_documento(
    arquivo: UploadFile,
    servico: Servico,
    configuracoes: Annotated[Configuracoes, Depends(obter_configuracoes)],
    resposta: Response,
) -> DocumentoResposta:
    limite = configuracoes.tamanho_max_upload_mb * 1024 * 1024
    conteudo = arquivo.file.read(limite + 1)
    if len(conteudo) > limite:
        raise ErroArquivoGrande(
            f"O arquivo excede o limite de {configuracoes.tamanho_max_upload_mb} MB."
        )

    documento, criado = servico.ingerir(arquivo.filename or "", conteudo)
    if not criado:
        resposta.status_code = status.HTTP_200_OK
    return DocumentoResposta.model_validate(documento)


@roteador.get("")
def listar_documentos(servico: Servico) -> list[DocumentoResposta]:
    return [DocumentoResposta.model_validate(documento) for documento in servico.listar()]


@roteador.get("/{documento_id}")
def obter_documento(documento_id: str, servico: Servico) -> DocumentoResposta:
    return DocumentoResposta.model_validate(servico.obter(documento_id))


@roteador.delete("/{documento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_documento(documento_id: str, servico: Servico) -> None:
    servico.excluir(documento_id)


@roteador.post("/{documento_id}/busca")
def buscar_trechos(
    documento_id: str, requisicao: BuscaRequisicao, servico: Servico
) -> list[TrechoEncontrado]:
    resultados = servico.buscar(documento_id, requisicao.consulta, requisicao.k)
    return [
        TrechoEncontrado(
            ordem=resultado.trecho.ordem,
            pagina=resultado.trecho.pagina,
            texto=resultado.trecho.texto,
            pontuacao=round(resultado.pontuacao, 4),
        )
        for resultado in resultados
    ]
