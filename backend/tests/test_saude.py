from fastapi.testclient import TestClient

from app.core.config import Configuracoes, obter_configuracoes
from app.main import app


def consultar_saude(**configuracoes):
    app.dependency_overrides[obter_configuracoes] = lambda: Configuracoes(
        _env_file=None, **configuracoes
    )
    try:
        return TestClient(app).get("/api/v1/health")
    finally:
        app.dependency_overrides.clear()


def test_saude_informa_chave_ausente():
    resposta = consultar_saude(groq_api_key=None)

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"
    assert resposta.json()["llm_configurado"] is False


def test_saude_informa_chave_configurada_sem_vazar_o_valor():
    resposta = consultar_saude(groq_api_key="segredo")

    assert resposta.json()["llm_configurado"] is True
    assert "segredo" not in resposta.text
