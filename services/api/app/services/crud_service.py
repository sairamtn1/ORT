import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories import Repository


class CRUDService:
    def __init__(self, model: type, db: AsyncSession):
        self.repository = Repository(model, db)

    async def list(self, limit: int, offset: int):
        return await self.repository.list(limit=limit, offset=offset)

    async def get_or_404(self, entity_id: uuid.UUID):
        entity = await self.repository.get(entity_id)
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.repository.model.__name__} not found",
            )
        return entity

    async def create(self, values: dict[str, Any]):
        return await self.repository.create(values)

    async def update(self, entity_id: uuid.UUID, values: dict[str, Any]):
        entity = await self.get_or_404(entity_id)
        return await self.repository.update(entity, values)

    async def delete(self, entity_id: uuid.UUID):
        entity = await self.get_or_404(entity_id)
        await self.repository.delete(entity)