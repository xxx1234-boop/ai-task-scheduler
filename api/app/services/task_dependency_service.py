from typing import List, Set

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Task, TaskDependency
from app.exceptions import (
    NotFoundException,
    ValidationException,
    DependencyCycleException,
)
from app.schemas.workflow_responses import TaskSummary


class TaskDependencyService:
    """タスク依存関係管理サービス"""

    async def get_dependencies(
        self, session: AsyncSession, task_id: int
    ) -> dict:
        """タスクの依存関係を取得（depends_on & blocking）

        Args:
            session: Database session
            task_id: Task ID

        Returns:
            {
                "depends_on": [...],  # このタスクが依存するタスク
                "blocking": [...]     # このタスクがブロックするタスク
            }

        Raises:
            NotFoundException: タスクが存在しない
        """
        # タスク存在確認
        task = await self._get_task_by_id(session, task_id)

        # このタスクが依存するタスクID一覧を取得
        depends_on_ids = await self._get_all_dependencies(session, task_id)

        # このタスクがブロックするタスクID一覧を取得
        blocking_ids = await self._get_all_blocking(session, task_id)

        # TaskSummaryに変換
        depends_on_tasks = []
        if depends_on_ids:
            query = select(Task).where(Task.id.in_(depends_on_ids))
            result = await session.execute(query)
            depends_on_tasks = [
                TaskSummary(id=t.id, name=t.name, status=t.status)
                for t in result.scalars().all()
            ]

        blocking_tasks = []
        if blocking_ids:
            query = select(Task).where(Task.id.in_(blocking_ids))
            result = await session.execute(query)
            blocking_tasks = [
                TaskSummary(id=t.id, name=t.name, status=t.status)
                for t in result.scalars().all()
            ]

        return {
            "depends_on": depends_on_tasks,
            "blocking": blocking_tasks,
        }

    async def add_dependency(
        self,
        session: AsyncSession,
        task_id: int,
        depends_on_task_id: int,
    ) -> None:
        """依存関係を追加（循環チェック付き）

        Args:
            session: Database session
            task_id: Task ID
            depends_on_task_id: 依存先タスクID

        Raises:
            ValidationException: 自己参照の場合
            DependencyCycleException: 循環依存が発生する場合
            NotFoundException: タスクが存在しない場合
        """
        # 自己参照チェック
        if task_id == depends_on_task_id:
            raise ValidationException("Task cannot depend on itself")

        # 両タスクの存在確認
        await self._get_task_by_id(session, task_id)
        await self._get_task_by_id(session, depends_on_task_id)

        # 循環依存チェック
        await self.check_cycle(session, task_id, [depends_on_task_id])

        # 依存関係を追加
        dependency = TaskDependency(
            task_id=task_id,
            depends_on_task_id=depends_on_task_id,
        )
        session.add(dependency)
        await session.commit()

    async def remove_dependency(
        self,
        session: AsyncSession,
        task_id: int,
        depends_on_task_id: int,
    ) -> None:
        """依存関係を削除

        Args:
            session: Database session
            task_id: Task ID
            depends_on_task_id: 依存先タスクID

        Raises:
            NotFoundException: 依存関係が存在しない場合
        """
        query = select(TaskDependency).where(
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_task_id == depends_on_task_id,
        )
        result = await session.execute(query)
        dependency = result.scalar_one_or_none()

        if not dependency:
            raise NotFoundException(
                f"Dependency from task {task_id} to {depends_on_task_id} not found"
            )

        await session.delete(dependency)
        await session.commit()

    async def check_cycle(
        self,
        session: AsyncSession,
        task_id: int,
        new_depends_on_ids: List[int],
    ) -> None:
        """新しい依存関係追加時の循環チェック

        Args:
            session: Database session
            task_id: Task ID
            new_depends_on_ids: 新たに依存させる予定のタスクID一覧

        Raises:
            DependencyCycleException: 循環が検出された場合
        """
        # 各新規依存先からtask_idに到達可能かチェック
        for depends_on_id in new_depends_on_ids:
            visited: Set[int] = set()
            recursion_stack: Set[int] = set()

            if await self._dfs_check_cycle(
                session, depends_on_id, task_id, visited, recursion_stack
            ):
                raise DependencyCycleException(
                    f"Adding dependency would create a cycle: {task_id} -> {depends_on_id}"
                )

    async def transfer_dependencies(
        self,
        session: AsyncSession,
        from_task_id: int,
        to_task_ids: List[int],
        mode: str,
    ) -> int:
        """依存関係を転送（breakdown時に使用）

        Args:
            session: Database session
            from_task_id: 元タスクID
            to_task_ids: 転送先タスクIDリスト
            mode: "to_all" = 全タスクへ, "to_last" = 最後のタスクへ

        Returns:
            転送した依存関係の数
        """
        count = 0

        # 元タスクが依存していたタスク（A → from_task）を取得
        incoming_deps = await self._get_all_dependencies(session, from_task_id)

        # 元タスクがブロックしていたタスク（from_task → B）を取得
        outgoing_deps = await self._get_all_blocking(session, from_task_id)

        # Incoming依存を転送（全サブタスクへ）
        for dep_id in incoming_deps:
            for to_task_id in to_task_ids:
                dependency = TaskDependency(
                    task_id=to_task_id,
                    depends_on_task_id=dep_id,
                )
                session.add(dependency)
                count += 1

        # Outgoing依存を転送（最後のサブタスクのみ or 全タスク）
        target_tasks = [to_task_ids[-1]] if mode == "to_last" else to_task_ids

        for dep_id in outgoing_deps:
            for to_task_id in target_tasks:
                dependency = TaskDependency(
                    task_id=dep_id,  # ブロックされるタスク
                    depends_on_task_id=to_task_id,  # 新しい依存先
                )
                session.add(dependency)
                count += 1

        return count

    async def merge_dependencies(
        self,
        session: AsyncSession,
        from_task_ids: List[int],
        to_task_id: int,
    ) -> int:
        """複数タスクの依存関係を統合（重複除去）

        Args:
            session: Database session
            from_task_ids: マージ元タスクIDリスト
            to_task_id: マージ先タスクID

        Returns:
            統合した依存関係の数
        """
        # 全マージ元タスクの依存先・被依存先を収集
        all_depends_on: Set[int] = set()
        all_blocking: Set[int] = set()

        for task_id in from_task_ids:
            deps = await self._get_all_dependencies(session, task_id)
            all_depends_on.update(deps)

            blocks = await self._get_all_blocking(session, task_id)
            all_blocking.update(blocks)

        # マージ元タスク自身への参照を除外
        all_depends_on.discard(to_task_id)
        all_depends_on -= set(from_task_ids)
        all_blocking.discard(to_task_id)
        all_blocking -= set(from_task_ids)

        count = 0

        # Incoming依存を追加（to_task が依存）
        for dep_id in all_depends_on:
            dependency = TaskDependency(
                task_id=to_task_id,
                depends_on_task_id=dep_id,
            )
            session.add(dependency)
            count += 1

        # Outgoing依存を追加（to_task がブロック）
        for dep_id in all_blocking:
            dependency = TaskDependency(
                task_id=dep_id,
                depends_on_task_id=to_task_id,
            )
            session.add(dependency)
            count += 1

        return count

    # ===== Private Methods =====

    async def _dfs_check_cycle(
        self,
        session: AsyncSession,
        current: int,
        target: int,
        visited: Set[int],
        recursion_stack: Set[int],
    ) -> bool:
        """DFSによる循環検出（再帰版）

        Args:
            current: 現在のノード
            target: 検索対象ノード（循環の起点）
            visited: 訪問済みノード
            recursion_stack: 再帰スタック（バックエッジ検出用）

        Returns:
            循環が存在する場合True
        """
        if current == target:
            return True  # 循環検出！

        if current in visited:
            return False  # 既に探索済み

        visited.add(current)
        recursion_stack.add(current)

        # currentが依存する全タスクを取得
        dependencies = await self._get_all_dependencies(session, current)

        for dep_id in dependencies:
            if dep_id in recursion_stack:
                # バックエッジ検出（同じ経路で再訪問）
                return True

            if await self._dfs_check_cycle(
                session, dep_id, target, visited, recursion_stack
            ):
                return True

        recursion_stack.remove(current)
        return False

    async def _get_all_dependencies(
        self,
        session: AsyncSession,
        task_id: int,
    ) -> List[int]:
        """タスクが依存する全タスクIDを取得

        Args:
            session: Database session
            task_id: Task ID

        Returns:
            依存先タスクID一覧
        """
        query = select(TaskDependency.depends_on_task_id).where(
            TaskDependency.task_id == task_id
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def _get_all_blocking(
        self,
        session: AsyncSession,
        task_id: int,
    ) -> List[int]:
        """タスクがブロックする全タスクIDを取得

        Args:
            session: Database session
            task_id: Task ID

        Returns:
            ブロック先タスクID一覧
        """
        query = select(TaskDependency.task_id).where(
            TaskDependency.depends_on_task_id == task_id
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def _get_task_by_id(
        self,
        session: AsyncSession,
        task_id: int,
    ) -> Task:
        """タスク取得

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
