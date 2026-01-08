"""Schedule generation service with Claude API integration."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any

from sqlmodel import select, func, and_
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Task, Schedule, Project, Genre, TimeEntry, TaskDependency
from app.clients.claude_client import ClaudeClient, ClaudeAPIException
from app.schemas.workflow_requests import (
    SchedulePreferences,
    DailyHours,
    FixedEvent,
)
from app.schemas.workflow_responses import (
    WeeklyScheduleResponse,
    ScheduleEntry,
    ScheduleSummary,
    ProjectSummary,
    GenreSummary,
)
from app.exceptions import ValidationException

logger = logging.getLogger(__name__)


@dataclass
class SchedulableTask:
    """Task data prepared for scheduling."""

    id: int
    name: str
    project_id: Optional[int]
    project_name: Optional[str]
    genre_id: Optional[int]
    genre_name: Optional[str]
    priority: str
    want_level: str
    deadline: Optional[datetime]
    estimated_hours: Decimal
    actual_hours: Decimal
    remaining_hours: Decimal
    is_splittable: bool
    min_work_unit: Decimal


@dataclass
class ParsedScheduleEntry:
    """Parsed schedule entry from Claude response."""

    task_id: int
    date: datetime
    start_time: Optional[str]
    end_time: Optional[str]
    allocated_hours: Decimal
    reasoning: Optional[str] = None


class ScheduleService:
    """Service for AI-powered schedule generation."""

    def __init__(self, claude_client: Optional[ClaudeClient] = None):
        self.claude_client = claude_client or ClaudeClient()

    async def generate_weekly_schedule(
        self,
        session: AsyncSession,
        week_start: datetime,
        preferences: SchedulePreferences,
        fixed_events: List[FixedEvent],
        clear_existing: bool = True,
    ) -> WeeklyScheduleResponse:
        """Generate optimized weekly schedule using Claude API.

        Args:
            session: Database session
            week_start: Start date of the week (Monday)
            preferences: User scheduling preferences
            fixed_events: Fixed events that block time
            clear_existing: Whether to clear existing AI-generated schedules

        Returns:
            WeeklyScheduleResponse with generated schedules
        """
        week_end = week_start + timedelta(days=6)

        # 1. Clear existing AI-generated schedules if requested
        if clear_existing:
            await self._clear_existing_ai_schedules(session, week_start, week_end)

        # 2. Gather schedulable tasks
        tasks = await self._gather_schedulable_tasks(session, week_end)

        if not tasks:
            return WeeklyScheduleResponse(
                week_start=week_start,
                week_end=week_end,
                schedules=[],
                summary=ScheduleSummary(
                    total_planned_hours=Decimal("0"),
                    by_project=[],
                    by_genre=[],
                ),
                warnings=["スケジュール可能なタスクがありません"],
            )

        # 3. Gather task dependencies
        task_ids = [t.id for t in tasks]
        dependencies = await self._gather_task_dependencies(session, task_ids)

        # 4. Build Claude API prompts
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            tasks, dependencies, preferences, fixed_events, week_start, week_end
        )

        # 5. Call Claude API
        try:
            response_text = await self.claude_client.generate_schedule(
                system_prompt, user_prompt
            )
        except ClaudeAPIException as e:
            logger.error(f"Claude API error: {e}")
            raise

        # 6. Parse response
        parsed_entries = self._parse_schedule_response(response_text, tasks)

        # 7. Validate and generate warnings
        warnings = self._validate_schedule(
            parsed_entries, tasks, preferences, dependencies
        )

        # 8. Create schedule records in database
        created_schedules = await self._create_schedule_records(
            session, parsed_entries, tasks
        )

        # 9. Build summary
        summary = self._build_summary(created_schedules, tasks)

        # 10. Build response entries with task details
        schedule_entries = self._build_schedule_entries(created_schedules, tasks)

        return WeeklyScheduleResponse(
            week_start=week_start,
            week_end=week_end,
            schedules=schedule_entries,
            summary=summary,
            warnings=warnings,
        )

    async def _gather_schedulable_tasks(
        self,
        session: AsyncSession,
        week_end: datetime,
    ) -> List[SchedulableTask]:
        """Get active tasks that need scheduling.

        Active tasks are those with status in (todo, doing, waiting)
        and have remaining hours > 0.
        """
        query = (
            select(Task)
            .where(Task.status.in_(["todo", "doing", "waiting"]))
            .options(
                selectinload(Task.project),
                selectinload(Task.genre),
            )
        )
        result = await session.execute(query)
        db_tasks = result.scalars().all()

        schedulable_tasks = []
        for task in db_tasks:
            # Calculate actual hours from time entries
            actual_query = select(func.sum(TimeEntry.duration_minutes)).where(
                TimeEntry.task_id == task.id
            )
            actual_result = await session.execute(actual_query)
            actual_minutes = actual_result.scalar_one() or 0
            actual_hours = Decimal(str(actual_minutes)) / Decimal("60")

            # Calculate remaining hours
            estimated = task.estimated_hours or Decimal("1")
            remaining = max(estimated - actual_hours, Decimal("0"))

            # Skip if no remaining hours
            if remaining <= 0:
                continue

            schedulable_tasks.append(
                SchedulableTask(
                    id=task.id,
                    name=task.name,
                    project_id=task.project_id,
                    project_name=task.project.name if task.project else None,
                    genre_id=task.genre_id,
                    genre_name=task.genre.name if task.genre else None,
                    priority=task.priority,
                    want_level=task.want_level,
                    deadline=task.deadline,
                    estimated_hours=estimated,
                    actual_hours=actual_hours,
                    remaining_hours=remaining,
                    is_splittable=task.is_splittable,
                    min_work_unit=task.min_work_unit,
                )
            )

        return schedulable_tasks

    async def _gather_task_dependencies(
        self,
        session: AsyncSession,
        task_ids: List[int],
    ) -> Dict[int, List[int]]:
        """Get dependency graph for tasks.

        Returns:
            Dict mapping task_id -> list of task_ids it depends on
        """
        query = select(TaskDependency).where(TaskDependency.task_id.in_(task_ids))
        result = await session.execute(query)
        deps = result.scalars().all()

        dependency_map: Dict[int, List[int]] = {tid: [] for tid in task_ids}
        for dep in deps:
            if dep.depends_on_task_id in task_ids:
                dependency_map[dep.task_id].append(dep.depends_on_task_id)

        return dependency_map

    def _build_system_prompt(self) -> str:
        """Build the system prompt for Claude API."""
        return """あなたは研究時間管理アシスタントです。最適化された週間スケジュールを作成します。
有効なJSON配列のみを出力してください。説明文は不要です。

スケジューリングルール:
1. 各日の作業可能時間を超えない
2. 優先度が高いタスク（高）を先にスケジュール
3. タスクの依存関係を尊重（前提タスク完了後に依存タスク）
4. 締切が近いタスクを優先
5. コンテキストスイッチを最小化（同じプロジェクトをグループ化）
6. 固定予定の時間帯を避ける
7. 各タスクのmin_work_unit未満の作業時間は割り当てない
8. 全タスクのremaining_hoursを消化できるよう配分

出力形式（JSON配列のみ）:
[
  {
    "task_id": 1,
    "date": "2025-01-13",
    "start_time": "09:00",
    "end_time": "12:00",
    "allocated_hours": 3.0,
    "reasoning": "高優先度、締切接近"
  }
]"""

    def _build_user_prompt(
        self,
        tasks: List[SchedulableTask],
        dependencies: Dict[int, List[int]],
        preferences: SchedulePreferences,
        fixed_events: List[FixedEvent],
        week_start: datetime,
        week_end: datetime,
    ) -> str:
        """Build the user prompt with scheduling data."""
        # Format daily hours
        daily_hours = preferences.daily_hours
        days = ["月", "火", "水", "木", "金", "土", "日"]
        hours_list = [
            daily_hours.mon,
            daily_hours.tue,
            daily_hours.wed,
            daily_hours.thu,
            daily_hours.fri,
            daily_hours.sat,
            daily_hours.sun,
        ]
        daily_hours_str = "\n".join(
            f"- {day}: {hours}時間" for day, hours in zip(days, hours_list)
        )

        # Format fixed events
        fixed_events_str = "なし"
        if fixed_events:
            events_list = []
            for e in fixed_events:
                events_list.append(
                    f"- {e.date.strftime('%Y-%m-%d')} {e.start_time}-{e.end_time}: {e.title}"
                )
            fixed_events_str = "\n".join(events_list)

        # Format tasks as JSON
        tasks_data = []
        for t in tasks:
            tasks_data.append(
                {
                    "id": t.id,
                    "name": t.name,
                    "project": t.project_name,
                    "genre": t.genre_name,
                    "priority": t.priority,
                    "want_level": t.want_level,
                    "deadline": t.deadline.isoformat() if t.deadline else None,
                    "remaining_hours": float(t.remaining_hours),
                    "is_splittable": t.is_splittable,
                    "min_work_unit": float(t.min_work_unit),
                }
            )
        tasks_json = json.dumps(tasks_data, ensure_ascii=False, indent=2)

        # Format dependencies
        deps_data = {
            str(k): v for k, v in dependencies.items() if v
        }  # Only include non-empty
        deps_json = json.dumps(deps_data, ensure_ascii=False) if deps_data else "{}"

        return f"""週間スケジュールを生成してください。

## 期間
{week_start.strftime('%Y-%m-%d')}（月）〜 {week_end.strftime('%Y-%m-%d')}（日）

## 曜日別作業可能時間
{daily_hours_str}

## 固定予定（ブロック時間帯）
{fixed_events_str}

## タスク一覧
{tasks_json}

## 依存関係（task_id: [depends_on_task_ids]）
{deps_json}

## 追加設定
- 1タスク1日あたり最大時間: {preferences.max_hours_per_task_per_day}時間
- コンテキストスイッチ回避: {"はい" if preferences.avoid_context_switch else "いいえ"}
{f"- フォーカスプロジェクト: ID={preferences.focus_project_id}" if preferences.focus_project_id else ""}

JSON配列のみを出力してください。"""

    def _parse_schedule_response(
        self,
        response_text: str,
        tasks: List[SchedulableTask],
    ) -> List[ParsedScheduleEntry]:
        """Parse Claude API response into structured data."""
        # Try to extract JSON from response
        text = response_text.strip()

        # Handle markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            raise ValidationException(f"Claude APIの応答をパースできませんでした: {e}")

        if not isinstance(data, list):
            raise ValidationException("Claude APIの応答が配列形式ではありません")

        # Validate task IDs
        valid_task_ids = {t.id for t in tasks}
        entries = []

        for item in data:
            task_id = item.get("task_id")
            if task_id not in valid_task_ids:
                logger.warning(f"Unknown task_id in response: {task_id}")
                continue

            try:
                entry = ParsedScheduleEntry(
                    task_id=task_id,
                    date=datetime.fromisoformat(item["date"]),
                    start_time=item.get("start_time"),
                    end_time=item.get("end_time"),
                    allocated_hours=Decimal(str(item["allocated_hours"])),
                    reasoning=item.get("reasoning"),
                )
                entries.append(entry)
            except (KeyError, ValueError) as e:
                logger.warning(f"Skipping invalid entry: {item}, error: {e}")
                continue

        return entries

    def _validate_schedule(
        self,
        entries: List[ParsedScheduleEntry],
        tasks: List[SchedulableTask],
        preferences: SchedulePreferences,
        dependencies: Dict[int, List[int]],
    ) -> List[str]:
        """Validate generated schedule and return warnings."""
        warnings = []
        task_map = {t.id: t for t in tasks}

        # Check total hours per day
        daily_hours_config = preferences.daily_hours
        hours_by_date: Dict[str, Decimal] = {}
        for entry in entries:
            date_str = entry.date.strftime("%Y-%m-%d")
            hours_by_date[date_str] = hours_by_date.get(
                date_str, Decimal("0")
            ) + entry.allocated_hours

        weekday_limits = {
            0: daily_hours_config.mon,
            1: daily_hours_config.tue,
            2: daily_hours_config.wed,
            3: daily_hours_config.thu,
            4: daily_hours_config.fri,
            5: daily_hours_config.sat,
            6: daily_hours_config.sun,
        }

        for entry in entries:
            date_str = entry.date.strftime("%Y-%m-%d")
            weekday = entry.date.weekday()
            limit = weekday_limits.get(weekday, Decimal("6"))
            if hours_by_date.get(date_str, Decimal("0")) > limit:
                warnings.append(f"{date_str}の作業時間が{limit}時間を超えています")

        # Check if all remaining hours are scheduled
        scheduled_hours: Dict[int, Decimal] = {}
        for entry in entries:
            scheduled_hours[entry.task_id] = scheduled_hours.get(
                entry.task_id, Decimal("0")
            ) + entry.allocated_hours

        for task in tasks:
            scheduled = scheduled_hours.get(task.id, Decimal("0"))
            if scheduled < task.remaining_hours:
                diff = task.remaining_hours - scheduled
                warnings.append(
                    f"タスク「{task.name}」の残り{diff:.1f}時間がスケジュールされていません"
                )

        # Check dependency order
        task_first_date: Dict[int, datetime] = {}
        for entry in entries:
            if entry.task_id not in task_first_date:
                task_first_date[entry.task_id] = entry.date
            elif entry.date < task_first_date[entry.task_id]:
                task_first_date[entry.task_id] = entry.date

        for task_id, dep_ids in dependencies.items():
            if task_id not in task_first_date:
                continue
            task_date = task_first_date[task_id]
            for dep_id in dep_ids:
                if dep_id in task_first_date:
                    # Check if all work on dependency is done before this task starts
                    # This is a simplified check - just comparing first dates
                    if task_first_date[dep_id] >= task_date:
                        task_name = task_map[task_id].name
                        dep_name = task_map[dep_id].name
                        warnings.append(
                            f"依存関係違反: 「{task_name}」は「{dep_name}」完了後に開始すべきです"
                        )

        # Check deadlines
        for task in tasks:
            if task.deadline:
                scheduled = scheduled_hours.get(task.id, Decimal("0"))
                # Find last scheduled date for this task
                last_date = None
                for entry in entries:
                    if entry.task_id == task.id:
                        if last_date is None or entry.date > last_date:
                            last_date = entry.date
                if last_date and last_date > task.deadline:
                    warnings.append(
                        f"タスク「{task.name}」の締切({task.deadline.strftime('%Y-%m-%d')})を超過するスケジュールです"
                    )

        return warnings

    def _parse_time_string(self, time_str: str, base_date: datetime) -> Optional[datetime]:
        """Parse time string like '09:00' or '24:00' into datetime."""
        if not time_str:
            return None
        try:
            # Handle "24:00" which means midnight of next day
            if time_str == "24:00":
                return datetime.combine(base_date.date(), datetime.strptime("00:00", "%H:%M").time()) + timedelta(days=1)
            return datetime.combine(base_date.date(), datetime.strptime(time_str, "%H:%M").time())
        except ValueError:
            logger.warning(f"Invalid time format: {time_str}")
            return None

    async def _create_schedule_records(
        self,
        session: AsyncSession,
        entries: List[ParsedScheduleEntry],
        tasks: List[SchedulableTask],
    ) -> List[Schedule]:
        """Create Schedule records in database."""
        created = []
        for entry in entries:
            schedule = Schedule(
                task_id=entry.task_id,
                scheduled_date=entry.date,
                start_time=self._parse_time_string(entry.start_time, entry.date),
                end_time=self._parse_time_string(entry.end_time, entry.date),
                allocated_hours=entry.allocated_hours,
                is_generated_by_ai=True,
                status="scheduled",
            )
            session.add(schedule)
            created.append(schedule)

        await session.commit()

        # Refresh to get IDs
        for schedule in created:
            await session.refresh(schedule)

        return created

    async def _clear_existing_ai_schedules(
        self,
        session: AsyncSession,
        week_start: datetime,
        week_end: datetime,
    ) -> int:
        """Clear existing AI-generated schedules for the week."""
        from sqlmodel import delete

        # Delete AI-generated schedules in the date range
        stmt = delete(Schedule).where(
            and_(
                Schedule.is_generated_by_ai == True,
                Schedule.scheduled_date >= week_start,
                Schedule.scheduled_date <= week_end + timedelta(days=1),
                Schedule.status == "scheduled",  # Don't delete completed/skipped
            )
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount

    def _build_summary(
        self,
        schedules: List[Schedule],
        tasks: List[SchedulableTask],
    ) -> ScheduleSummary:
        """Build summary of scheduled hours."""
        task_map = {t.id: t for t in tasks}

        total_hours = Decimal("0")
        by_project: Dict[Optional[int], Decimal] = {}
        by_genre: Dict[Optional[int], Decimal] = {}
        project_names: Dict[Optional[int], str] = {}
        genre_names: Dict[Optional[int], str] = {}

        for schedule in schedules:
            task = task_map.get(schedule.task_id)
            if not task:
                continue

            hours = schedule.allocated_hours
            total_hours += hours

            # By project
            pid = task.project_id
            by_project[pid] = by_project.get(pid, Decimal("0")) + hours
            if task.project_name:
                project_names[pid] = task.project_name

            # By genre
            gid = task.genre_id
            by_genre[gid] = by_genre.get(gid, Decimal("0")) + hours
            if task.genre_name:
                genre_names[gid] = task.genre_name

        # Convert to response format
        project_summaries = [
            ProjectSummary(
                id=pid,
                name=project_names.get(pid, "未分類"),
                hours=hours,
            )
            for pid, hours in by_project.items()
        ]

        genre_summaries = [
            GenreSummary(
                id=gid,
                name=genre_names.get(gid, "未分類"),
                hours=hours,
            )
            for gid, hours in by_genre.items()
        ]

        return ScheduleSummary(
            total_planned_hours=total_hours,
            by_project=project_summaries,
            by_genre=genre_summaries,
        )

    def _build_schedule_entries(
        self,
        schedules: List[Schedule],
        tasks: List[SchedulableTask],
    ) -> List[ScheduleEntry]:
        """Build schedule entry responses with task details."""
        task_map = {t.id: t for t in tasks}
        entries = []

        for schedule in schedules:
            task = task_map.get(schedule.task_id)
            entries.append(
                ScheduleEntry(
                    id=schedule.id,
                    task_id=schedule.task_id,
                    task_name=task.name if task else "Unknown",
                    project_name=task.project_name if task else None,
                    genre_name=task.genre_name if task else None,
                    genre_color=None,  # Would need to fetch from Genre model
                    date=schedule.scheduled_date,
                    start_time=(
                        schedule.start_time.strftime("%H:%M")
                        if schedule.start_time
                        else None
                    ),
                    end_time=(
                        schedule.end_time.strftime("%H:%M") if schedule.end_time else None
                    ),
                    allocated_hours=schedule.allocated_hours,
                    is_generated_by_ai=schedule.is_generated_by_ai,
                )
            )

        return entries
