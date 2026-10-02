import asyncio
import json
import logging
from enum import StrEnum
from functools import lru_cache
from typing import Any

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

    Há três camadas de proteção para a saída:
    1. No modo estrito, o provedor só deixa o modelo gerar JSON que obedeça ao esquema.
    2. Falhas de transporte (429, conexão, 5xx) são retentadas pelo SDK, respeitando
       o `retry-after`.
    3. Regras que o JSON Schema não expressa (somas, contagens, combinações) ficam nos
       validadores Pydantic; quando falham, o erro é devolvido ao modelo para correção.
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
        max_tokens: int = 4096,
    ) -> T:
        cliente = self._obter_cliente()
        modelo = self._modelos[papel]
        estrito = self._configuracoes.llm_saida_estrita
        if not estrito:
            sistema = f"{sistema}\n\n{_instrucoes_de_formato(esquema)}"
        mensagens_base = [
            {"role": "system", "content": sistema},
            {"role": "user", "content": usuario},
        ]
        parametros = self._parametros(modelo, esquema, estrito)
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
                        **parametros,
                    )
            except BadRequestError as erro:
                # A Groq rejeita a requisição quando o modelo emite JSON malformado;
                # é falha de geração e vale retentar, não é erro de quem chamou.
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
                    "%s/%s: saída reprovada na validação de %s (tentativa %d): %s",
                    papel,
                    modelo,
                    esquema.__name__,
                    tentativa,
                    _resumir_erros(erro),
                )
                mensagens = [
                    *mensagens_base,
                    {"role": "assistant", "content": conteudo},
                    {"role": "user", "content": _pedido_de_correcao(erro)},
                ]

        raise ErroSaidaLLM(
            f"O modelo não retornou uma resposta válida após {tentativas} tentativas."
        ) from ultimo_erro

    def _parametros(self, modelo: str, esquema: type[BaseModel], estrito: bool) -> dict[str, Any]:
        parametros: dict[str, Any] = {}
        if estrito:
            parametros["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": esquema.__name__,
                    "strict": True,
                    "schema": esquema_estrito(esquema),
                },
            }
        else:
            parametros["response_format"] = {"type": "json_object"}
        # Os modelos gpt-oss raciocinam antes de responder, e esses tokens contam no
        # limite por minuto; outros modelos recusam o parâmetro.
        if modelo.startswith("openai/gpt-oss"):
            parametros["reasoning_effort"] = self._configuracoes.llm_esforco_raciocinio
        return parametros


# Restrições que o modo estrito não aceita. Elas continuam valendo, porque o
# Pydantic as verifica na validação, e as descrições dos campos as explicam ao modelo.
_PALAVRAS_NAO_SUPORTADAS = {
    "default",
    "title",
    "minItems",
    "maxItems",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "pattern",
    "format",
}


def esquema_estrito(esquema: type[BaseModel]) -> dict[str, Any]:
    """Adapta o JSON Schema do Pydantic às regras do modo estrito: todo objeto lista
    todos os campos como obrigatórios e proíbe campos extras."""
    return _tornar_estrito(esquema.model_json_schema())


def _tornar_estrito(no: Any) -> Any:
    if isinstance(no, list):
        return [_tornar_estrito(item) for item in no]
    if not isinstance(no, dict):
        return no

    novo: dict[str, Any] = {}
    for chave, valor in no.items():
        if chave in _PALAVRAS_NAO_SUPORTADAS:
            continue
        if chave in ("properties", "$defs"):
            # Aqui as chaves são nomes de campos, não palavras do JSON Schema.
            novo[chave] = {nome: _tornar_estrito(sub) for nome, sub in valor.items()}
        elif chave == "const":
            novo["enum"] = [valor]
        else:
            novo[chave] = _tornar_estrito(valor)

    if "properties" in novo:
        novo["required"] = list(novo["properties"])
        novo["additionalProperties"] = False
    return novo


def _instrucoes_de_formato(esquema: type[BaseModel]) -> str:
    esquema_json = json.dumps(esquema.model_json_schema(), ensure_ascii=False)
    return (
        "Responda APENAS com um objeto JSON válido, sem markdown e sem texto fora do JSON. "
        f"O objeto deve obedecer a este JSON Schema:\n{esquema_json}"
    )


def _resumir_erros(erro: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(parte) for parte in item['loc']) or '(raiz)'}: {item['msg']}"
        for item in erro.errors()
    )


def _pedido_de_correcao(erro: ValidationError) -> str:
    return (
        f"Sua resposta anterior não obedece às regras. Problemas: {_resumir_erros(erro)}. "
        "Responda novamente apenas com o objeto JSON corrigido."
    )


@lru_cache
def obter_cliente_llm() -> ClienteLLM:
    return ClienteLLM(obter_configuracoes())
