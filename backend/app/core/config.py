from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

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

    modelo_planejador: str = "openai/gpt-oss-20b"
    modelo_gerador: str = "openai/gpt-oss-20b"
    modelo_revisor: str = "openai/gpt-oss-120b"

    # O plano gratuito da Groq limita tokens por minuto: as retentativas esperam o
    # `retry-after` do 429, e a concorrência baixa evita estourar o limite à toa.
    llm_max_retentativas: int = Field(default=8, ge=0)
    llm_max_tentativas_validacao: int = Field(default=3, ge=1)
    llm_max_concorrencia: int = Field(default=2, ge=1)
    llm_timeout_segundos: float = Field(default=90, gt=0)
    # Saída estrita: o provedor restringe a decodificação ao JSON Schema. Desligue
    # para modelos que só aceitam o modo JSON simples.
    llm_saida_estrita: bool = True
    # Só se aplica aos modelos de raciocínio (gpt-oss). "low" gasta menos tokens.
    llm_esforco_raciocinio: Literal["low", "medium", "high"] = "low"

    # Agentes
    nota_minima_revisao: int = Field(default=7, ge=0, le=10)
    max_tentativas_por_questao: int = Field(default=2, ge=1)
    trechos_por_topico: int = Field(default=5, ge=1)
    # Quanto do documento o planejador lê para extrair os tópicos.
    max_caracteres_planejador: int = Field(default=12000, ge=1000)

    # O padrão aponta para o Postgres do docker compose visto do host; dentro do
    # compose o serviço do backend sobrescreve com o host `db`.
    url_banco: str = "postgresql+psycopg://provas:provas@localhost:5442/provas"
    tamanho_max_upload_mb: int = Field(default=20, ge=1)

    modelo_embeddings: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    # Na imagem Docker o modelo já vem baixado neste diretório.
    diretorio_modelos: Path = Path("dados/modelos")
    # Usa só o modelo em cache, sem consultar o Hugging Face. Sem isso o fastembed vai
    # à rede a cada carga e, no container, levava minutos para começar. A imagem Docker
    # liga esta opção, porque o modelo vem baixado nela.
    embeddings_somente_local: bool = False
    # Em caracteres. Trechos curtos tratam de um assunto só, e o vetor de um modelo
    # pequeno como este fica mais preciso: com 1000 caracteres a busca misturava temas.
    tamanho_trecho: int = Field(default=400, ge=200)
    sobreposicao_trecho: int = Field(default=80, ge=0)

    @field_validator("origens_cors", mode="before")
    @classmethod
    def _separar_origens(cls, valor: object) -> object:
        if isinstance(valor, str):
            return [origem.strip() for origem in valor.split(",") if origem.strip()]
        return valor


@lru_cache
def obter_configuracoes() -> Configuracoes:
    return Configuracoes()
