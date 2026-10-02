# syntax=docker/dockerfile:1

# ---------- base: dependências de produção e modelo de embeddings ----------
FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # O ambiente virtual fica fora de /app para não ser escondido quando o código
    # é montado como volume no desenvolvimento.
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH" \
    DIRETORIO_MODELOS=/opt/modelos

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# O modelo é baixado na construção da imagem: o primeiro envio de documento
# não espera download, e o container funciona sem acesso ao Hugging Face.
ARG MODELO_EMBEDDINGS=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('${MODELO_EMBEDDINGS}', cache_dir='/opt/modelos')"

EXPOSE 8000

# ---------- desenvolvimento: + pytest/ruff, código montado via volume ----------
FROM base AS desenvolvimento

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]

# ---------- producao: código copiado para dentro da imagem ----------
FROM base AS producao

COPY . .
RUN useradd --create-home --uid 1000 app && chown -R app /app
USER app

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
