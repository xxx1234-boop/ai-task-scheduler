from decimal import Decimal
from typing import List, Optional

from sqlmodel import select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Task, TimeEntry, Schedule
from app.exceptions import NotFoundException, ValidationException
from app.schemas.workflow_requests import SubtaskInput, TaskInput
from app.schemas.workflow_responses import (
    TaskBreakdownResponse,
    TaskMergeResponse,
    BulkCreateResponse,
    TaskSummary,
)
from app.services.task_dependency_service import TaskDependencyService


class TaskWorkflowService:
    """タスクワークフロー操作サービス"""

    def __init__(self):
        self.dep_service = TaskDependencyService()

    async def breakdown_task(
        self,
        session: AsyncSession,
        task_id: int,
        subtasks: List[SubtaskInput],
        reason: Optional[str],
        archive_original: bool,
    ) -> TaskBreakdownResponse:
        """タスク分解（1→多）

        処理フロー:
        1. 元タスク検証（存在確認、status != 'archive'）
        2. サブタスク作成（parent_task_id設定、decomposition_level+1）
        3. 依存関係の引継ぎ
        4. サブタスク間依存関係構築
        5. 元タスクarchive（archive_original=trueの場合）
        6. トランザクションコミット

        Args:
            session: Database session
            task_id: 元タスクID
            subtasks: サブタスク情報リスト
            reason: 分解理由（オプション）
            archive_original: 元タスクをアーカイブするか

        Returns:
            TaskBreakdownResponse (history_id=None固定)

        Raises:
            NotFoundException: タスクが存在しない
            ValidationException: タスクが既にアーカイブ済み
        """
        # 1. 元タスク検証
        original = await self._validate_task_exists(session, task_id)
        await self._validate_task_not_archived(original)

        # サブタスクが空でないことを確認
        if not subtasks:
            raise ValidationException("At least one subtask is required")

        # 2. サブタスク作成
        created = await self._create_subtasks(session, original, subtasks)
        session.add_all(created)
        await session.flush()  # IDを取得するためにflush

        created_ids = [task.id for task in created]

        # 3. 依存関係の引継ぎ
        dependencies_transferred = 0
        if original.id:
            # 元タスクの依存関係を最後のサブタスクへ転送
            dependencies_transferred = await self.dep_service.transfer_dependencies(
                session,
                from_task_id=original.id,
                to_task_ids=created_ids,
                mode="to_last",  # outgoing依存は最後のサブタスクへ
            )

        # 4. サブタスク間依存関係構築（depends_on_indicesに基づく）
        for i, subtask_input in enumerate(subtasks):
            if subtask_input.depends_on_indices:
                for dep_index in subtask_input.depends_on_indices:
                    # インデックスの範囲チェック
                    if dep_index < 0 or dep_index >= len(created):
                        raise ValidationException(
                            f"Invalid depends_on_indices: {dep_index} is out of range"
                        )

                    # 循環チェック
                    await self.dep_service.check_cycle(
                        session,
                        task_id=created_ids[i],
                        new_depends_on_ids=[created_ids[dep_index]],
                    )

                    # 依存関係追加
                    await self.dep_service.add_dependency(
                        session,
                        task_id=created_ids[i],
                        depends_on_task_id=created_ids[dep_index],
                    )
                    dependencies_transferred += 1

        # 5. 元タスクアーカイブ
        if archive_original:
            original.status = "archive"
            session.add(original)

        # 6. コミット
        await session.commit()

        # リフレッシュ
        for task in created:
            await session.refresh(task)
        await session.refresh(original)

        return TaskBreakdownResponse(
            original_task=TaskSummary(
                id=original.id,
                name=original.name,
                status=original.status,
            ),
            created_tasks=[
                TaskSummary(id=t.id, name=t.name, status=t.status) for t in created
            ],
            dependencies_transferred=dependencies_transferred,
            history_id=None,  # 後回し
        )

    async def merge_tasks(
        self,
        session: AsyncSession,
        task_ids: List[int],
        merged_task: TaskInput,
        reason: Optional[str],
    ) -> TaskMergeResponse:
        """タスク統合（多→1）

        処理フロー:
        1. マージ元タスク検証（2つ以上、全て存在、同一project_id）
        2. 新規タスク作成（merged_taskの仕様）
        3. actual_hours合算
        4. TimeEntry転送
        5. Schedule転送
        6. 依存関係統合
        7. マージ元タスクarchive
        8. トランザクションコミット

        Args:
            session: Database session
            task_ids: マージ元タスクIDリスト
            merged_task: マージ後タスク情報
            reason: マージ理由（オプション）

        Returns:
            TaskMergeResponse (history_id=None固定)

        Raises:
            NotFoundException: タスクが存在しない
            ValidationException: タスクが2つ未満、またはproject_id不一致
        """
        # 1. マージ元タスク検証
        if len(task_ids) < 2:
            raise ValidationException("At least 2 tasks are required for merging")

        # タスク存在確認
        tasks = []
        for task_id in task_ids:
            task = await self._validate_task_exists(session, task_id)
            tasks.append(task)

        # 同一プロジェクト確認
        await self._validate_same_project(tasks)

        # 2. 新規タスク作成
        project_id = tasks[0].project_id  # すべて同じproject_id
        new_task = Task(
            name=merged_task.name,
            project_id=project_id,
            genre_id=merged_task.genre_id,
            estimated_hours=merged_task.estimated_hours,
            priority=merged_task.priority,
            want_level=merged_task.want_level,
            deadline=merged_task.deadline,
            status="todo",
        )

        # 3. actual_hours合算
        total_actual_hours = await self._calculate_total_actual_hours(tasks)
        new_task.actual_hours = total_actual_hours

        session.add(new_task)
        await session.flush()  # IDを取得

        # 4. TimeEntry転送
        time_entries_transferred = await self._transfer_time_entries(
            session, task_ids, new_task.id
        )

        # 5. Schedule転送
        await self._transfer_schedules(session, task_ids, new_task.id)

        # 6. 依存関係統合
        dependencies_count = await self.dep_service.merge_dependencies(
            session, task_ids, new_task.id
        )

        # 7. マージ元タスクarchive
        for task in tasks:
            task.status = "archive"
            session.add(task)

        # 8. コミット
        await session.commit()

        # リフレッシュ
        await session.refresh(new_task)

        return TaskMergeResponse(
            merged_task=TaskSummary(
                id=new_task.id,
                name=new_task.name,
                status=new_task.status,
            ),
            archived_tasks=task_ids,
            time_entries_transferred=time_entries_transferred,
            history_id=None,  # 後回し
        )

    async def bulk_create_tasks(
        self,
        session: AsyncSession,
        project_id: Optional[int],
        tasks: List[TaskInput],
    ) -> BulkCreateResponse:
        """依存関係付き一括作成

        処理フロー:
        1. タスク一括作成（project_id共通設定）
        2. depends_on_indicesをタスクIDに変換
        3. 各依存関係に対して循環チェック
        4. 依存関係一括挿入
        5. トランザクションコミット

        Args:
            session: Database session
            project_id: プロジェクトID（オプション）
            tasks: タスク情報リスト

        Returns:
            BulkCreateResponse

        Raises:
            ValidationException: タスクが空、または循環依存
        """
        # タスクが空でないことを確認
        if not tasks:
            raise ValidationException("At least one task is required")

        # 1. タスク一括作成
        created_tasks = []
        for task_input in tasks:
            new_task = Task(
                name=task_input.name,
                project_id=project_id,
                genre_id=task_input.genre_id,
                estimated_hours=task_input.estimated_hours,
                priority=task_input.priority,
                want_level=task_input.want_level,
                deadline=task_input.deadline,
                status="todo",
            )
            session.add(new_task)
            created_tasks.append(new_task)

        await session.flush()  # IDを取得

        created_ids = [task.id for task in created_tasks]

        # 2-3. depends_on_indicesをタスクIDに変換して依存関係追加
        dependencies_created = 0

        for i, task_input in enumerate(tasks):
            if task_input.depends_on_indices:
                for dep_index in task_input.depends_on_indices:
                    # インデックスの範囲チェック
                    if dep_index < 0 or dep_index >= len(created_tasks):
                        raise ValidationException(
                            f"Invalid depends_on_indices: {dep_index} is out of range"
                        )

                    # 自己参照チェック
                    if dep_index == i:
                        raise ValidationException("Task cannot depend on itself")

                    # 循環チェック
                    await self.dep_service.check_cycle(
                        session,
                        task_id=created_ids[i],
                        new_depends_on_ids=[created_ids[dep_index]],
                    )

                    # 依存関係追加
                    await self.dep_service.add_dependency(
                        session,
                        task_id=created_ids[i],
                        depends_on_task_id=created_ids[dep_index],
                    )
                    dependencies_created += 1

        # 5. コミット
        await session.commit()

        # リフレッシュ
        for task in created_tasks:
            await session.refresh(task)

        return BulkCreateResponse(
            created_tasks=[
                TaskSummary(id=t.id, name=t.name, status=t.status)
                for t in created_tasks
            ],
            dependencies_created=dependencies_created,
        )

    # ===== Private Methods =====

    async def _validate_task_exists(
        self,
        session: AsyncSession,
        task_id: int,
    ) -> Task:
        """タスク存在確認

        Args:
            session: Database session
            task_id: Task ID

        Returns:
            Task object

        Raises:
            NotFoundException: タスクが存在しない
        """
        query = select(Task).where(Task.id == task_id)
        result = await session.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            raise NotFoundException(f"Task with id {task_id} not found")

        return task

    async def _validate_task_not_archived(self, task: Task) -> None:
        """タスクがアーカイブされていないことを確認

        Args:
            task: Task object

        Raises:
            ValidationException: タスクがarchive状態
        """
        if task.status == "archive":
            raise ValidationException(
                f"Task {task.id} is already archived and cannot be modified"
            )

    async def _validate_same_project(self, tasks: List[Task]) -> None:
        """全タスクが同一プロジェクトに属することを確認

        Args:
            tasks: Task objects

        Raises:
            ValidationException: project_idが異なる
        """
        if not tasks:
            return

        first_project_id = tasks[0].project_id

        for task in tasks[1:]:
            if task.project_id != first_project_id:
                raise ValidationException(
                    f"All tasks must belong to the same project. "
                    f"Found project_id {first_project_id} and {task.project_id}"
                )

    async def _create_subtasks(
        self,
        session: AsyncSession,
        parent_task: Task,
        subtasks: List[SubtaskInput],
    ) -> List[Task]:
        """サブタスクを作成

        継承する項目:
        - project_id
        - decomposition_level (parent + 1)
        - parent_task_id

        Args:
            session: Database session
            parent_task: 親タスク
            subtasks: サブタスク情報リスト

        Returns:
            作成されたサブタスクリスト
        """
        created = []

        for subtask_input in subtasks:
            new_task = Task(
                name=subtask_input.name,
                project_id=parent_task.project_id,
                genre_id=subtask_input.genre_id or parent_task.genre_id,
                estimated_hours=subtask_input.estimated_hours,
                priority=subtask_input.priority,
                deadline=subtask_input.deadline or parent_task.deadline,
                parent_task_id=parent_task.id,
                decomposition_level=parent_task.decomposition_level + 1,
                status="todo",
            )
            created.append(new_task)

        return created

    async def _transfer_time_entries(
        self,
        session: AsyncSession,
        from_task_ids: List[int],
        to_task_id: int,
    ) -> int:
        """TimeEntryを転送

        Args:
            session: Database session
            from_task_ids: 転送元タスクIDリスト
            to_task_id: 転送先タスクID

        Returns:
            転送したエントリ数
        """
        # TimeEntryのtask_idを一括更新
        stmt = (
            update(TimeEntry)
            .where(TimeEntry.task_id.in_(from_task_ids))
            .values(task_id=to_task_id)
        )
        result = await session.execute(stmt)
        return result.rowcount

    async def _transfer_schedules(
        self,
        session: AsyncSession,
        from_task_ids: List[int],
        to_task_id: int,
    ) -> int:
        """Scheduleを転送

        Args:
            session: Database session
            from_task_ids: 転送元タスクIDリスト
            to_task_id: 転送先タスクID

        Returns:
            転送したスケジュール数
        """
        # Scheduleのtask_idを一括更新
        stmt = (
            update(Schedule)
            .where(Schedule.task_id.in_(from_task_ids))
            .values(task_id=to_task_id)
        )
        result = await session.execute(stmt)
        return result.rowcount

    async def _calculate_total_actual_hours(self, tasks: List[Task]) -> Decimal:
        """複数タスクのactual_hours合計を計算

        Args:
            tasks: Task objects

        Returns:
            actual_hoursの合計
        """
        total = Decimal("0")
        for task in tasks:
            total += task.actual_hours or Decimal("0")
        return total
