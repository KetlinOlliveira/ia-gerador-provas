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

## Testes

```bash
cd backend
uv run pytest
uv run ruff check .
```
