"""
patterns.py — Patrones de referencia para el agente backend-fastapi.
Este archivo NO se ejecuta directamente. Es una referencia para que el agente
genere código consistente con la arquitectura del proyecto.
"""

# ─── MODEL PATTERN ──────────────────────────────────────────────────────────
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FeatureCreate(BaseModel):
    """Schema para crear un nuevo recurso."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class FeatureResponse(BaseModel):
    """Schema de respuesta público (nunca exponer campos internos de MongoDB)."""
    uid: str
    name: str
    description: Optional[str] = None
    created_at: datetime


# ─── REPOSITORY PATTERN ─────────────────────────────────────────────────────
class FeatureRepository:
    """Única clase que toca la colección MongoDB."""

    COLLECTION_NAME = "features"

    def __init__(self, db):
        self.collection = db[self.COLLECTION_NAME]

    async def create(self, data: dict) -> dict:
        result = await self.collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return data

    async def find_by_uid(self, uid: str) -> Optional[dict]:
        return await self.collection.find_one({"uid": uid})

    async def upsert_by_uid(self, uid: str, data: dict) -> dict:
        await self.collection.update_one(
            {"uid": uid},
            {"$set": data},
            upsert=True,
        )
        return await self.find_by_uid(uid)

    async def delete_by_uid(self, uid: str) -> bool:
        result = await self.collection.delete_one({"uid": uid})
        return result.deleted_count > 0


# ─── SERVICE PATTERN ────────────────────────────────────────────────────────
class FeatureService:
    """Lógica de negocio pura. Recibe repository por constructor (DI manual)."""

    def __init__(self, repo: FeatureRepository):
        self.repo = repo

    async def create(self, data: FeatureCreate, uid: str) -> dict:
        document = data.model_dump()
        document["uid"] = uid
        document["created_at"] = datetime.utcnow().isoformat()
        return await self.repo.create(document)

    async def get_by_uid(self, uid: str) -> Optional[dict]:
        result = await self.repo.find_by_uid(uid)
        if not result:
            raise ValueError(f"Feature not found for uid: {uid}")
        return result


# ─── ROUTER PATTERN ─────────────────────────────────────────────────────────
from fastapi import APIRouter, Header, HTTPException, status
from app.config.database import get_db

router = APIRouter(prefix="/feature", tags=["feature"])


@router.post("/", response_model=FeatureResponse, status_code=status.HTTP_201_CREATED)
async def create_feature(data: FeatureCreate, authorization: str = Header(...)):
    # Wiring: siempre en el router, nunca en el service
    db = get_db()
    repo = FeatureRepository(db)
    service = FeatureService(repo)

    # Verificar token (ejemplo con firebase_service)
    # from app.services.firebase_service import verify_token
    # uid = verify_token(authorization.replace("Bearer ", ""))

    try:
        result = await service.create(data, uid="extracted-uid")
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{uid}", response_model=FeatureResponse)
async def get_feature(uid: str):
    db = get_db()
    repo = FeatureRepository(db)
    service = FeatureService(repo)
    try:
        return await service.get_by_uid(uid)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
