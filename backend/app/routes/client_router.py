from fastapi import APIRouter, Depends, Query
from typing import Optional
from uuid import UUID

from app.dependencies import get_user_id, get_db
from app.services.client_service import ClientService
from app.models.client_model import ClientCreate, ClientUpdate

router = APIRouter()


def _service(db=Depends(get_db), user_id: str = Depends(get_user_id)) -> ClientService:
    return ClientService(db, user_id)


@router.get("/")
async def list_clients(
    search: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: ClientService = Depends(_service),
):
    return await service.list_all(search=search, limit=limit, offset=offset)


@router.post("/", status_code=201)
async def create_client(body: ClientCreate, service: ClientService = Depends(_service)):
    return await service.create(body)


@router.get("/{client_id}")
async def get_client(client_id: UUID, service: ClientService = Depends(_service)):
    return await service.get_by_id(client_id)


@router.put("/{client_id}")
async def update_client(client_id: UUID, body: ClientUpdate, service: ClientService = Depends(_service)):
    return await service.update(client_id, body)


@router.get("/{client_id}/summary")
async def get_client_summary(client_id: UUID, service: ClientService = Depends(_service)):
    return await service.get_summary(client_id)


@router.delete("/{client_id}", status_code=204)
async def delete_client(client_id: UUID, service: ClientService = Depends(_service)):
    await service.delete(client_id)
