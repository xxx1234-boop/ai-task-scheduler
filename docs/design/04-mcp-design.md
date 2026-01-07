# 研究時間管理システム MCP設計書

## 1. 概要

### 1.1 目的

本設計書は、研究時間管理システムのMCP（Model Context Protocol）サーバー設計を定義する。

### 1.2 MCPとは

MCPはClaude.aiが外部APIを呼び出すためのプロトコル。Claude.ai Integrationsを通じて、自然言語でシステムを操作可能にする。

### 1.3 設計方針

- **既存API活用**: MCPはREST APIのラッパーとして機能
- **サービス層呼び出し**: ビジネスロジックは既存サービス層に集約
- **SSE通信**: Server-Sent Eventsで常時接続を維持
- **認証連携**: Cloudflare Access経由で認証

---

## 2. アーキテクチャ

### 2.1 全体構成

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude.ai                              │
│  ユーザー: 「今日の予定を見せて」                            │
│      ↓                                                      │
│  Claude: get_today_schedule ツールを呼び出し                │
└─────────────────────────┬───────────────────────────────────┘
                          │ MCP over SSE (HTTPS)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Cloudflare Tunnel                                          │
│  https://research-tracker.your-domain.com/mcp/sse           │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Server                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  MCP Server                                            │ │
│  │  - ツール定義（JSON Schema）                            │ │
│  │  - ツール実行ハンドラ                                   │ │
│  │  - SSEストリーミング                                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                          ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  サービス層                                            │ │
│  │  - TimerService                                        │ │
│  │  - TaskService                                         │ │
│  │  - ScheduleService                                     │ │
│  │  - ProjectService                                      │ │
│  │  - DashboardService                                    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 通信フロー

```
Claude.ai                    FastAPI Server
    │                              │
    │──── GET /mcp/sse ───────────>│  SSE接続確立
    │<─── event: open ─────────────│
    │<─── event: tools ────────────│  ツール一覧送信
    │                              │
    │  ... 接続維持 ...            │
    │                              │
    │──── POST /mcp/messages ─────>│  ツール呼び出し
    │     {type: "tool_call",      │
    │      name: "start_timer",    │
    │      arguments: {...}}       │
    │<─── {type: "tool_result",    │  実行結果
    │      content: {...}} ────────│
    │                              │
```

---

## 3. MCPエンドポイント

### 3.1 エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/mcp/sse` | SSE接続（Claude.ai Integrations用） |
| POST | `/mcp/messages` | ツール呼び出し処理 |

### 3.2 GET /mcp/sse

Claude.aiとのSSE接続を確立する。

**レスポンス（SSEストリーム）:**

```
event: open
data: {"status": "connected"}

event: tools
data: {"tools": [...]}
```

### 3.3 POST /mcp/messages

ツール呼び出しリクエストを処理する。

**リクエスト（ツール呼び出し）:**

```json
{
  "type": "tool_call",
  "name": "start_timer",
  "arguments": {
    "task_name": "先行研究調査"
  }
}
```

**レスポンス:**

```json
{
  "type": "tool_result",
  "name": "start_timer",
  "content": {
    "result": {
      "time_entry_id": 5,
      "task_id": 1,
      "task_name": "先行研究調査",
      "start_time": "2025-01-07T09:00:00Z"
    }
  }
}
```

**リクエスト（ツール一覧取得）:**

```json
{
  "type": "list_tools"
}
```

**レスポンス:**

```json
{
  "type": "tools",
  "tools": [...]
}
```

---

## 4. MCPツール定義

### 4.1 ツール一覧

| カテゴリ | ツール名 | 説明 | 対応API |
|---------|---------|------|--------|
| **参照** | `get_today_schedule` | 今日のスケジュール | GET `/api/v1/dashboard/today` |
| | `get_week_schedule` | 週間スケジュール | GET `/api/v1/dashboard/weekly` |
| | `get_kanban_view` | カンバンデータ | GET `/api/v1/dashboard/kanban` |
| | `get_projects` | プロジェクト一覧 | GET `/api/v1/projects` |
| | `get_task_detail` | タスク詳細 | GET `/api/v1/tasks/{id}` |
| | `get_summary` | 全体サマリー | GET `/api/v1/dashboard/summary` |
| | `get_timer_status` | タイマー状態 | GET `/api/v1/workflow/timer/status` |
| **タイマー** | `start_timer` | タイマー開始 | POST `/api/v1/workflow/timer/start` |
| | `stop_timer` | タイマー停止 | POST `/api/v1/workflow/timer/stop` |
| **タスク** | `create_task` | タスク作成 | POST `/api/v1/tasks` |
| | `update_task` | タスク更新 | PATCH `/api/v1/tasks/{id}` |
| | `complete_task` | タスク完了 | POST `/api/v1/workflow/tasks/complete` |
| | `breakdown_task` | タスク分解 | POST `/api/v1/workflow/tasks/breakdown` |
| | `merge_tasks` | タスク統合 | POST `/api/v1/workflow/tasks/merge` |
| **プロジェクト** | `create_project` | プロジェクト作成 | POST `/api/v1/projects` |
| **スケジュール** | `generate_weekly_schedule` | 週次スケジュール生成 | POST `/api/v1/workflow/schedule/generate-weekly` |
| | `reschedule` | リスケジュール | POST `/api/v1/workflow/schedule/reschedule` |

### 4.2 ツール定義詳細（JSON Schema）

#### 4.2.1 参照系ツール

**get_today_schedule**

```json
{
  "name": "get_today_schedule",
  "description": "今日のスケジュールを取得する。予定、実績、実行中のタイマーを含む。",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

**get_week_schedule**

```json
{
  "name": "get_week_schedule",
  "description": "指定した週のスケジュールを取得する。日別の予定・実績、プロジェクト別・ジャンル別の集計を含む。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "week_start": {
        "type": "string",
        "format": "date",
        "description": "週の開始日（YYYY-MM-DD形式）。省略時は今週。"
      }
    },
    "required": []
  }
}
```

**get_kanban_view**

```json
{
  "name": "get_kanban_view",
  "description": "カンバン形式でタスク一覧を取得する。Todo/Doing/Waiting/Doneの4列で表示。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "project_id": {
        "type": "integer",
        "description": "プロジェクトIDでフィルタ（省略時は全プロジェクト）"
      }
    },
    "required": []
  }
}
```

**get_projects**

```json
{
  "name": "get_projects",
  "description": "プロジェクト一覧を取得する。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "status": {
        "type": "string",
        "enum": ["active", "completed", "archived"],
        "description": "ステータスでフィルタ"
      }
    },
    "required": []
  }
}
```

**get_task_detail**

```json
{
  "name": "get_task_detail",
  "description": "タスクの詳細情報を取得する。依存関係、子タスク、時間記録を含む。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_id": {
        "type": "integer",
        "description": "タスクID"
      }
    },
    "required": ["task_id"]
  }
}
```

**get_summary**

```json
{
  "name": "get_summary",
  "description": "全体のサマリーを取得する。今日・今週の進捗、緊急タスク、タイマー状態を含む。",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

**get_timer_status**

```json
{
  "name": "get_timer_status",
  "description": "現在のタイマー状態を取得する。実行中のタスク、経過時間を含む。",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

#### 4.2.2 タイマー操作ツール

**start_timer**

```json
{
  "name": "start_timer",
  "description": "タスクのタイマーを開始する。既に実行中のタイマーがあれば自動停止する。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_id": {
        "type": "integer",
        "description": "タスクID"
      },
      "task_name": {
        "type": "string",
        "description": "タスク名（部分一致で検索）。task_idが指定されていない場合に使用。"
      }
    },
    "required": []
  }
}
```

**stop_timer**

```json
{
  "name": "stop_timer",
  "description": "実行中のタイマーを停止する。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "note": {
        "type": "string",
        "description": "作業メモ（任意）"
      }
    },
    "required": []
  }
}
```

#### 4.2.3 タスク操作ツール

**create_task**

```json
{
  "name": "create_task",
  "description": "新しいタスクを作成する。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {
        "type": "string",
        "description": "タスク名"
      },
      "project_id": {
        "type": "integer",
        "description": "プロジェクトID"
      },
      "genre_id": {
        "type": "integer",
        "description": "ジャンルID（1:リサーチ, 2:コーディング, 3:執筆, 4:ミーティング, 5:レビュー, 6:実験, 7:データ分析, 8:その他）"
      },
      "estimated_hours": {
        "type": "number",
        "description": "見積もり時間（時間単位）"
      },
      "priority": {
        "type": "string",
        "enum": ["高", "中", "低"],
        "description": "優先度"
      },
      "want_level": {
        "type": "string",
        "enum": ["高", "中", "低"],
        "description": "やりたい度"
      },
      "deadline": {
        "type": "string",
        "format": "date-time",
        "description": "締切日時"
      }
    },
    "required": ["name"]
  }
}
```

**update_task**

```json
{
  "name": "update_task",
  "description": "タスクを更新する。見積もり、優先度、ステータスなどを変更。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_id": {
        "type": "integer",
        "description": "タスクID"
      },
      "name": {
        "type": "string",
        "description": "タスク名"
      },
      "estimated_hours": {
        "type": "number",
        "description": "見積もり時間"
      },
      "priority": {
        "type": "string",
        "enum": ["高", "中", "低"],
        "description": "優先度"
      },
      "want_level": {
        "type": "string",
        "enum": ["高", "中", "低"],
        "description": "やりたい度"
      },
      "status": {
        "type": "string",
        "enum": ["todo", "doing", "waiting", "done"],
        "description": "ステータス"
      },
      "deadline": {
        "type": "string",
        "format": "date-time",
        "description": "締切日時"
      },
      "note": {
        "type": "string",
        "description": "メモ"
      }
    },
    "required": ["task_id"]
  }
}
```

**complete_task**

```json
{
  "name": "complete_task",
  "description": "タスクを完了にする。実行中タイマーの停止、スケジュールの完了処理も行う。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_id": {
        "type": "integer",
        "description": "タスクID"
      }
    },
    "required": ["task_id"]
  }
}
```

**breakdown_task**

```json
{
  "name": "breakdown_task",
  "description": "タスクを複数のサブタスクに分解する。元タスクはアーカイブされる。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_id": {
        "type": "integer",
        "description": "分解するタスクのID"
      },
      "subtasks": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": {
              "type": "string",
              "description": "サブタスク名"
            },
            "estimated_hours": {
              "type": "number",
              "description": "見積もり時間"
            },
            "genre_id": {
              "type": "integer",
              "description": "ジャンルID"
            }
          },
          "required": ["name"]
        },
        "description": "作成するサブタスクのリスト"
      },
      "reason": {
        "type": "string",
        "description": "分解の理由"
      }
    },
    "required": ["task_id", "subtasks"]
  }
}
```

**merge_tasks**

```json
{
  "name": "merge_tasks",
  "description": "複数のタスクを1つに統合する。元タスクはアーカイブされる。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_ids": {
        "type": "array",
        "items": {
          "type": "integer"
        },
        "description": "統合するタスクIDのリスト"
      },
      "merged_name": {
        "type": "string",
        "description": "統合後のタスク名"
      },
      "reason": {
        "type": "string",
        "description": "統合の理由"
      }
    },
    "required": ["task_ids", "merged_name"]
  }
}
```

#### 4.2.4 プロジェクト操作ツール

**create_project**

```json
{
  "name": "create_project",
  "description": "新しいプロジェクトを作成する。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {
        "type": "string",
        "description": "プロジェクト名"
      },
      "description": {
        "type": "string",
        "description": "説明"
      },
      "goal": {
        "type": "string",
        "description": "目標"
      },
      "deadline": {
        "type": "string",
        "format": "date",
        "description": "締切日"
      }
    },
    "required": ["name"]
  }
}
```

#### 4.2.5 スケジュール操作ツール

**generate_weekly_schedule**

```json
{
  "name": "generate_weekly_schedule",
  "description": "週次スケジュールを自動生成する。タスクの優先度、締切、依存関係を考慮して最適化。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "week_start": {
        "type": "string",
        "format": "date",
        "description": "週の開始日（省略時は次の月曜）"
      },
      "sync_to_gcal": {
        "type": "boolean",
        "description": "Google Calendarに同期するか"
      }
    },
    "required": []
  }
}
```

**reschedule**

```json
{
  "name": "reschedule",
  "description": "特定日のスケジュールをリスケジュールする。予定変更や急な割り込み時に使用。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "date": {
        "type": "string",
        "format": "date",
        "description": "リスケジュールする日付"
      },
      "reason": {
        "type": "string",
        "description": "リスケジュールの理由"
      },
      "blocked_times": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "start": {
              "type": "string",
              "description": "開始時刻（HH:MM形式）"
            },
            "end": {
              "type": "string",
              "description": "終了時刻（HH:MM形式）"
            }
          }
        },
        "description": "ブロックする時間帯"
      }
    },
    "required": ["date"]
  }
}
```

---

## 5. 実装詳細

### 5.1 ディレクトリ構成

```
app/
├── main.py
├── config.py
├── database.py
├── dependencies.py              # get_mcp_server など
├── routers/
│   ├── mcp.py                   # MCPエンドポイント
│   ├── projects.py
│   ├── tasks.py
│   └── ...
├── mcp/
│   ├── __init__.py
│   ├── server.py                # MCPServer クラス
│   └── tools.py                 # ツール定義（JSON Schema）
├── services/
│   ├── timer_service.py
│   ├── task_service.py
│   ├── schedule_service.py
│   ├── project_service.py
│   └── dashboard_service.py
└── models/
    └── ...
```

### 5.2 MCPServer クラス

```python
# app/mcp/server.py

from typing import Any
from app.mcp.tools import MCP_TOOLS


class MCPServer:
    """MCP (Model Context Protocol) サーバー"""
    
    def __init__(
        self,
        timer_service: TimerService,
        task_service: TaskService,
        schedule_service: ScheduleService,
        project_service: ProjectService,
        dashboard_service: DashboardService,
    ):
        self.timer_service = timer_service
        self.task_service = task_service
        self.schedule_service = schedule_service
        self.project_service = project_service
        self.dashboard_service = dashboard_service
        
        # ツール名 → ハンドラのマッピング
        self.tool_handlers = {
            "get_today_schedule": self._handle_get_today_schedule,
            "get_week_schedule": self._handle_get_week_schedule,
            "get_kanban_view": self._handle_get_kanban_view,
            "get_projects": self._handle_get_projects,
            "get_task_detail": self._handle_get_task_detail,
            "get_summary": self._handle_get_summary,
            "get_timer_status": self._handle_get_timer_status,
            "start_timer": self._handle_start_timer,
            "stop_timer": self._handle_stop_timer,
            "create_task": self._handle_create_task,
            "update_task": self._handle_update_task,
            "complete_task": self._handle_complete_task,
            "breakdown_task": self._handle_breakdown_task,
            "merge_tasks": self._handle_merge_tasks,
            "create_project": self._handle_create_project,
            "generate_weekly_schedule": self._handle_generate_weekly_schedule,
            "reschedule": self._handle_reschedule,
        }

    def get_tools(self) -> list[dict]:
        """利用可能なツール一覧を返す"""
        return MCP_TOOLS

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """ツールを実行する"""
        handler = self.tool_handlers.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}
        
        try:
            result = await handler(arguments)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

    # ========== ハンドラ実装 ==========
    
    async def _handle_get_today_schedule(self, args: dict) -> dict:
        return await self.dashboard_service.get_today()

    async def _handle_start_timer(self, args: dict) -> dict:
        task_id = args.get("task_id")
        task_name = args.get("task_name")
        return await self.timer_service.start(task_id=task_id, task_name=task_name)

    # ... 他のハンドラも同様に実装
```

### 5.3 SSEエンドポイント

```python
# app/routers/mcp.py

import json
import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse

from app.mcp.server import MCPServer
from app.dependencies import get_mcp_server

router = APIRouter(prefix="/mcp", tags=["MCP"])


async def sse_generator(
    request: Request,
    mcp_server: MCPServer
) -> AsyncGenerator[str, None]:
    """SSEストリームを生成する"""
    
    # 接続確立メッセージ
    yield f"event: open\ndata: {json.dumps({'status': 'connected'})}\n\n"
    
    # ツール一覧を送信
    tools = mcp_server.get_tools()
    yield f"event: tools\ndata: {json.dumps({'tools': tools})}\n\n"
    
    # クライアントからの切断を待機
    try:
        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass


@router.get("/sse")
async def mcp_sse(
    request: Request,
    mcp_server: MCPServer = Depends(get_mcp_server)
) -> StreamingResponse:
    """MCP over SSE エンドポイント"""
    return StreamingResponse(
        sse_generator(request, mcp_server),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/messages")
async def mcp_messages(
    request: Request,
    mcp_server: MCPServer = Depends(get_mcp_server)
) -> dict:
    """MCPメッセージ処理エンドポイント"""
    body = await request.json()
    
    message_type = body.get("type")
    
    if message_type == "tool_call":
        tool_name = body.get("name")
        arguments = body.get("arguments", {})
        result = await mcp_server.call_tool(tool_name, arguments)
        return {
            "type": "tool_result",
            "name": tool_name,
            "content": result
        }
    
    elif message_type == "list_tools":
        return {
            "type": "tools",
            "tools": mcp_server.get_tools()
        }
    
    else:
        return {
            "type": "error",
            "error": f"Unknown message type: {message_type}"
        }
```

---

## 6. Claude.ai Integrations設定

### 6.1 設定手順

1. **Cloudflare Tunnel設定**
   - FastAPIサーバーを公開
   - URL: `https://research-tracker.your-domain.com`

2. **Claude.ai Integrations登録**
   - Name: `Research Time Tracker`
   - URL: `https://research-tracker.your-domain.com/mcp/sse`
   - Authentication: Bearer Token（オプション）

3. **動作確認**
   - Claude.aiで「今日の予定を見せて」と入力
   - `get_today_schedule` ツールが呼び出されることを確認

### 6.2 認証設定

Cloudflare Accessを使用して追加の認証レイヤーを設定可能。

```yaml
# Cloudflare Access設定例
Application:
  Name: Research Tracker MCP
  Domain: research-tracker.your-domain.com/mcp/*
  
Policy:
  - Allow: Email ends with @your-domain.com
  - Allow: Service Token (for Claude.ai)
```

---

## 7. 会話例

### 7.1 今日の予定確認

```
ユーザー: 今日の予定を見せて

Claude: [get_today_schedule を呼び出し]

📅 今日のスケジュール (2025-01-07)

⏱️ 実行中: 先行研究調査 (35分経過)

┌──────────────┬─────────────────────┬─────────────┬────┐
│ 時間         │ タスク              │ プロジェクト │ 状態│
├──────────────┼─────────────────────┼─────────────┼────┤
│ 09:00-12:00  │ 先行研究調査        │ 卒業論文    │ ✅ │
│ 13:00-15:00  │ 実験設計            │ 卒業論文    │ ⬜ │
│ 15:00-17:00  │ コードレビュー      │ 授業課題    │ ⬜ │
└──────────────┴─────────────────────┴─────────────┴────┘

予定: 6.0h | 実績: 2.5h | 残り: 3.5h
```

### 7.2 タイマー操作

```
ユーザー: 実験設計始める

Claude: [start_timer を呼び出し: task_name="実験設計"]

⏱️ タイマーを開始しました

タスク: 実験設計
プロジェクト: 卒業論文
開始時刻: 13:00

※「先行研究調査」のタイマーは自動停止しました（95分）
```

```
ユーザー: 終わり

Claude: [stop_timer を呼び出し]

⏹️ タイマーを停止しました

タスク: 実験設計
作業時間: 1時間45分
累計実績: 3.5h / 8h
```

### 7.3 タスク分解

```
ユーザー: 先行研究調査、思ったより大変。分解して

Claude: 先行研究調査を分解しますね。以下のように分けるのはどうでしょうか？

1. 国内論文サーベイ（5h）
2. 海外論文サーベイ（6h）  
3. サーベイまとめ作成（4h）

合計: 15h（元の見積もりと同じ）

この内容で分解しますか？

ユーザー: OK

Claude: [breakdown_task を呼び出し]

✅ タスクを分解しました

元タスク: 先行研究調査 → アーカイブ

新タスク:
├─ 国内論文サーベイ (5h) - ID: 7
├─ 海外論文サーベイ (6h) - ID: 8
└─ サーベイまとめ作成 (4h) - ID: 9
   └─ 依存: 国内論文、海外論文の完了後

実績時間（3.5h）は国内論文サーベイに引き継ぎました。
```

### 7.4 週次スケジュール生成

```
ユーザー: 来週のスケジュールを作って

Claude: [generate_weekly_schedule を呼び出し]

📅 来週のスケジュール (1/13 - 1/19)

月曜日 (1/13) - 6h
├─ 09:00-12:00 国内論文サーベイ [卒業論文]
└─ 13:00-16:00 海外論文サーベイ [卒業論文]

火曜日 (1/14) - 6h
├─ 09:00-12:00 海外論文サーベイ [卒業論文]
└─ 14:00-16:00 ゼミ [固定予定]

水曜日 (1/15) - 4h
└─ 09:00-13:00 サーベイまとめ作成 [卒業論文]

...

📊 サマリー
・予定合計: 28.5h
・卒業論文: 20h (70%)
・授業課題: 8.5h (30%)

⚠️ 警告
・「実験実施」は締切(1/25)に間に合わない可能性があります

Google Calendarに同期しますか？
```

---

## 8. エラーハンドリング

### 8.1 エラーレスポンス形式

```json
{
  "type": "tool_result",
  "name": "start_timer",
  "content": {
    "error": "Task not found: 先行研究"
  }
}
```

### 8.2 主なエラーケース

| エラー | 説明 | 対処 |
|--------|------|------|
| `Unknown tool` | 存在しないツール | ツール名を確認 |
| `Task not found` | タスクが見つからない | task_idまたはtask_nameを確認 |
| `Timer not running` | タイマーが実行中でない | start_timerを先に実行 |
| `Dependency cycle` | 依存関係が循環 | 依存関係を見直し |
| `Database error` | DB接続エラー | サーバー状態を確認 |

---

## 9. セキュリティ考慮事項

### 9.1 認証

- Cloudflare Tunnelで公開
- Cloudflare Accessでアクセス制限
- Bearer Tokenによる追加認証（オプション）

### 9.2 認可

- 現状はシングルユーザー想定
- 将来的にマルチユーザー対応時はトークンにユーザーIDを含める

### 9.3 レート制限

- FastAPIミドルウェアでレート制限を実装
- 目安: 60リクエスト/分

---

## 更新履歴

| 日付 | バージョン | 内容 |
|------|------------|------|
| 2025-01-07 | 1.0 | 初版作成 |
