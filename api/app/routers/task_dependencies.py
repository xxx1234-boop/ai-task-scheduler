from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel

from app.database import get_session
from app.services.task_dependency_service import TaskDependencyService

router = APIRouter()
service = TaskDependencyService()


class AddDependencyRequest(BaseModel):
    """依存関係追加リクエスト"""

    depends_on_task_id: int


@router.get("/{id}/dependencies")
async def get_task_dependencies(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    """タスクの依存関係を取得

    Args:
        id: Task ID
        session: Database session

    Returns:
        {
            "depends_on": [...],  # このタスクが依存するタスク
            "blocking": [...]     # このタスクがブロックするタスク
        }
    """
    return await service.get_dependencies(session, id)


@router.post("/{id}/dependencies", status_code=status.HTTP_201_CREATED)
async def add_task_dependency(
    id: int,
    request: AddDependencyRequest,
    session: AsyncSession = Depends(get_session),
):
    """依存関係を追加

    循環依存は自動的に検出されエラーになります。

    Args:
        id: Task ID
        request: 依存先タスクID
        session: Database session

    Returns:
        成功メッセージ
    """
    await service.add_dependency(
        session,
        task_id=id,
        depends_on_task_id=request.depends_on_task_id,
    )
    return {"message": "Dependency added successfully"}


@router.delete("/{id}/dependencies/{dep_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_task_dependency(
    id: int,
    dep_id: int,
    session: AsyncSession = Depends(get_session),
):
    """依存関係を削除

    Args:
        id: Task ID
        dep_id: 依存先タスクID
        session: Database session

    Returns:
        No Content
    """
    await service.remove_dependency(
        session,
        task_id=id,
        depends_on_task_id=dep_id,
    )
