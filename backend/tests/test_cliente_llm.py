from types import SimpleNamespace
from typing import Literal

import httpx
import pytest
from groq import BadRequestError, RateLimitError
from pydantic import BaseModel, Field

from app.core.config import Configuracoes
from app.core.excecoes import ErroLLM, ErroLLMNaoConfigurado, ErroSaidaLLM
from app.llm.cliente import ClienteLLM, PapelModelo, esquema_estrito


class Topicos(BaseModel):
    topicos: list[str]


class GroqFalso:
    """Substitui o AsyncGroq: devolve respostas roteirizadas (ou levanta erros roteirizados)."""

    def __init__(self, *respostas):
        self._respostas = list(respostas)
        self.chamadas = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.chamadas.append(kwargs)
        resposta = self._respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        mensagem = SimpleNamespace(content=resposta)
        return SimpleNamespace(choices=[SimpleNamespace(message=mensagem)])


def criar_cliente(falso, **ajustes):
    configuracoes = Configuracoes(_env_file=None, groq_api_key="teste", **ajustes)
    return ClienteLLM(configuracoes, cliente=falso)


def erro_api(classe, status, mensagem):
    requisicao = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    resposta = httpx.Response(status, request=requisicao)
    return classe(mensagem, response=resposta, body=None)


async def perguntar(cliente, papel=PapelModelo.PLANEJADOR):
    return await cliente.completar_estruturado(
        papel=papel,
        sistema="Você é um planejador.",
        usuario="Extraia tópicos.",
        esquema=Topicos,
    )


async def test_devolve_objeto_validado_e_usa_saida_estrita():
    falso = GroqFalso('{"topicos": ["REST", "HTTP"]}')
    resultado = await perguntar(criar_cliente(falso))

    assert resultado == Topicos(topicos=["REST", "HTTP"])
    formato = falso.chamadas[0]["response_format"]
    assert formato["type"] == "json_schema"
    assert formato["json_schema"]["strict"] is True
    assert formato["json_schema"]["schema"]["required"] == ["topicos"]


async def test_sem_saida_estrita_usa_modo_json_com_esquema_no_prompt():
    falso = GroqFalso('{"topicos": ["REST"]}')
    await perguntar(criar_cliente(falso, llm_saida_estrita=False))

    chamada = falso.chamadas[0]
    assert chamada["response_format"] == {"type": "json_object"}
    assert '"topicos"' in chamada["messages"][0]["content"]


async def test_esforco_de_raciocinio_so_vai_para_modelos_gpt_oss():
    falso = GroqFalso('{"topicos": []}', '{"topicos": []}')
    cliente = criar_cliente(
        falso, modelo_planejador="openai/gpt-oss-20b", modelo_revisor="qwen/qwen3.8-27b"
    )

    await perguntar(cliente, PapelModelo.PLANEJADOR)
    await perguntar(cliente, PapelModelo.REVISOR)

    assert falso.chamadas[0]["reasoning_effort"] == "low"
    assert "reasoning_effort" not in falso.chamadas[1]


class Item(BaseModel):
    nome: str = Field(default="x", min_length=1, title="Nome")
    tipo: Literal["item"] = "item"


class Lista(BaseModel):
    itens: list[Item] = Field(min_length=1, max_length=3)
    observacao: str | None = None


def test_esquema_estrito_exige_todos_os_campos_e_proibe_extras():
    esquema = esquema_estrito(Lista)

    assert esquema["required"] == ["itens", "observacao"]
    assert esquema["additionalProperties"] is False
    item = esquema["$defs"]["Item"]
    assert item["required"] == ["nome", "tipo"]
    assert item["additionalProperties"] is False
    assert item["properties"]["tipo"]["enum"] == ["item"]
    # Restrições não suportadas saem do esquema (o Pydantic continua validando).
    assert "minItems" not in esquema["properties"]["itens"]
    assert "minLength" not in item["properties"]["nome"]
    assert "default" not in item["properties"]["nome"]


async def test_escolhe_modelo_pelo_papel():
    falso = GroqFalso('{"topicos": []}', '{"topicos": []}')
    cliente = criar_cliente(falso, modelo_planejador="pequeno", modelo_revisor="grande")

    await perguntar(cliente, PapelModelo.PLANEJADOR)
    await perguntar(cliente, PapelModelo.REVISOR)

    assert [chamada["model"] for chamada in falso.chamadas] == ["pequeno", "grande"]


async def test_devolve_erro_de_validacao_ao_modelo():
    falso = GroqFalso('{"topicos": "REST"}', '{"topicos": ["REST"]}')
    resultado = await perguntar(criar_cliente(falso))

    assert resultado.topicos == ["REST"]
    mensagens = falso.chamadas[1]["messages"]
    assert mensagens[-2] == {"role": "assistant", "content": '{"topicos": "REST"}'}
    assert "topicos" in mensagens[-1]["content"]


async def test_retenta_quando_o_provedor_rejeita_json_malformado():
    falso = GroqFalso(
        erro_api(BadRequestError, 400, "json_validate_failed: Failed to generate JSON"),
        '{"topicos": ["REST"]}',
    )
    assert (await perguntar(criar_cliente(falso))).topicos == ["REST"]


async def test_desiste_apos_o_maximo_de_tentativas_de_validacao():
    falso = GroqFalso("não é json", "{}")
    with pytest.raises(ErroSaidaLLM):
        await perguntar(criar_cliente(falso, llm_max_tentativas_validacao=2))
    assert len(falso.chamadas) == 2


async def test_falha_do_provedor_vira_erro_llm():
    falso = GroqFalso(erro_api(RateLimitError, 429, "rate limit exceeded"))
    with pytest.raises(ErroLLM):
        await perguntar(criar_cliente(falso))


async def test_outras_requisicoes_invalidas_nao_sao_retentadas():
    falso = GroqFalso(erro_api(BadRequestError, 400, "model not found"), '{"topicos": []}')
    with pytest.raises(ErroLLM):
        await perguntar(criar_cliente(falso))
    assert len(falso.chamadas) == 1


async def test_chave_ausente_levanta_erro_claro():
    cliente = ClienteLLM(Configuracoes(_env_file=None, groq_api_key=None))
    with pytest.raises(ErroLLMNaoConfigurado):
        await perguntar(cliente)
