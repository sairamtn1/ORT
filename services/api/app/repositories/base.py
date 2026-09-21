from collections.abc import Sequence
from typing import Generic, TypeVar
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    def __init__(self, model: type[ModelT], db: AsyncSession):
        self.model = model
        self.db = db

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        result = await self.db.scalars(
            select(self.model).order_by(self.model.created_at.desc()).limit(limit).offset(offset)
        )
        return result.all()

    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return await self.db.get(self.model, entity_id)

    async def create(self, values: dict) -> ModelT:
        entity = self.model(**values)
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def update(self, entity: ModelT, values: dict) -> ModelT:
        for key, value in values.items():
            setattr(entity, key, value)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.db.delete(entity)
        await self.db.commit()
