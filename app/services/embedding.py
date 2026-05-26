import asyncio
import logging
from functools import lru_cache
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
LOCAL_MODEL_NAME = "all-MiniLM-L6-v2"
LOCAL_EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def _get_local_model():
    from sentence_transformers import SentenceTransformer

    logger.info("Loading local embedding model '%s'…", LOCAL_MODEL_NAME)
    model = SentenceTransformer(LOCAL_MODEL_NAME, device="cpu")
    model.encode("warmup", convert_to_numpy=True)
    logger.info("Local embedding model ready.")
    return model


def _use_openai() -> bool:
    return bool(settings.openai_api_key)


async def embed_text(text: str) -> list[float]:
    if _use_openai():
        return await _embed_openai(text)
    return await _embed_local(text)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if _use_openai():
        return await _embed_openai_batch(texts)
    return await _embed_local_batch(texts)


async def _embed_local(text: str) -> list[float]:
    loop = asyncio.get_event_loop()
    embedding = await loop.run_in_executor(
        None, lambda: _get_local_model().encode(text.replace("\n", " ")).tolist()
    )
    return embedding


async def _embed_local_batch(texts: list[str]) -> list[list[float]]:
    loop = asyncio.get_event_loop()
    cleaned = [t.replace("\n", " ") for t in texts]
    embeddings = await loop.run_in_executor(
        None, lambda: _get_local_model().encode(cleaned).tolist()
    )
    return embeddings


async def _embed_openai(text: str) -> list[float]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.embeddings.create(
        model=settings.openai_embedding_model, input=text.replace("\n", " ")
    )
    return response.data[0].embedding


async def _embed_openai_batch(texts: list[str]) -> list[list[float]]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=[t.replace("\n", " ") for t in texts],
    )
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
