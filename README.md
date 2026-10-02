# IA Gerador de Provas

Gera provas (múltipla escolha, dissertativas e verdadeiro/falso) com gabarito comentado a
partir do material de aula enviado pelo professor, usando RAG e um pipeline de agentes
(planejador, gerador e revisor).

> Em desenvolvimento. O protótipo original, feito no Google Colab, está em
> [notebooks/](notebooks/).

## Arquitetura

```
docker compose
├── db       Postgres 16 + pgvector: documentos, trechos e seus embeddings
└── backend  FastAPI: ingestão, embeddings locais (fastembed), busca e agentes LLM (Groq)
```

Documentos e vetores ficam no mesmo banco, então são gravados na mesma transação e a busca
semântica é uma consulta SQL comum, ordenada pela distância de cosseno do pgvector.

## Rodando com Docker

Requer Docker com o Compose.

```bash
cp backend/.env.example backend/.env    # preencha GROQ_API_KEY
docker compose up --build
```

- API: http://localhost:8010/api/v1/health
- Documentação interativa: http://localhost:8010/docs
- Postgres: `localhost:5442` (usuário, senha e banco: `provas`)

As migrações do banco rodam automaticamente quando o backend sobe. O código do backend é
montado no container, então alterações recarregam a API sem reconstruir a imagem.

As portas do host podem ser trocadas com as variáveis `PORTA_API` e `PORTA_BANCO`, por
exemplo em um arquivo `.env` na raiz do projeto.

## Rodando o backend fora do Docker

Útil para depurar. Requer [uv](https://docs.astral.sh/uv/) e o banco do compose no ar.

```bash
docker compose up -d db
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Fora do Docker, o primeiro envio de documento baixa o modelo de embeddings (cerca de
240 MB) para `backend/dados/modelos`.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/v1/documentos` | Envia um `.txt`, `.pdf` ou `.docx`, que é dividido em trechos e indexado |
| `GET` | `/api/v1/documentos` | Lista os documentos enviados |
| `GET` | `/api/v1/documentos/{id}` | Detalhes de um documento |
| `DELETE` | `/api/v1/documentos/{id}` | Remove o documento e seus trechos |
| `POST` | `/api/v1/documentos/{id}/busca` | Busca semântica nos trechos do documento |

## Testes

Os testes de API rodam contra um Postgres real, num banco separado (`provas_testes`) que é
criado e migrado automaticamente.

```bash
# dentro do container
docker compose exec backend pytest

# ou no host, com o banco do compose no ar
cd backend
uv run pytest
uv run ruff check .
```

## Migrações

```bash
cd backend
uv run alembic revision -m "descricao da mudanca"   # cria uma migração nova
uv run alembic upgrade head                          # aplica as pendentes
```
