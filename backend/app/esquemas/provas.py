import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Dificuldade(StrEnum):
    FACIL = "facil"
    MEDIO = "medio"
    DIFICIL = "dificil"


class TipoQuestao(StrEnum):
    MULTIPLA_ESCOLHA = "multipla_escolha"
    DISSERTATIVA = "dissertativa"
    VERDADEIRO_FALSO = "verdadeiro_falso"


# ---------- Configuração escolhida pelo usuário ----------


class ConfiguracaoProva(BaseModel):
    dificuldade: Dificuldade
    multipla_escolha: int = Field(default=0, ge=0, le=20)
    dissertativas: int = Field(default=0, ge=0, le=10)
    verdadeiro_falso: int = Field(default=0, ge=0, le=10)

    @model_validator(mode="after")
    def _ao_menos_uma_questao(self) -> "ConfiguracaoProva":
        if self.total == 0:
            raise ValueError("A prova precisa de pelo menos uma questão.")
        return self

    @property
    def total(self) -> int:
        return self.multipla_escolha + self.dissertativas + self.verdadeiro_falso

    @property
    def quantidades(self) -> dict[TipoQuestao, int]:
        return {
            TipoQuestao.MULTIPLA_ESCOLHA: self.multipla_escolha,
            TipoQuestao.DISSERTATIVA: self.dissertativas,
            TipoQuestao.VERDADEIRO_FALSO: self.verdadeiro_falso,
        }


# ---------- Saídas dos agentes (o que o LLM preenche) ----------

_DESCRICAO_TRECHOS = "Números dos trechos do material que sustentam a questão e o gabarito."
# "A) ", "b. ", "C - ", "(D) " no início da alternativa, repetidos ou não.
_PREFIXO_ALTERNATIVA = re.compile(r"^\s*(?:\(?[A-Da-d]\s*[\).:\-]\s*)+")


class Topico(BaseModel):
    titulo: str = Field(description="Nome curto do subtema, com até 8 palavras.")
    descricao: str = Field(
        description="Uma ou duas frases dizendo o que o material ensina sobre o subtema."
    )


class PlanoProva(BaseModel):
    topicos: list[Topico] = Field(
        min_length=1,
        description="Subtemas do material, do mais para o menos importante, sem repetição.",
    )


class QuestaoMultiplaEscolha(BaseModel):
    tipo: Literal["multipla_escolha"] = "multipla_escolha"
    enunciado: str
    alternativas: list[str] = Field(
        min_length=4,
        max_length=4,
        description="Exatamente 4 alternativas, na ordem A, B, C, D, sem a letra no texto.",
    )
    resposta_correta: Literal["A", "B", "C", "D"]
    justificativa: str = Field(
        description="Por que a correta está certa e por que cada uma das outras está errada."
    )
    trechos_usados: list[int] = Field(description=_DESCRICAO_TRECHOS)

    @field_validator("alternativas", mode="before")
    @classmethod
    def _remover_letras(cls, alternativas: object) -> object:
        # Mesmo instruídos, os modelos às vezes escrevem "A) texto"; a letra é da interface.
        if isinstance(alternativas, list):
            return [
                _PREFIXO_ALTERNATIVA.sub("", item) if isinstance(item, str) else item
                for item in alternativas
            ]
        return alternativas

    @field_validator("alternativas")
    @classmethod
    def _alternativas_distintas(cls, alternativas: list[str]) -> list[str]:
        normalizadas = {alternativa.strip().lower() for alternativa in alternativas}
        if len(normalizadas) != len(alternativas):
            raise ValueError("As alternativas devem ser diferentes entre si.")
        return alternativas


class CriterioCorrecao(BaseModel):
    descricao: str = Field(description="O que a resposta precisa conter, sem mencionar pontos.")
    pontos: float = Field(gt=0)


class QuestaoDissertativa(BaseModel):
    tipo: Literal["dissertativa"] = "dissertativa"
    enunciado: str
    resposta_esperada: str = Field(description="Resposta-modelo completa.")
    criterios: list[CriterioCorrecao] = Field(
        min_length=2, description="Critérios de correção cujos pontos somam exatamente 10."
    )
    trechos_usados: list[int] = Field(description=_DESCRICAO_TRECHOS)

    @field_validator("criterios")
    @classmethod
    def _pontos_somam_dez(cls, criterios: list[CriterioCorrecao]) -> list[CriterioCorrecao]:
        soma = sum(criterio.pontos for criterio in criterios)
        if abs(soma - 10) > 0.01:
            raise ValueError(f"Os pontos dos critérios somam {soma:g}, mas devem somar 10.")
        return criterios


class Afirmativa(BaseModel):
    texto: str
    verdadeira: bool
    justificativa: str = Field(description="Por que a afirmativa é verdadeira ou falsa.")


class QuestaoVerdadeiroFalso(BaseModel):
    tipo: Literal["verdadeiro_falso"] = "verdadeiro_falso"
    enunciado: str = Field(description="Instrução curta, como 'Julgue as afirmativas a seguir.'")
    afirmativas: list[Afirmativa] = Field(
        min_length=3, max_length=5, description="De 3 a 5 afirmativas, misturando V e F."
    )
    trechos_usados: list[int] = Field(description=_DESCRICAO_TRECHOS)

    @field_validator("afirmativas")
    @classmethod
    def _mistura_verdadeiras_e_falsas(cls, afirmativas: list[Afirmativa]) -> list[Afirmativa]:
        valores = {afirmativa.verdadeira for afirmativa in afirmativas}
        if valores != {True, False}:
            raise ValueError("Inclua ao menos uma afirmativa verdadeira e uma falsa.")
        return afirmativas


ConteudoQuestao = Annotated[
    QuestaoMultiplaEscolha | QuestaoDissertativa | QuestaoVerdadeiroFalso,
    Field(discriminator="tipo"),
]


class Avaliacao(BaseModel):
    nota: int = Field(ge=0, le=10, description="Qualidade geral da questão, de 0 a 10.")
    fundamentada: bool = Field(
        description="True só se enunciado e gabarito forem sustentados pelos trechos do material."
    )
    adequada_a_dificuldade: bool
    problemas: list[str] = Field(description="Problemas concretos encontrados; vazio se nenhum.")
    sugestoes: str = Field(description="Como corrigir os problemas; vazio se nenhum.")


# ---------- Resultado final ----------


class Fonte(BaseModel):
    ordem: int
    pagina: int | None
    texto: str


class QuestaoGerada(BaseModel):
    numero: int
    topico: str
    dificuldade: Dificuldade
    conteudo: ConteudoQuestao
    fontes: list[Fonte]
    avaliacao: Avaliacao
    aprovada: bool
    tentativas: int


class Prova(BaseModel):
    documento_id: str
    configuracao: ConfiguracaoProva
    topicos: list[Topico]
    questoes: list[QuestaoGerada]
    gerada_em: datetime
    duracao_segundos: float
