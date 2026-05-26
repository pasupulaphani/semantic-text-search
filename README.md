# Semantic Document Search API

A production-ready FastAPI service for managing client documents with **hybrid search** — combining PostgreSQL full-text search (`tsvector`/`ILIKE`) with **pgvector** semantic similarity on OpenAI embeddings.

The key insight: keyword search alone cannot match `"address proof"` to a document titled `"utility bill"`. Semantic search bridges that gap by understanding meaning, not just tokens.

---
---

## Architecture Notes

### Hybrid search scoring

Results from both passes are merged and ranked by:

```
combined_score = (keyword_weight × keyword_score) + (semantic_weight × semantic_score)
```

Default weights: `keyword=0.4`, `semantic=0.6`. Tunable via env vars `KEYWORD_WEIGHT` / `SEMANTIC_WEIGHT`.

### tsvector trigger

The `search_vector` column is auto-populated by a Postgres trigger on `INSERT`/`UPDATE`, so no application-level maintenance is needed.

### Embedding pipeline

1. Document is created → response returned immediately (201)
2. Background task calls `text-embedding-3-small` (1536 dims)
3. Vector stored in `documents.embedding`
4. Available for semantic search within ~1 second


## Setup

### Prerequisites

- Docker & Docker Compose
- An OpenAI API key (for summarisation); fallback to local model

### 1. Clone and configure

```bash
git clone <repo-url>
cd semantic_text_search
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...
```

### 2. Start services

```bash
docker-compose up --build
```

This starts:
- **postgres** on `localhost:5432` (pgvector-enabled)
- **api** on `localhost:8000` with hot-reload

### 3. Run migrations

```bash
docker-compose exec api alembic upgrade head
```

### 4. Open Swagger UI

Visit [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Running Tests

Tests use an in-memory SQLite database — no Docker required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```


## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async DB connection string |
| `OPENAI_API_KEY` | — | Required for semantic search |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | Summarisation model |
| `KEYWORD_WEIGHT` | `0.4` | Weight for keyword score |
| `SEMANTIC_WEIGHT` | `0.6` | Weight for semantic score |
| `LOG_LEVEL` | `INFO` | Logging level |
