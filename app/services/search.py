import logging
import uuid
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.models import Client, Document
from app.schemas import (
    ClientResponse,
    ClientSearchResult,
    DocumentResponse,
    SearchResponse,
    SearchResult,
)


logger = logging.getLogger(__name__)
settings = get_settings()


async def unified_search(
    db: AsyncSession, query: str, *, limit: int = 10, use_semantic: bool = True
) -> SearchResponse:
    client_hits = await _client_search(db, query, limit=limit)
    doc_hits = await _document_search(db, query, limit=limit, use_semantic=use_semantic)
    total = len(client_hits) + len(doc_hits)
    return SearchResponse(
        query=query, total=total, items=client_hits + doc_hits
    )


async def _client_search(
    db: AsyncSession, query: str, *, limit: int
) -> list[ClientSearchResult]:
    pattern = f"%{query }%"
    stmt = (
        select(Client)
        .where(
            or_(
                Client.first_name.ilike(pattern),
                Client.last_name.ilike(pattern),
                Client.email.ilike(pattern),
                Client.description.ilike(pattern),
            )
        )
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    results: list[ClientSearchResult] = []
    for client in rows:
        score = 1.0
        q_lower = query.lower()
        if q_lower in (client.email or "").lower():
            score = 1.0
        elif (
            q_lower in (client.first_name or "").lower()
            or q_lower in (client.last_name or "").lower()
        ):
            score = 1.0
        elif q_lower in (client.description or "").lower():
            score = 0.7
        results.append(
            ClientSearchResult(
                client=ClientResponse.model_validate(client), score=round(score, 4)
            )
        )
    results.sort(key=lambda r: r.score, reverse=True)
    return results


async def _document_search(
    db: AsyncSession, query: str, *, limit: int, use_semantic: bool
) -> list[SearchResult]:
    keyword_results = await _keyword_search(db, query, limit=limit * 2)
    semantic_scores: dict[uuid.UUID, float] = {}
    if use_semantic:
        try:
            semantic_scores = await _semantic_search(db, query, limit=limit * 2)
        except Exception as exc:
            logger.warning("Semantic search failed, using keyword only: %s", exc)
    all_docs: dict[uuid.UUID, Document] = {doc.id: doc for doc, _ in keyword_results}
    keyword_scores: dict[uuid.UUID, float] = {
        doc.id: score for doc, score in keyword_results
    }
    semantic_only = set(semantic_scores) - set(all_docs)
    if semantic_only:
        rows = (
            await db.execute(select(Document).where(Document.id.in_(semantic_only)))
        ).scalars()
        for doc in rows:
            all_docs[doc.id] = doc
    max_kw = max(keyword_scores.values(), default=1.0) or 1.0
    results: list[SearchResult] = []
    for doc_id, doc in all_docs.items():
        kw = keyword_scores.get(doc_id, 0.0) / max_kw
        sem = semantic_scores.get(doc_id, 0.0)
        combined = (
            settings.keyword_weight * kw + settings.semantic_weight * sem
            if use_semantic and semantic_scores
            else kw
        )
        results.append(
            SearchResult(
                document=DocumentResponse.model_validate(doc),
                keyword_score=round(kw, 4),
                semantic_score=round(sem, 4),
                combined_score=round(combined, 4),
            )
        )
    results.sort(key=lambda r: r.combined_score, reverse=True)
    return results[:limit]


async def _keyword_search(
    db: AsyncSession, query: str, *, limit: int
) -> list[tuple[Document, float]]:
    results: list[tuple[Document, float]] = []
    try:
        ts_query = func.plainto_tsquery("english", query)
        ts_rank = func.ts_rank(Document.search_vector, ts_query)
        stmt = (
            select(Document, ts_rank.label("rank"))
            .where(Document.search_vector.op("@@")(ts_query))
            .order_by(ts_rank.desc())
            .limit(limit)
        )
        results = [(row[0], float(row[1])) for row in (await db.execute(stmt)).all()]
    except Exception as exc:
        logger.debug("tsvector unavailable (%s), using ILIKE only", exc)
    found_ids = {doc.id for doc, _ in results}
    pattern = f"%{query }%"
    ilike_stmt = (
        select(Document)
        .where(
            or_(Document.title.ilike(pattern), Document.content.ilike(pattern)),
            Document.id.not_in(found_ids) if found_ids else text("TRUE"),
        )
        .limit(limit)
    )
    for doc in (await db.execute(ilike_stmt)).scalars().all():
        results.append((doc, 0.1))
    return results


async def _semantic_search(
    db: AsyncSession, query: str, *, limit: int
) -> dict[uuid.UUID, float]:
    from app.services.embedding import embed_text

    query_embedding = await embed_text(query)
    distance = Document.embedding.op("<=>")(query_embedding)
    similarity = (1 - distance).label("similarity")
    stmt = (
        select(Document.id, similarity)
        .where(Document.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    )
    return {row[0]: float(row[1]) for row in (await db.execute(stmt)).all()}
