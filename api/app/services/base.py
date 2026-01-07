from typing import Generic, TypeVar, Type, Optional, List, Any

from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundException

ModelType = TypeVar("ModelType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseCRUDService(Generic[ModelType, UpdateSchemaType]):
    """Base class for CRUD operations on SQLModel models."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get_by_id(
        self,
        session: AsyncSession,
        id: int,
        relationships: Optional[List[str]] = None,
    ) -> ModelType:
        """Get a single record by ID with optional relationship loading.

        Args:
            session: Database session
            id: Record ID
            relationships: List of relationship attribute names to eager load

        Returns:
            Model instance

        Raises:
            NotFoundException: If record not found
        """
        query = select(self.model).where(self.model.id == id)

        # Eager load relationships if specified
        if relationships:
            for rel in relationships:
                query = query.options(selectinload(getattr(self.model, rel)))

        result = await session.execute(query)
        item = result.scalar_one_or_none()

        if not item:
            raise NotFoundException(f"{self.model.__name__} with id {id} not found")

        return item

    async def get_all(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[dict] = None,
        order_by: Optional[str] = None,
        relationships: Optional[List[str]] = None,
    ) -> tuple[List[ModelType], int]:
        """Get all records with pagination, filtering, and sorting.

        Args:
            session: Database session
            skip: Number of records to skip
            limit: Number of records to return
            filters: Dictionary of field names and values to filter by
            order_by: Field name to sort by (prefix with - for descending)
            relationships: List of relationship attribute names to eager load

        Returns:
            Tuple of (items list, total count)
        """
        # Base query
        query = select(self.model)

        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)

        # Get total count (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        # Apply sorting
        if order_by:
            desc = order_by.startswith("-")
            field = order_by.lstrip("-")
            if hasattr(self.model, field):
                order_col = getattr(self.model, field)
                query = query.order_by(order_col.desc() if desc else order_col)

        # Eager load relationships
        if relationships:
            for rel in relationships:
                if hasattr(self.model, rel):
                    query = query.options(selectinload(getattr(self.model, rel)))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await session.execute(query)
        items = result.scalars().all()

        return items, total

    async def create(
        self,
        session: AsyncSession,
        obj_in: ModelType,
    ) -> ModelType:
        """Create a new record.

        Args:
            session: Database session
            obj_in: Model instance to create

        Returns:
            Created model instance
        """
        session.add(obj_in)
        await session.commit()
        await session.refresh(obj_in)
        return obj_in

    async def update(
        self,
        session: AsyncSession,
        id: int,
        obj_in: UpdateSchemaType,
    ) -> ModelType:
        """Update an existing record with partial data.

        Args:
            session: Database session
            id: Record ID
            obj_in: Update schema with partial data

        Returns:
            Updated model instance

        Raises:
            NotFoundException: If record not found
        """
        db_obj = await self.get_by_id(session, id)

        # Update fields that are set (not None)
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def delete(
        self,
        session: AsyncSession,
        id: int,
    ) -> None:
        """Delete a record by ID.

        Args:
            session: Database session
            id: Record ID

        Raises:
            NotFoundException: If record not found
        """
        db_obj = await self.get_by_id(session, id)
        await session.delete(db_obj)
        await session.commit()
