import asyncio
import json
import logging
from enum import StrEnum
from functools import lru_cache

from groq import APIError, AsyncGroq, BadRequestError
from pydantic import BaseModel, ValidationError

from app.core.config import Configuracoes, obter_configuracoes
from app.core.excecoes import ErroLLM, ErroLLMNaoConfigurado, ErroSaidaLLM

logger = logging.getLogger(__name__)


class PapelModelo(StrEnum):
    PLANEJADOR = "planejador"
    GERADOR = "gerador"
    REVISOR = "revisor"


class ClienteLLM:
    """Encapsula a Groq e devolve objetos Pydantic validados em vez de texto cru.

    Falhas de transporte (429, conexão, 5xx) são retentadas pelo SDK com espera
    progressiva, respeitando o `retry-after`. Esta classe acrescenta o segundo
    tipo de retentativa: quando o modelo responde com um JSON que não obedece ao
    esquema, o erro de validação é devolvido a ele para que se corrija.
    """

    def __init__(self, configuracoes: Configuracoes, cliente: AsyncGroq | None = None) -> None:
        self._configuracoes = configuracoes
        self._cliente = cliente
        self._semaforo = asyncio.Semaphore(configuracoes.llm_max_concorrencia)
        self._modelos = {
            PapelModelo.PLANEJADOR: configuracoes.modelo_planejador,
            PapelModelo.GERADOR: configuracoes.modelo_gerador,
            PapelModelo.REVISOR: configuracoes.modelo_revisor,
        }

    def _obter_cliente(self) -> AsyncGroq:
        if self._cliente is None:
            if self._configuracoes.groq_api_key is None:
                raise ErroLLMNaoConfigurado(
                    "GROQ_API_KEY não configurada. Defina a chave no arquivo .env do backend."
                )
            self._cliente = AsyncGroq(
                api_key=self._configuracoes.groq_api_key.get_secret_value(),
                max_retries=self._configuracoes.llm_max_retentativas,
                timeout=self._configuracoes.llm_timeout_segundos,
            )
        return self._cliente

    async def completar_estruturado[T: BaseModel](
        self,
        *,
        papel: PapelModelo,
        sistema: str,
        usuario: str,
        esquema: type[T],
        temperatura: float = 0.4,
        max_tokens: int = 2048,
    ) -> T:
        cliente = self._obter_cliente()
        modelo = self._modelos[papel]
        mensagens_base = [
            {"role": "system", "content": f"{sistema}\n\n{_instrucoes_de_formato(esquema)}"},
            {"role": "user", "content": usuario},
        ]
        mensagens = mensagens_base
        tentativas = self._configuracoes.llm_max_tentativas_validacao
        ultimo_erro: Exception | None = None

        for tentativa in range(1, tentativas + 1):
            try:
                async with self._semaforo:
                    resposta = await cliente.chat.completions.create(
                        model=modelo,
                        messages=mensagens,
                        temperature=temperatura,
                        max_tokens=max_tokens,
                        response_format={"type": "json_object"},
                    )
            except BadRequestError as erro:
                # No modo JSON a Groq rejeita a requisição quando o modelo emite JSON
                # malformado; é falha de geração e vale retentar, não é erro de quem chamou.
                if "json_validate_failed" not in str(erro):
                    raise ErroLLM(f"Falha na chamada ao modelo: {erro}") from erro
                ultimo_erro = erro
                mensagens = mensagens_base
                logger.warning("%s/%s: JSON malformado (tentativa %d)", papel, modelo, tentativa)
                continue
            except APIError as erro:
                raise ErroLLM(f"Falha na chamada ao modelo: {erro}") from erro

            conteudo = resposta.choices[0].message.content or ""
            try:
                return esquema.model_validate_json(conteudo)
            except ValidationError as erro:
                ultimo_erro = erro
                logger.warning(
                    "%s/%s: saída reprovada na validação de %s (tentativa %d)",
                    papel,
                    modelo,
                    esquema.__name__,
                    tentativa,
                )
                mensagens = [
                    *mensagens_base,
                    {"role": "assistant", "content": conteudo},
                    {"role": "user", "content": _pedido_de_correcao(erro)},
                ]

        raise ErroSaidaLLM(
            f"O modelo não retornou uma resposta válida após {tentativas} tentativas."
        ) from ultimo_erro


def _instrucoes_de_formato(esquema: type[BaseModel]) -> str:
    esquema_json = json.dumps(esquema.model_json_schema(), ensure_ascii=False)
    return (
        "Responda APENAS com um objeto JSON válido, sem markdown e sem texto fora do JSON. "
        f"O objeto deve obedecer a este JSON Schema:\n{esquema_json}"
    )


def _pedido_de_correcao(erro: ValidationError) -> str:
    problemas = "; ".join(
        f"{'.'.join(str(parte) for parte in item['loc']) or '(raiz)'}: {item['msg']}"
        for item in erro.errors()
    )
    return (
        f"Sua resposta anterior não obedece ao esquema. Problemas: {problemas}. "
        "Responda novamente apenas com o objeto JSON corrigido."
    )


@lru_cache
def obter_cliente_llm() -> ClienteLLM:
    return ClienteLLM(obter_configuracoes())
