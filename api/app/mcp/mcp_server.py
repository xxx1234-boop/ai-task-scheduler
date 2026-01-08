"""MCP Server using httpx to call the HTTP API."""

import os
from typing import Optional

import httpx
from fastmcp import FastMCP

# API base URL (within Docker network, api service is reachable at http://api:8000)
API_BASE_URL = os.getenv("API_URL", "http://api:8000")

# Initialize MCP server
mcp = FastMCP("Research Scheduler")

# Reusable httpx client
http_client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0)


async def api_get(path: str, params: dict = None) -> dict:
    """Make GET request to API."""
    try:
        response = await http_client.get(path, params=params)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"API error: {e.response.status_code}", "detail": e.response.text}
    except Exception as e:
        return {"error": str(e)}


async def api_post(path: str, json: dict = None) -> dict:
    """Make POST request to API."""
    try:
        response = await http_client.post(path, json=json or {})
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"API error: {e.response.status_code}", "detail": e.response.text}
    except Exception as e:
        return {"error": str(e)}


async def api_patch(path: str, json: dict = None) -> dict:
    """Make PATCH request to API."""
    try:
        response = await http_client.patch(path, json=json or {})
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"API error: {e.response.status_code}", "detail": e.response.text}
    except Exception as e:
        return {"error": str(e)}


async def api_delete(path: str) -> dict:
    """Make DELETE request to API."""
    try:
        response = await http_client.delete(path)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"API error: {e.response.status_code}", "detail": e.response.text}
    except Exception as e:
        return {"error": str(e)}


# ===== Reference Tools =====

@mcp.tool()
async def get_timer_status() -> dict:
    """現在のタイマー状態を取得します。稼働中のタイマーがあれば経過時間も表示します。"""
    return await api_get("/api/v1/workflow/timer/status")


@mcp.tool()
async def get_summary() -> dict:
    """全体サマリーを取得します。今日と今週の進捗、緊急タスク、タイマー状態を一覧表示します。"""
    return await api_get("/api/v1/dashboard/summary")


@mcp.tool()
async def get_today_schedule() -> dict:
    """今日のスケジュールとタイマー状態を取得します。予定されているタスク、計画時間、実績時間を確認できます。"""
    return await api_get("/api/v1/dashboard/today")


@mcp.tool()
async def get_week_schedule(week_start: Optional[str] = None) -> dict:
    """週間スケジュールを取得します。日別の計画時間と実績時間、プロジェクト・ジャンル別の集計を確認できます。

    Args:
        week_start: 週の開始日（YYYY-MM-DD形式）。指定しない場合は今週。
    """
    params = {}
    if week_start:
        params["week_start"] = week_start
    return await api_get("/api/v1/dashboard/weekly", params=params if params else None)


@mcp.tool()
async def get_kanban_view(project_id: Optional[int] = None) -> dict:
    """カンバンビューを取得します。タスクをTodo/Doing/Waiting/Doneのステータス別に表示します。

    Args:
        project_id: プロジェクトIDでフィルタリング（オプション）
    """
    params = {}
    if project_id:
        params["project_id"] = project_id
    return await api_get("/api/v1/dashboard/kanban", params=params if params else None)


@mcp.tool()
async def get_projects(is_active: Optional[bool] = None) -> dict:
    """プロジェクト一覧を取得します。アクティブ/非アクティブでフィルタリング可能です。

    Args:
        is_active: アクティブなプロジェクトのみ取得する場合はtrue
    """
    params = {}
    if is_active is not None:
        params["is_active"] = str(is_active).lower()
    return await api_get("/api/v1/projects", params=params if params else None)


@mcp.tool()
async def get_genres() -> dict:
    """ジャンル一覧を取得します。タスク作成時にジャンルを指定する際に参照してください。

    Returns:
        ジャンル一覧（id, name, color）
    """
    return await api_get("/api/v1/genres")


@mcp.tool()
async def create_genre(name: str, color: str) -> dict:
    """新しいジャンルを作成します。

    Args:
        name: ジャンル名（例: リサーチ、コーディング、執筆）
        color: 表示色（#RRGGBB形式、例: #3B82F6）
    """
    return await api_post("/api/v1/genres", json={"name": name, "color": color})


@mcp.tool()
async def get_task_detail(task_id: int) -> dict:
    """タスクの詳細情報を取得します。依存関係、時間記録、スケジュールを含みます。

    Args:
        task_id: タスクID
    """
    return await api_get(f"/api/v1/tasks/{task_id}")


# ===== Timer Tools =====

@mcp.tool()
async def start_timer(task_id: Optional[int] = None, task_name: Optional[str] = None) -> dict:
    """タスクのタイマーを開始します。別のタイマーが稼働中の場合は自動停止します。

    Args:
        task_id: タスクID
        task_name: タスク名（部分一致で検索）
    """
    if not task_id and not task_name:
        return {"error": "Either task_id or task_name is required"}

    json_data = {}
    if task_id:
        json_data["task_id"] = task_id
    if task_name:
        json_data["task_name"] = task_name

    return await api_post("/api/v1/workflow/timer/start", json=json_data)


@mcp.tool()
async def stop_timer(note: Optional[str] = None) -> dict:
    """稼働中のタイマーを停止します。

    Args:
        note: 作業メモ（オプション）
    """
    json_data = {}
    if note:
        json_data["note"] = note
    return await api_post("/api/v1/workflow/timer/stop", json=json_data)


# ===== Task Tools =====

@mcp.tool()
async def create_task(
    name: str,
    description: str,
    project_id: Optional[int] = None,
    genre_id: Optional[int] = None,
    estimated_hours: Optional[float] = None,
    priority: Optional[str] = None,
    want_level: Optional[str] = None,
    deadline: Optional[str] = None,
) -> dict:
    """新しいタスクを作成します。

    Args:
        name: タスク名
        description: タスクの詳細説明（Markdown対応）
        project_id: プロジェクトID
        genre_id: ジャンルID
        estimated_hours: 見積もり時間（時間単位）
        priority: 優先度（高/中/低）
        want_level: やりたい度（高/中/低）
        deadline: 締め切り（ISO 8601形式）
    """
    json_data = {"name": name, "description": description}
    if project_id is not None:
        json_data["project_id"] = project_id
    if genre_id is not None:
        json_data["genre_id"] = genre_id
    if estimated_hours is not None:
        json_data["estimated_hours"] = estimated_hours
    if priority is not None:
        json_data["priority"] = priority
    if want_level is not None:
        json_data["want_level"] = want_level
    if deadline is not None:
        json_data["deadline"] = deadline

    return await api_post("/api/v1/tasks", json=json_data)


@mcp.tool()
async def update_task(
    task_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    project_id: Optional[int] = None,
    genre_id: Optional[int] = None,
    estimated_hours: Optional[float] = None,
    priority: Optional[str] = None,
    want_level: Optional[str] = None,
    deadline: Optional[str] = None,
    note: Optional[str] = None,
) -> dict:
    """既存のタスクを更新します。

    Args:
        task_id: タスクID
        name: タスク名
        description: タスクの詳細説明（Markdown対応）
        status: ステータス（todo/doing/waiting/done/archive）
        project_id: プロジェクトID
        genre_id: ジャンルID
        estimated_hours: 見積もり時間
        priority: 優先度（高/中/低）
        want_level: やりたい度（高/中/低）
        deadline: 締め切り
        note: メモ
    """
    json_data = {}
    if name is not None:
        json_data["name"] = name
    if description is not None:
        json_data["description"] = description
    if status is not None:
        json_data["status"] = status
    if project_id is not None:
        json_data["project_id"] = project_id
    if genre_id is not None:
        json_data["genre_id"] = genre_id
    if estimated_hours is not None:
        json_data["estimated_hours"] = estimated_hours
    if priority is not None:
        json_data["priority"] = priority
    if want_level is not None:
        json_data["want_level"] = want_level
    if deadline is not None:
        json_data["deadline"] = deadline
    if note is not None:
        json_data["note"] = note

    return await api_patch(f"/api/v1/tasks/{task_id}", json=json_data)


@mcp.tool()
async def complete_task(task_id: int) -> dict:
    """タスクを完了状態にします。

    Args:
        task_id: タスクID
    """
    return await api_patch(f"/api/v1/tasks/{task_id}", json={"status": "done"})


@mcp.tool()
async def breakdown_task(
    task_id: int,
    subtasks: list[dict],
    reason: Optional[str] = None,
) -> dict:
    """タスクを複数のサブタスクに分解します。元のタスクはアーカイブされます。

    Args:
        task_id: 分解するタスクID
        subtasks: サブタスクのリスト（各要素は{name, estimated_hours?, genre_id?}）
        reason: 分解理由
    """
    json_data = {
        "task_id": task_id,
        "subtasks": subtasks,
        "archive_original": True,
    }
    if reason:
        json_data["reason"] = reason

    return await api_post("/api/v1/workflow/tasks/breakdown", json=json_data)


@mcp.tool()
async def merge_tasks(
    task_ids: list[int],
    merged_name: str,
    reason: Optional[str] = None,
) -> dict:
    """複数のタスクを1つに統合します。元のタスクはアーカイブされます。

    Args:
        task_ids: 統合するタスクIDのリスト（2つ以上）
        merged_name: 統合後のタスク名
        reason: 統合理由
    """
    json_data = {
        "task_ids": task_ids,
        "merged_task": {"name": merged_name},
    }
    if reason:
        json_data["reason"] = reason

    return await api_post("/api/v1/workflow/tasks/merge", json=json_data)


@mcp.tool()
async def add_task_dependency(task_id: int, depends_on_task_id: int) -> dict:
    """タスク間の依存関係を追加します。task_idがdepends_on_task_idの完了を待つ関係になります。循環依存は自動検出されエラーになります。

    Args:
        task_id: 依存元のタスクID（待つ側）
        depends_on_task_id: 依存先のタスクID（先に完了すべき側）
    """
    return await api_post(f"/api/v1/tasks/{task_id}/dependencies", json={"depends_on_task_id": depends_on_task_id})


@mcp.tool()
async def remove_task_dependency(task_id: int, depends_on_task_id: int) -> dict:
    """タスク間の依存関係を削除します。

    Args:
        task_id: 依存元のタスクID
        depends_on_task_id: 依存先のタスクID
    """
    try:
        response = await http_client.delete(f"/api/v1/tasks/{task_id}/dependencies/{depends_on_task_id}")
        response.raise_for_status()
        return {"message": "Dependency removed successfully"}
    except httpx.HTTPStatusError as e:
        return {"error": f"API error: {e.response.status_code}", "detail": e.response.text}
    except Exception as e:
        return {"error": str(e)}


# ===== Project Tool =====

@mcp.tool()
async def create_project(
    name: str,
    description: str,
    deadline: Optional[str] = None,
) -> dict:
    """新しいプロジェクトを作成します。

    Args:
        name: プロジェクト名
        description: プロジェクトの詳細説明（Markdown対応）
        deadline: 締め切り
    """
    json_data = {"name": name, "description": description}
    if deadline:
        json_data["deadline"] = deadline

    return await api_post("/api/v1/projects", json=json_data)


# ===== Schedule Tools =====

@mcp.tool()
async def generate_weekly_schedule(
    week_start: Optional[str] = None,
    daily_hours: Optional[dict] = None,
    fixed_events: Optional[list[dict]] = None,
) -> dict:
    """AIによる週間スケジュール自動生成。タスクの優先度・締切・依存関係を考慮して最適なスケジュールを生成します。

    Args:
        week_start: 週の開始日（YYYY-MM-DD形式）。省略時は次の月曜日。
        daily_hours: 曜日別の作業可能時間（例: {"mon": 6, "tue": 6, "wed": 4, ...}）
        fixed_events: 固定予定のリスト（例: [{"date": "2025-01-14", "start_time": "14:00", "end_time": "16:00", "title": "ミーティング"}]）
    """
    from datetime import datetime, timedelta

    # Calculate next Monday if week_start not provided
    if not week_start:
        today = datetime.now().date()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)
        week_start = next_monday.isoformat()

    json_data = {
        "week_start": week_start,
        "preferences": {},
        "fixed_events": fixed_events or [],
        "clear_existing": True,
    }

    if daily_hours:
        json_data["preferences"]["daily_hours"] = daily_hours

    return await api_post("/api/v1/workflow/schedule/generate-weekly", json=json_data)


@mcp.tool()
async def reschedule(
    date: str,
    reason: Optional[str] = None,
    blocked_times: Optional[list[dict]] = None,
) -> dict:
    """特定の日のスケジュールを再生成（未実装）。

    Args:
        date: 再スケジュールする日付（YYYY-MM-DD形式）
        reason: 再スケジュール理由
        blocked_times: ブロックする時間帯のリスト
    """
    return {
        "error": "Not implemented",
        "message": "リスケジュール機能は未実装です。週間スケジュール生成を使用してください。",
    }


# Run server
if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8001)
