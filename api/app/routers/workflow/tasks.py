from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.services.task_workflow_service import TaskWorkflowService
from app.schemas.workflow_requests import (
    TaskBreakdownRequest,
    TaskMergeRequest,
    BulkCreateTasksRequest,
)
from app.schemas.workflow_responses import (
    TaskBreakdownResponse,
    TaskMergeResponse,
    BulkCreateResponse,
)

router = APIRouter()
service = TaskWorkflowService()


@router.post(
    "/breakdown",
    response_model=TaskBreakdownResponse,
    status_code=status.HTTP_200_OK,
)
async def breakdown_task(
    request: TaskBreakdownRequest,
    session: AsyncSession = Depends(get_session),
):
    """タスク分解（1→多）

    親タスクを複数のサブタスクに分解します。
    - **制約**: 子タスクを持つタスクは分割できません（葉ノードのみ分割可能）
    - TimeEntry（作業記録）は estimated_hours の比率で配分されます
    - Schedule（予定）は estimated_hours の比率で配分されます
    - allocated_hours を指定すると手動で配分比率を調整できます
    - 依存関係は自動的に引き継がれます
    - サブタスク間の依存関係は depends_on_indices で指定
    - 元タスクは archive_original=true の場合にアーカイブされます

    Args:
        request: タスク分解リクエスト
        session: Database session

    Returns:
        TaskBreakdownResponse: 分解結果（allocation_summary含む）
    """
    return await service.breakdown_task(
        session,
        task_id=request.task_id,
        subtasks=request.subtasks,
        reason=request.reason,
        archive_original=request.archive_original,
    )


@router.post(
    "/merge",
    response_model=TaskMergeResponse,
    status_code=status.HTTP_200_OK,
)
async def merge_tasks(
    request: TaskMergeRequest,
    session: AsyncSession = Depends(get_session),
):
    """タスク統合（多→1）

    複数のタスクを1つに統合します。
    - TimeEntry と Schedule は自動的に転送されます
    - 依存関係は統合されます（重複排除）
    - 元タスクはアーカイブされます

    Args:
        request: タスク統合リクエスト
        session: Database session

    Returns:
        TaskMergeResponse: 統合結果
    """
    return await service.merge_tasks(
        session,
        task_ids=request.task_ids,
        merged_task=request.merged_task,
        reason=request.reason,
    )


@router.post(
    "/bulk-create",
    response_model=BulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_tasks(
    request: BulkCreateTasksRequest,
    session: AsyncSession = Depends(get_session),
):
    """依存関係付き一括作成

    複数のタスクを依存関係とともに一括作成します。
    - depends_on_indices でタスク間の依存関係を指定
    - 循環依存は自動的に検出されエラーになります

    Args:
        request: 一括作成リクエスト
        session: Database session

    Returns:
        BulkCreateResponse: 作成結果
    """
    return await service.bulk_create_tasks(
        session,
        project_id=request.project_id,
        tasks=request.tasks,
    )
