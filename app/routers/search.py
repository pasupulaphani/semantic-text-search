from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import SearchResponse
from app.services.search import unified_search

router = APIRouter(prefix="/search", tags=["Search"])


@router.get(
    "/", response_model=SearchResponse, summary="Unified search — clients and documents"
)
async def search(
    q: str = Query(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query",
        examples=["NevisWealth"],
    ),
    limit: int = Query(10, ge=1, le=100, description="Maximum results per category"),
    use_semantic: bool = Query(
        True, description="Include pgvector semantic search for documents"
    ),
    db: AsyncSession = Depends(get_db),
):
    return await unified_search(db, q, limit=limit, use_semantic=use_semantic)
