import logging
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Client, Document
from app.schemas import (
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    SummaryResponse,
)
# Import embedding/LLM services lazily inside functions to avoid
# importing heavy ML libraries at module import time (speeds up tests).

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/clients/{client_id}/documents", tags=["Documents"])


async def _get_client_or_404(client_id: uuid.UUID, db: AsyncSession) -> Client:
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Client not found."
        )
    return client


async def _get_document_or_404(
    client_id: uuid.UUID, document_id: uuid.UUID, db: AsyncSession
) -> Document:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id, Document.client_id == client_id
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        )
    return doc


@router.post(
    "/",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
    responses={404: {"description": "Client not found"}},
)
async def create_document(
    client_id: uuid.UUID,
    payload: DocumentCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, db)
    doc = Document(client_id=client_id, **payload.model_dump())
    db.add(doc)
    await db.flush()
    background_tasks.add_task(_generate_and_save_embedding, doc.id, payload.content)
    await db.refresh(doc)
    return doc


@router.get(
    "/",
    response_model=list[DocumentResponse],
    summary="List client documents",
    responses={404: {"description": "Client not found"}},
)
async def list_documents(
    client_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, db)
    result = await db.execute(
        select(Document)
        .where(Document.client_id == client_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get a document",
    responses={404: {"description": "Client or document not found"}},
)
async def get_document(
    client_id: uuid.UUID, document_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    return await _get_document_or_404(client_id, document_id, db)


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Update a document",
    responses={404: {"description": "Client or document not found"}},
)
async def update_document(
    client_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_document_or_404(client_id, document_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doc, field, value)
    if "content" in update_data:
        background_tasks.add_task(
            _generate_and_save_embedding, doc.id, update_data["content"]
        )
    await db.flush()
    await db.refresh(doc)
    return doc


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    responses={404: {"description": "Client or document not found"}},
)
async def delete_document(
    client_id: uuid.UUID, document_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    doc = await _get_document_or_404(client_id, document_id, db)
    await db.delete(doc)


@router.post(
    "/{document_id}/summarise",
    response_model=SummaryResponse,
    summary="Summarise a document (LLM)",
    responses={404: {"description": "Client or document not found"}},
)
async def summarise(
    client_id: uuid.UUID, document_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    doc = await _get_document_or_404(client_id, document_id, db)
    if not doc.summary:
        from app.services.llm import summarise_document

        doc.summary = await summarise_document(doc.title, doc.content)
        await db.flush()
    return SummaryResponse(document_id=doc.id, summary=doc.summary)


async def _generate_and_save_embedding(document_id: uuid.UUID, content: str) -> None:
    from app.database import AsyncSessionLocal

    try:
        from app.services.embedding import embed_text

        embedding = await embed_text(content)
        async with AsyncSessionLocal() as session:
            doc = await session.get(Document, document_id)
            if doc:
                doc.embedding = embedding
                await session.commit()
    except Exception as exc:
        logger.error(
            "Failed to generate embedding for document %s: %s", document_id, exc
        )
