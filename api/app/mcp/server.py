"""MCP Server implementation."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Task, Project, Genre, Schedule, TimeEntry, TaskCreate, TaskUpdate
from app.mcp.tools import MCP_TOOLS
from app.services.timer_service import TimerService
from app.services.dashboard_service import DashboardService
from app.services.task_service import TaskService
from app.services.task_workflow_service import TaskWorkflowService
from app.services.base import BaseCRUDService
from app.schemas.workflow_requests import SubtaskInput, TaskInput
from app.exceptions import NotFoundException, ValidationException


class MCPServer:
    """MCP Server for handling tool calls from Claude.ai."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.timer_service = TimerService()
        self.dashboard_service = DashboardService()
        self.task_service = TaskService(Task)
        self.task_workflow_service = TaskWorkflowService()
        self.project_service = BaseCRUDService[Project, Any](Project)

        # Map tool names to handlers
        self.tool_handlers: dict[str, Callable] = {
            # Reference tools
            "get_today_schedule": self._handle_get_today_schedule,
            "get_week_schedule": self._handle_get_week_schedule,
            "get_kanban_view": self._handle_get_kanban_view,
            "get_projects": self._handle_get_projects,
            "get_task_detail": self._handle_get_task_detail,
            "get_summary": self._handle_get_summary,
            "get_timer_status": self._handle_get_timer_status,
            # Timer tools
            "start_timer": self._handle_start_timer,
            "stop_timer": self._handle_stop_timer,
            # Task tools
            "create_task": self._handle_create_task,
            "update_task": self._handle_update_task,
            "complete_task": self._handle_complete_task,
            "breakdown_task": self._handle_breakdown_task,
            "merge_tasks": self._handle_merge_tasks,
            # Project tool
            "create_project": self._handle_create_project,
            # Schedule tools (placeholders)
            "generate_weekly_schedule": self._handle_generate_weekly_schedule,
            "reschedule": self._handle_reschedule,
        }

    def get_tools(self) -> list[dict]:
        """Return list of available MCP tools."""
        return MCP_TOOLS

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Execute a tool and return the result.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Dict with "result" or "error" key
        """
        handler = self.tool_handlers.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}

        try:
            result = await handler(arguments)
            return {"result": result}
        except NotFoundException as e:
            return {"error": str(e)}
        except ValidationException as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Internal error: {str(e)}"}

    # ===== Reference Tool Handlers =====

    async def _handle_get_today_schedule(self, args: dict) -> dict:
        """Get today's schedule and timer status."""
        response = await self.dashboard_service.get_today(self.session)
        return self._serialize_response(response)

    async def _handle_get_week_schedule(self, args: dict) -> dict:
        """Get weekly schedule."""
        week_start = None
        if args.get("week_start"):
            week_start = date.fromisoformat(args["week_start"])

        response = await self.dashboard_service.get_weekly(self.session, week_start)
        return self._serialize_response(response)

    async def _handle_get_kanban_view(self, args: dict) -> dict:
        """Get kanban view."""
        project_id = args.get("project_id")
        response = await self.dashboard_service.get_kanban(self.session, project_id)
        return self._serialize_response(response)

    async def _handle_get_projects(self, args: dict) -> dict:
        """Get projects list."""
        filters = {}
        if "is_active" in args:
            filters["is_active"] = args["is_active"]

        projects, total = await self.project_service.get_all(
            self.session,
            filters=filters if filters else None,
            order_by="-created_at",
        )

        return {
            "items": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "deadline": p.deadline.isoformat() if p.deadline else None,
                    "is_active": p.is_active,
                }
                for p in projects
            ],
            "total": total,
        }

    async def _handle_get_task_detail(self, args: dict) -> dict:
        """Get task detail with dependencies and time entries."""
        task_id = args["task_id"]

        # Get task with relationships
        query = (
            select(Task)
            .options(
                selectinload(Task.project),
                selectinload(Task.genre),
                selectinload(Task.time_entries),
                selectinload(Task.schedules),
            )
            .where(Task.id == task_id)
        )
        result = await self.session.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            raise NotFoundException(f"Task with id {task_id} not found")

        # Calculate actual hours
        actual_minutes = sum(
            te.duration_minutes or 0
            for te in task.time_entries
            if te.duration_minutes
        )
        actual_hours = Decimal(actual_minutes) / 60

        # Get dependencies
        from app.services.task_dependency_service import TaskDependencyService
        dep_service = TaskDependencyService()
        deps = await dep_service.get_dependencies(self.session, task_id)

        return {
            "id": task.id,
            "name": task.name,
            "status": task.status,
            "project": {
                "id": task.project.id,
                "name": task.project.name,
            } if task.project else None,
            "genre": {
                "id": task.genre.id,
                "name": task.genre.name,
                "color": task.genre.color,
            } if task.genre else None,
            "estimated_hours": float(task.estimated_hours) if task.estimated_hours else None,
            "actual_hours": float(actual_hours),
            "priority": task.priority,
            "want_level": task.want_level,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "note": task.note,
            "dependencies": deps,
            "time_entries": [
                {
                    "id": te.id,
                    "start_time": te.start_time.isoformat(),
                    "end_time": te.end_time.isoformat() if te.end_time else None,
                    "duration_minutes": te.duration_minutes,
                }
                for te in task.time_entries
            ],
            "schedules": [
                {
                    "id": s.id,
                    "scheduled_date": s.scheduled_date.isoformat(),
                    "allocated_hours": float(s.allocated_hours),
                    "status": s.status,
                }
                for s in task.schedules
            ],
        }

    async def _handle_get_summary(self, args: dict) -> dict:
        """Get overall summary."""
        response = await self.dashboard_service.get_summary(self.session)
        return self._serialize_response(response)

    async def _handle_get_timer_status(self, args: dict) -> dict:
        """Get current timer status."""
        return await self.timer_service.get_timer_status(self.session)

    # ===== Timer Tool Handlers =====

    async def _handle_start_timer(self, args: dict) -> dict:
        """Start timer for a task."""
        task_id = args.get("task_id")
        task_name = args.get("task_name")

        if not task_id and not task_name:
            raise ValidationException("Either task_id or task_name is required")

        new_entry, previous_entry = await self.timer_service.start_timer(
            self.session,
            task_id=task_id,
            task_name=task_name,
        )

        # Load task name for response
        await self.session.refresh(new_entry, ["task"])

        result = {
            "started": {
                "time_entry_id": new_entry.id,
                "task_id": new_entry.task_id,
                "task_name": new_entry.task.name,
                "start_time": new_entry.start_time.isoformat(),
            }
        }

        if previous_entry:
            result["auto_stopped"] = {
                "time_entry_id": previous_entry.id,
                "task_id": previous_entry.task_id,
                "duration_minutes": previous_entry.duration_minutes,
            }

        return result

    async def _handle_stop_timer(self, args: dict) -> dict:
        """Stop the running timer."""
        note = args.get("note")

        entry = await self.timer_service.stop_timer(self.session, note=note)
        await self.session.refresh(entry, ["task"])

        return {
            "stopped": {
                "time_entry_id": entry.id,
                "task_id": entry.task_id,
                "task_name": entry.task.name,
                "start_time": entry.start_time.isoformat(),
                "end_time": entry.end_time.isoformat(),
                "duration_minutes": entry.duration_minutes,
            }
        }

    # ===== Task Tool Handlers =====

    async def _handle_create_task(self, args: dict) -> dict:
        """Create a new task."""
        # Parse deadline if provided
        deadline = None
        if args.get("deadline"):
            deadline = datetime.fromisoformat(args["deadline"].replace("Z", "+00:00"))

        # Create task
        task = Task(
            name=args["name"],
            project_id=args.get("project_id"),
            genre_id=args.get("genre_id"),
            estimated_hours=Decimal(str(args["estimated_hours"])) if args.get("estimated_hours") else None,
            priority=args.get("priority", "中"),
            want_level=args.get("want_level", "中"),
            deadline=deadline,
            status="todo",
        )

        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)

        return {
            "created": {
                "id": task.id,
                "name": task.name,
                "status": task.status,
            }
        }

    async def _handle_update_task(self, args: dict) -> dict:
        """Update an existing task."""
        task_id = args["task_id"]

        # Build update data
        update_data = {}
        if "name" in args:
            update_data["name"] = args["name"]
        if "status" in args:
            update_data["status"] = args["status"]
        if "estimated_hours" in args:
            update_data["estimated_hours"] = Decimal(str(args["estimated_hours"]))
        if "priority" in args:
            update_data["priority"] = args["priority"]
        if "want_level" in args:
            update_data["want_level"] = args["want_level"]
        if "deadline" in args:
            update_data["deadline"] = datetime.fromisoformat(
                args["deadline"].replace("Z", "+00:00")
            )
        if "note" in args:
            update_data["note"] = args["note"]

        task_update = TaskUpdate(**update_data)
        task = await self.task_service.update(self.session, task_id, task_update)

        return {
            "updated": {
                "id": task.id,
                "name": task.name,
                "status": task.status,
            }
        }

    async def _handle_complete_task(self, args: dict) -> dict:
        """Complete a task."""
        task_id = args["task_id"]

        task_update = TaskUpdate(status="done")
        task = await self.task_service.update(self.session, task_id, task_update)

        return {
            "completed": {
                "id": task.id,
                "name": task.name,
                "status": task.status,
            }
        }

    async def _handle_breakdown_task(self, args: dict) -> dict:
        """Break down a task into subtasks."""
        task_id = args["task_id"]
        subtasks_data = args["subtasks"]
        reason = args.get("reason")

        # Convert to SubtaskInput list
        subtasks = [
            SubtaskInput(
                name=st["name"],
                estimated_hours=Decimal(str(st["estimated_hours"])) if st.get("estimated_hours") else None,
                genre_id=st.get("genre_id"),
            )
            for st in subtasks_data
        ]

        response = await self.task_workflow_service.breakdown_task(
            self.session,
            task_id=task_id,
            subtasks=subtasks,
            reason=reason,
            archive_original=True,
        )

        return self._serialize_response(response)

    async def _handle_merge_tasks(self, args: dict) -> dict:
        """Merge multiple tasks into one."""
        task_ids = args["task_ids"]
        merged_name = args["merged_name"]
        reason = args.get("reason")

        merged_task = TaskInput(name=merged_name)

        response = await self.task_workflow_service.merge_tasks(
            self.session,
            task_ids=task_ids,
            merged_task=merged_task,
            reason=reason,
        )

        return self._serialize_response(response)

    # ===== Project Tool Handlers =====

    async def _handle_create_project(self, args: dict) -> dict:
        """Create a new project."""
        deadline = None
        if args.get("deadline"):
            deadline = datetime.fromisoformat(args["deadline"].replace("Z", "+00:00"))

        project = Project(
            name=args["name"],
            description=args.get("description") or args.get("goal"),  # goal is alias
            deadline=deadline,
            is_active=True,
        )

        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)

        return {
            "created": {
                "id": project.id,
                "name": project.name,
            }
        }

    # ===== Schedule Tool Handlers (Placeholders) =====

    async def _handle_generate_weekly_schedule(self, args: dict) -> dict:
        """Generate weekly schedule (not implemented)."""
        return {
            "error": "Not implemented",
            "message": "週間スケジュール自動生成機能は未実装です。Claude APIとの統合が必要です。",
        }

    async def _handle_reschedule(self, args: dict) -> dict:
        """Reschedule a specific date (not implemented)."""
        return {
            "error": "Not implemented",
            "message": "リスケジュール機能は未実装です。Claude APIとの統合が必要です。",
        }

    # ===== Helper Methods =====

    def _serialize_response(self, obj: Any) -> dict:
        """Serialize a Pydantic model or SQLModel to dict.

        Handles Decimal and datetime conversion.
        """
        if hasattr(obj, "model_dump"):
            data = obj.model_dump()
        elif hasattr(obj, "dict"):
            data = obj.dict()
        else:
            return obj

        return self._convert_types(data)

    def _convert_types(self, obj: Any) -> Any:
        """Recursively convert Decimal and datetime to JSON-serializable types."""
        if isinstance(obj, dict):
            return {k: self._convert_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_types(item) for item in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        else:
            return obj
