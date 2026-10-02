# IA Gerador de Provas

Gera provas (múltipla escolha, dissertativas e verdadeiro/falso) com gabarito comentado a
partir do material de aula enviado pelo professor, usando RAG e um pipeline de agentes
(planejador, gerador e revisor).

> Em desenvolvimento. O protótipo original, feito no Google Colab, está em
> [notebooks/](notebooks/).

## Rodando o backend

Requer [uv](https://docs.astral.sh/uv/).

```bash
cd backend
cp .env.example .env        # preencha GROQ_API_KEY
uv sync
uv run uvicorn app.main:app --reload
```

- API: http://localhost:8000/api/v1/health
- Documentação interativa: http://localhost:8000/docs

O primeiro envio de documento baixa o modelo de embeddings (cerca de 240 MB) para
`backend/dados/modelos`. Os envios seguintes usam o modelo em cache.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/v1/documentos` | Envia um `.txt`, `.pdf` ou `.docx`, que é dividido em trechos e indexado |
| `GET` | `/api/v1/documentos` | Lista os documentos enviados |
| `GET` | `/api/v1/documentos/{id}` | Detalhes de um documento |
| `DELETE` | `/api/v1/documentos/{id}` | Remove o documento e seus vetores |
| `POST` | `/api/v1/documentos/{id}/busca` | Busca semântica nos trechos do documento |

## Testes

```bash
cd backend
uv run pytest
uv run ruff check .
```
