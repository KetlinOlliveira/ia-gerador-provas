from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Configuracoes(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    nome_app: str = "IA Gerador de Provas"
    prefixo_api: str = "/api/v1"
    nivel_log: str = "INFO"
    origens_cors: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    # Opcional para a aplicação subir (e os testes rodarem) sem chave; o cliente
    # LLM levanta um erro claro na primeira vez em que ela for realmente necessária.
    groq_api_key: SecretStr | None = None

    modelo_planejador: str = "llama-3.1-8b-instant"
    modelo_gerador: str = "llama-3.1-8b-instant"
    modelo_revisor: str = "llama-3.1-8b-instant"

    llm_max_retentativas: int = Field(default=4, ge=0)
    llm_max_tentativas_validacao: int = Field(default=3, ge=1)
    llm_max_concorrencia: int = Field(default=4, ge=1)
    llm_timeout_segundos: float = Field(default=60, gt=0)

    @field_validator("origens_cors", mode="before")
    @classmethod
    def _separar_origens(cls, valor: object) -> object:
        if isinstance(valor, str):
            return [origem.strip() for origem in valor.split(",") if origem.strip()]
        return valor


@lru_cache
def obter_configuracoes() -> Configuracoes:
    return Configuracoes()
