import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Client
from app.schemas import ClientCreate, ClientResponse, ClientUpdate

router = APIRouter(prefix="/clients", tags=["Clients"])


async def _get_or_404(client_id: uuid.UUID, db: AsyncSession) -> Client:
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Client not found."
        )
    return client


@router.post(
    "/",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a client",
    responses={409: {"description": "Email already registered"}},
)
async def create_client(payload: ClientCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Client).where(Client.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A client with email '{payload .email }' already exists.",
        )
    client = Client(**payload.model_dump())
    db.add(client)
    await db.flush()
    await db.refresh(client)
    return client


@router.get("/", response_model=list[ClientResponse], summary="List clients")
async def list_clients(
    skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Client).offset(skip).limit(limit))
    return result.scalars().all()


@router.get(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Get a client",
    responses={404: {"description": "Client not found"}},
)
async def get_client(client_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await _get_or_404(client_id, db)


@router.patch(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Update a client",
    responses={404: {"description": "Client not found"}},
)
async def update_client(
    client_id: uuid.UUID, payload: ClientUpdate, db: AsyncSession = Depends(get_db)
):
    client = await _get_or_404(client_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    await db.flush()
    await db.refresh(client)
    return client


@router.delete(
    "/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a client",
    responses={404: {"description": "Client not found"}},
)
async def delete_client(client_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    client = await _get_or_404(client_id, db)
    await db.delete(client)
