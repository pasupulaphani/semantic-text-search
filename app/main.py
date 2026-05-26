import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import clients, documents, search

settings = get_settings()
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.seed_on_startup:
        logger.info("seeding database...")
        try:
            from app.seed import seed_database

            await seed_database()
        except Exception as exc:
            logger.warning("seed failed (non-fatal): %s", exc)
    yield


app = FastAPI(
    title="Semantic Document Search API",
    description="Hybrid keyword + semantic search over client documents. Combines PostgreSQL full-text search with pgvector cosine similarity.\n\n",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(clients.router)
app.include_router(documents.router)
app.include_router(search.router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "env": settings.app_env}
