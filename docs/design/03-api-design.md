# 研究時間管理システム API設計書

## 1. 概要

### 1.1 目的

本設計書は、研究時間管理システムのREST API設計を定義する。

### 1.2 設計方針

- **RESTful**: CRUD操作はREST原則に従う
- **ワークフロー分離**: ビジネスロジックを含む操作は専用エンドポイントに分離
- **MCP対応**: Claude.ai Integrations用のMCPツールを提供

### 1.3 API構成

| カテゴリ | ベースパス | 用途 |
|---------|-----------|------|
| **CRUD** | `/api/v1/{resource}` | 基本的なデータ操作 |
| **ワークフロー** | `/api/v1/workflow/*` | ビジネスロジックを含む操作 |
| **ダッシュボード** | `/api/v1/dashboard/*` | 集計・表示用（読み取り専用） |
| **同期** | `/api/v1/sync/*` | 外部サービス連携 |
| **MCP** | `/mcp/*` | Claude.ai Integrations用 |

### 1.4 共通仕様

#### リクエストヘッダー

```
Content-Type: application/json
Authorization: Bearer {token}  # 認証が必要な場合
```

#### レスポンス形式

```json
// 成功時（単一リソース）
{
  "id": 1,
  "name": "タスク名",
  ...
}

// 成功時（リスト）
{
  "items": [...],
  "total": 100
}

// エラー時
{
  "error": {
    "code": "ERROR_CODE",
    "message": "エラーメッセージ",
    "details": {}
  }
}
```

#### HTTPステータスコード

| コード | 説明 |
|--------|------|
| 200 | 成功 |
| 201 | 作成成功 |
| 400 | リクエスト不正 |
| 404 | リソースなし |
| 409 | 競合 |
| 422 | バリデーションエラー |
| 500 | サーバーエラー |

---

## 2. CRUD API

### 2.1 Projects（プロジェクト）

#### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/projects` | 一覧取得 |
| GET | `/api/v1/projects/{id}` | 詳細取得 |
| POST | `/api/v1/projects` | 作成 |
| PUT | `/api/v1/projects/{id}` | 全体更新 |
| PATCH | `/api/v1/projects/{id}` | 部分更新 |
| DELETE | `/api/v1/projects/{id}` | 削除（論理削除） |

#### GET /api/v1/projects

プロジェクト一覧を取得する。

**クエリパラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| status | string | No | active, completed, archived |
| sort | string | No | deadline, created_at, name |
| order | string | No | asc, desc（デフォルト: desc） |

**レスポンス例:**

```json
{
  "items": [
    {
      "id": 1,
      "name": "卒業論文",
      "description": "〇〇に関する研究",
      "goal": "3月末に提出",
      "deadline": "2025-03-31",
      "status": "active",
      "created_at": "2025-01-07T10:00:00Z",
      "updated_at": "2025-01-07T10:00:00Z",
      "task_count": 6,
      "completed_task_count": 2,
      "total_estimated_hours": 90.0,
      "total_actual_hours": 25.5
    }
  ],
  "total": 5
}
```

#### POST /api/v1/projects

プロジェクトを作成する。

**リクエストボディ:**

```json
{
  "name": "卒業論文",
  "description": "〇〇に関する研究",
  "goal": "3月末に提出",
  "deadline": "2025-03-31"
}
```

**レスポンス:** 201 Created

```json
{
  "id": 1,
  "name": "卒業論文",
  "description": "〇〇に関する研究",
  "goal": "3月末に提出",
  "deadline": "2025-03-31",
  "status": "active",
  "created_at": "2025-01-07T10:00:00Z",
  "updated_at": "2025-01-07T10:00:00Z"
}
```

#### PATCH /api/v1/projects/{id}

プロジェクトを部分更新する。

**リクエストボディ:**

```json
{
  "status": "completed"
}
```

---

### 2.2 Tasks（タスク）

#### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/tasks` | 一覧取得 |
| GET | `/api/v1/tasks/{id}` | 詳細取得 |
| POST | `/api/v1/tasks` | 作成 |
| PUT | `/api/v1/tasks/{id}` | 全体更新 |
| PATCH | `/api/v1/tasks/{id}` | 部分更新 |
| DELETE | `/api/v1/tasks/{id}` | 削除（論理削除） |
| GET | `/api/v1/tasks/{id}/children` | 子タスク一覧 |
| GET | `/api/v1/tasks/{id}/history` | 操作履歴 |
| GET | `/api/v1/tasks/{id}/time-entries` | 時間記録一覧 |
| GET | `/api/v1/tasks/{id}/dependencies` | 依存関係取得 |
| POST | `/api/v1/tasks/{id}/dependencies` | 依存追加 |
| DELETE | `/api/v1/tasks/{id}/dependencies/{dep_id}` | 依存削除 |

#### GET /api/v1/tasks

タスク一覧を取得する。

**クエリパラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| project_id | integer | No | プロジェクトID |
| genre_id | integer | No | ジャンルID |
| status | string | No | todo, doing, waiting, done, archive |
| priority | string | No | 高, 中, 低 |
| parent_task_id | integer | No | 親タスクID（nullでトップレベル） |
| has_parent | boolean | No | true=子タスクのみ, false=トップレベルのみ |
| deadline_before | date | No | 締切日以前 |
| deadline_after | date | No | 締切日以降 |
| sort | string | No | deadline, priority, created_at, want_level |
| order | string | No | asc, desc |
| limit | integer | No | 取得件数（デフォルト: 50） |
| offset | integer | No | オフセット |

**レスポンス例:**

```json
{
  "items": [
    {
      "id": 1,
      "name": "先行研究調査",
      "project_id": 1,
      "project_name": "卒業論文",
      "genre_id": 1,
      "genre_name": "リサーチ",
      "genre_color": "#4A90D9",
      "status": "doing",
      "deadline": "2025-01-20T23:59:59Z",
      "estimated_hours": 15.0,
      "actual_hours": 3.5,
      "priority": "高",
      "want_level": "中",
      "recurrence": "なし",
      "is_splittable": true,
      "min_work_unit": 0.5,
      "parent_task_id": null,
      "decomposition_level": 0,
      "note": null,
      "created_at": "2025-01-07T10:00:00Z",
      "updated_at": "2025-01-07T15:30:00Z",
      "blocked_by_count": 0,
      "blocking_count": 3,
      "children_count": 0
    }
  ],
  "total": 25
}
```

#### POST /api/v1/tasks

タスクを作成する。

**リクエストボディ:**

```json
{
  "name": "先行研究調査",
  "project_id": 1,
  "genre_id": 1,
  "deadline": "2025-01-20T23:59:59Z",
  "estimated_hours": 15.0,
  "priority": "高",
  "want_level": "中",
  "parent_task_id": null,
  "depends_on_task_ids": []
}
```

#### GET /api/v1/tasks/{id}/dependencies

タスクの依存関係を取得する。

**レスポンス例:**

```json
{
  "depends_on": [
    {"id": 1, "name": "先行研究調査", "status": "done"}
  ],
  "blocking": [
    {"id": 3, "name": "実験実施", "status": "todo"},
    {"id": 4, "name": "結果分析", "status": "todo"}
  ]
}
```

#### POST /api/v1/tasks/{id}/dependencies

依存関係を追加する。

**リクエストボディ:**

```json
{
  "depends_on_task_id": 2
}
```

---

### 2.3 Genres（ジャンル）

#### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/genres` | 一覧取得 |
| GET | `/api/v1/genres/{id}` | 詳細取得 |
| POST | `/api/v1/genres` | 作成 |
| PUT | `/api/v1/genres/{id}` | 更新 |
| DELETE | `/api/v1/genres/{id}` | 削除 |

#### GET /api/v1/genres

**レスポンス例:**

```json
{
  "items": [
    {"id": 1, "name": "リサーチ", "color": "#4A90D9"},
    {"id": 2, "name": "コーディング", "color": "#50C878"},
    {"id": 3, "name": "執筆", "color": "#FFB347"},
    {"id": 4, "name": "ミーティング", "color": "#FF6B6B"},
    {"id": 5, "name": "レビュー", "color": "#DDA0DD"},
    {"id": 6, "name": "実験", "color": "#87CEEB"},
    {"id": 7, "name": "データ分析", "color": "#98D8C8"},
    {"id": 8, "name": "その他", "color": "#C0C0C0"}
  ]
}
```

---

### 2.4 Schedules（スケジュール）

#### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/schedules` | 一覧取得 |
| GET | `/api/v1/schedules/{id}` | 詳細取得 |
| POST | `/api/v1/schedules` | 作成 |
| PUT | `/api/v1/schedules/{id}` | 更新 |
| DELETE | `/api/v1/schedules/{id}` | 削除 |

#### GET /api/v1/schedules

**クエリパラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| date | date | No | 特定日 |
| date_from | date | No | 期間開始 |
| date_to | date | No | 期間終了 |
| task_id | integer | No | タスクID |
| project_id | integer | No | プロジェクトID |
| status | string | No | scheduled, completed, skipped |

**レスポンス例:**

```json
{
  "items": [
    {
      "id": 1,
      "task_id": 1,
      "task_name": "先行研究調査",
      "project_name": "卒業論文",
      "genre_name": "リサーチ",
      "genre_color": "#4A90D9",
      "date": "2025-01-13",
      "start_time": "09:00",
      "end_time": "12:00",
      "planned_hours": 3.0,
      "actual_hours": 2.5,
      "status": "completed",
      "gcal_event_id": "gcal_abc123"
    }
  ],
  "total": 15
}
```

---

### 2.5 Time Entries（時間記録）

#### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/time-entries` | 一覧取得 |
| GET | `/api/v1/time-entries/{id}` | 詳細取得 |
| POST | `/api/v1/time-entries` | 作成（手動記録） |
| PUT | `/api/v1/time-entries/{id}` | 更新 |
| DELETE | `/api/v1/time-entries/{id}` | 削除 |

#### GET /api/v1/time-entries

**クエリパラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| task_id | integer | No | タスクID |
| project_id | integer | No | プロジェクトID |
| date_from | datetime | No | 期間開始 |
| date_to | datetime | No | 期間終了 |
| is_running | boolean | No | true=実行中のみ |

**レスポンス例:**

```json
{
  "items": [
    {
      "id": 1,
      "task_id": 1,
      "task_name": "先行研究調査",
      "project_name": "卒業論文",
      "start_time": "2025-01-07T09:00:00Z",
      "end_time": "2025-01-07T10:35:00Z",
      "duration_minutes": 95,
      "note": null
    }
  ],
  "total": 50
}
```

#### POST /api/v1/time-entries

手動で時間記録を追加する。

**リクエストボディ:**

```json
{
  "task_id": 1,
  "start_time": "2025-01-06T14:00:00Z",
  "end_time": "2025-01-06T16:00:00Z",
  "note": "昨日の作業を記録"
}
```

---

### 2.6 Settings（設定）

#### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/settings` | 全設定取得 |
| GET | `/api/v1/settings/{key}` | 特定設定取得 |
| PUT | `/api/v1/settings/{key}` | 設定更新 |

#### GET /api/v1/settings

**レスポンス例:**

```json
{
  "items": [
    {
      "key": "weekly_available_hours",
      "value": {"mon": 6, "tue": 6, "wed": 4, "thu": 6, "fri": 6, "sat": 3, "sun": 0},
      "updated_at": "2025-01-07T10:00:00Z"
    },
    {
      "key": "default_work_hours",
      "value": {"start": "09:00", "end": "18:00", "lunch_start": "12:00", "lunch_end": "13:00"},
      "updated_at": "2025-01-07T10:00:00Z"
    }
  ]
}
```

---

## 3. ワークフローAPI

ビジネスロジックを含む複合操作。

### 3.1 タイマー操作

#### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/v1/workflow/timer/start` | タイマー開始 |
| POST | `/api/v1/workflow/timer/stop` | タイマー停止 |
| GET | `/api/v1/workflow/timer/status` | 現在の状態 |

#### POST /api/v1/workflow/timer/start

タイマーを開始する。実行中のタイマーがあれば自動停止。

**リクエストボディ:**

```json
{
  "task_id": 1
}
```

または名前で検索:

```json
{
  "task_name": "先行研究"
}
```

**レスポンス例:**

```json
{
  "time_entry_id": 5,
  "task_id": 1,
  "task_name": "先行研究調査",
  "project_name": "卒業論文",
  "start_time": "2025-01-07T09:00:00Z",
  "previous_entry": {
    "time_entry_id": 4,
    "task_name": "実験設計",
    "duration_minutes": 45,
    "stopped_at": "2025-01-07T09:00:00Z"
  }
}
```

#### POST /api/v1/workflow/timer/stop

実行中のタイマーを停止する。

**リクエストボディ:**

```json
{
  "note": "区切りのいいところまで完了"
}
```

**レスポンス例:**

```json
{
  "time_entry_id": 5,
  "task_id": 1,
  "task_name": "先行研究調査",
  "start_time": "2025-01-07T09:00:00Z",
  "end_time": "2025-01-07T10:35:00Z",
  "duration_minutes": 95,
  "task_actual_hours_total": 5.08
}
```

#### GET /api/v1/workflow/timer/status

現在のタイマー状態を取得する。

**レスポンス例（実行中）:**

```json
{
  "is_running": true,
  "current_entry": {
    "time_entry_id": 5,
    "task_id": 1,
    "task_name": "先行研究調査",
    "project_name": "卒業論文",
    "start_time": "2025-01-07T09:00:00Z",
    "elapsed_minutes": 35
  }
}
```

**レスポンス例（停止中）:**

```json
{
  "is_running": false,
  "current_entry": null,
  "last_entry": {
    "task_name": "実験設計",
    "end_time": "2025-01-07T08:15:00Z",
    "duration_minutes": 45
  }
}
```

---

### 3.2 タスク分解・統合

#### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/v1/workflow/tasks/breakdown` | タスク分解（1→多） |
| POST | `/api/v1/workflow/tasks/merge` | タスク統合（多→1） |
| POST | `/api/v1/workflow/tasks/bulk-create` | 一括作成 |

#### POST /api/v1/workflow/tasks/breakdown

タスクを複数のサブタスクに分解する。

**リクエストボディ:**

```json
{
  "task_id": 1,
  "subtasks": [
    {
      "name": "国内論文サーベイ",
      "estimated_hours": 5,
      "genre_id": 1
    },
    {
      "name": "海外論文サーベイ",
      "estimated_hours": 6,
      "genre_id": 1
    },
    {
      "name": "サーベイまとめ作成",
      "estimated_hours": 4,
      "genre_id": 3,
      "depends_on_indices": [0, 1]
    }
  ],
  "reason": "作業量が想定より多かった",
  "archive_original": true
}
```

**レスポンス例:**

```json
{
  "original_task": {
    "id": 1,
    "name": "先行研究調査",
    "status": "archive"
  },
  "created_tasks": [
    {"id": 7, "name": "国内論文サーベイ"},
    {"id": 8, "name": "海外論文サーベイ"},
    {"id": 9, "name": "サーベイまとめ作成"}
  ],
  "dependencies_transferred": 3,
  "history_id": 15
}
```

#### POST /api/v1/workflow/tasks/merge

複数のタスクを1つに統合する。

**リクエストボディ:**

```json
{
  "task_ids": [7, 8],
  "merged_task": {
    "name": "論文サーベイ（国内・海外）",
    "estimated_hours": 11,
    "genre_id": 1
  },
  "reason": "粒度が細かすぎた"
}
```

**レスポンス例:**

```json
{
  "merged_task": {
    "id": 10,
    "name": "論文サーベイ（国内・海外）",
    "estimated_hours": 11,
    "actual_hours": 3.5
  },
  "archived_tasks": [7, 8],
  "time_entries_transferred": 5,
  "history_id": 16
}
```

#### POST /api/v1/workflow/tasks/bulk-create

タスクを一括作成する（依存関係も同時に設定可能）。

**リクエストボディ:**

```json
{
  "project_id": 1,
  "tasks": [
    {
      "name": "先行研究調査",
      "genre_id": 1,
      "estimated_hours": 15,
      "priority": "高"
    },
    {
      "name": "実験設計",
      "genre_id": 2,
      "estimated_hours": 8,
      "priority": "高",
      "depends_on_indices": [0]
    }
  ]
}
```

**レスポンス例:**

```json
{
  "created_tasks": [
    {"id": 1, "name": "先行研究調査"},
    {"id": 2, "name": "実験設計"}
  ],
  "dependencies_created": 1
}
```

---

### 3.3 スケジュール生成

#### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/v1/workflow/schedule/generate-weekly` | 週次スケジュール生成 |
| POST | `/api/v1/workflow/schedule/generate-daily` | 日次スケジュール生成 |
| POST | `/api/v1/workflow/schedule/reschedule` | リスケジュール |
| POST | `/api/v1/workflow/schedule/complete` | スケジュール項目を完了 |

#### POST /api/v1/workflow/schedule/generate-weekly

週次スケジュールを自動生成する（Claude APIで最適化）。

**リクエストボディ:**

```json
{
  "week_start": "2025-01-13",
  "preferences": {
    "daily_hours": {
      "mon": 6, "tue": 6, "wed": 4, "thu": 6, "fri": 6, "sat": 3, "sun": 0
    },
    "focus_project_id": null,
    "avoid_context_switch": true
  },
  "fixed_events": [
    {
      "date": "2025-01-14",
      "start_time": "14:00",
      "end_time": "16:00",
      "title": "ゼミ"
    }
  ],
  "sync_to_gcal": true
}
```

**レスポンス例:**

```json
{
  "week_start": "2025-01-13",
  "week_end": "2025-01-19",
  "schedules": [
    {
      "id": 1,
      "date": "2025-01-13",
      "start_time": "09:00",
      "end_time": "12:00",
      "task_id": 1,
      "task_name": "先行研究調査",
      "project_name": "卒業論文",
      "planned_hours": 3.0,
      "gcal_event_id": "gcal_abc123"
    }
  ],
  "summary": {
    "total_planned_hours": 28.5,
    "by_project": [
      {"name": "卒業論文", "hours": 20.0},
      {"name": "授業課題", "hours": 8.5}
    ],
    "by_genre": [
      {"name": "リサーチ", "hours": 12.0},
      {"name": "コーディング", "hours": 10.0},
      {"name": "執筆", "hours": 6.5}
    ]
  },
  "warnings": [
    "タスク「実験実施」は締切(1/25)に間に合わない可能性があります"
  ]
}
```

#### POST /api/v1/workflow/schedule/reschedule

特定日のスケジュールをリスケジュールする。

**リクエストボディ:**

```json
{
  "date": "2025-01-14",
  "reason": "MTGが入った",
  "blocked_times": [
    {"start": "09:00", "end": "12:00"}
  ],
  "reschedule_to": "auto"
}
```

**レスポンス例:**

```json
{
  "cancelled_schedules": [
    {"id": 5, "task_name": "実験設計", "original_date": "2025-01-14"}
  ],
  "new_schedules": [
    {"id": 10, "task_name": "実験設計", "date": "2025-01-15", "start_time": "13:00"}
  ],
  "gcal_updated": true
}
```

#### POST /api/v1/workflow/schedule/complete

スケジュール項目を完了にする。

**リクエストボディ:**

```json
{
  "schedule_id": 1
}
```

または:

```json
{
  "task_id": 1,
  "date": "2025-01-13"
}
```

**レスポンス例:**

```json
{
  "schedule_id": 1,
  "status": "completed",
  "actual_hours": 2.5,
  "task_progress": {
    "task_id": 1,
    "estimated_hours": 15.0,
    "actual_hours": 5.5,
    "remaining_hours": 9.5
  }
}
```

---

### 3.4 プロジェクト作成 + タスク分解

#### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/v1/workflow/projects/create-with-tasks` | プロジェクト＋タスク一括作成 |
| POST | `/api/v1/workflow/projects/suggest-breakdown` | タスク分解提案（Claude API） |

#### POST /api/v1/workflow/projects/create-with-tasks

プロジェクトとタスクを一括で作成する。

**リクエストボディ:**

```json
{
  "project": {
    "name": "卒業論文",
    "description": "〇〇に関する研究",
    "goal": "3月末に提出",
    "deadline": "2025-03-31"
  },
  "tasks": [
    {
      "name": "先行研究調査",
      "genre_id": 1,
      "estimated_hours": 15,
      "priority": "高"
    },
    {
      "name": "実験設計",
      "genre_id": 2,
      "estimated_hours": 8,
      "depends_on_indices": [0]
    }
  ]
}
```

**レスポンス例:**

```json
{
  "project": {"id": 1, "name": "卒業論文"},
  "tasks": [
    {"id": 1, "name": "先行研究調査"},
    {"id": 2, "name": "実験設計"}
  ],
  "dependencies_created": 1
}
```

#### POST /api/v1/workflow/projects/suggest-breakdown

Claude APIを使ってタスク分解を提案する。

**リクエストボディ:**

```json
{
  "project_id": 1
}
```

または:

```json
{
  "project_description": "卒業論文を書く。テーマは〇〇。3月末締切。"
}
```

**レスポンス例:**

```json
{
  "suggested_tasks": [
    {
      "name": "先行研究調査",
      "genre_suggestion": "リサーチ",
      "estimated_hours": 15,
      "priority": "高",
      "rationale": "研究の基盤となるため早期に着手"
    },
    {
      "name": "実験設計",
      "genre_suggestion": "コーディング",
      "estimated_hours": 8,
      "depends_on": ["先行研究調査"],
      "rationale": "先行研究を踏まえて設計"
    }
  ],
  "total_estimated_hours": 90,
  "warnings": [
    "締切まで12週間、週15時間の作業で達成可能"
  ]
}
```

---

### 3.5 タスク完了

#### POST /api/v1/workflow/tasks/complete

タスクを完了にする（タイマー停止、スケジュール更新を含む）。

**リクエストボディ:**

```json
{
  "task_id": 1,
  "stop_timer": true,
  "complete_schedules": true
}
```

**レスポンス例:**

```json
{
  "task": {
    "id": 1,
    "name": "先行研究調査",
    "status": "done",
    "estimated_hours": 15.0,
    "actual_hours": 14.5
  },
  "timer_stopped": {
    "duration_minutes": 45
  },
  "schedules_completed": 3,
  "unblocked_tasks": [
    {"id": 2, "name": "実験設計"}
  ]
}
```

---

## 4. ダッシュボードAPI

Reflexダッシュボード用の集計済みデータ（読み取り専用）。

#### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/dashboard/kanban` | カンバンデータ |
| GET | `/api/v1/dashboard/today` | 今日の予定・実績 |
| GET | `/api/v1/dashboard/timeline` | タイムラインデータ |
| GET | `/api/v1/dashboard/weekly` | 週次サマリー |
| GET | `/api/v1/dashboard/stats` | 統計データ |
| GET | `/api/v1/dashboard/summary` | 全体サマリー |

#### GET /api/v1/dashboard/kanban

カンバン表示用データを取得する。

**クエリパラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| project_id | integer | No | フィルタ |

**レスポンス例:**

```json
{
  "columns": {
    "todo": [
      {
        "id": 3,
        "name": "実験実施",
        "project_name": "卒業論文",
        "genre_name": "コーディング",
        "genre_color": "#50C878",
        "priority": "高",
        "deadline": "2025-01-25",
        "estimated_hours": 20.0,
        "actual_hours": 0,
        "blocked_by": ["実験設計"]
      }
    ],
    "doing": [],
    "waiting": [],
    "done": []
  },
  "counts": {"todo": 5, "doing": 2, "waiting": 1, "done": 8}
}
```

#### GET /api/v1/dashboard/today

今日の予定・実績を取得する。

**レスポンス例:**

```json
{
  "date": "2025-01-07",
  "timer": {
    "is_running": true,
    "task_name": "先行研究調査",
    "elapsed_minutes": 35
  },
  "schedules": [
    {
      "start_time": "09:00",
      "end_time": "12:00",
      "task_name": "先行研究調査",
      "project_name": "卒業論文",
      "genre_color": "#4A90D9",
      "planned_hours": 3.0,
      "actual_hours": 2.5,
      "status": "completed"
    }
  ],
  "summary": {
    "planned_hours": 6.0,
    "actual_hours": 4.5,
    "remaining_hours": 1.5
  }
}
```

#### GET /api/v1/dashboard/timeline

タイムライン表示用データを取得する。

**クエリパラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| date | date | No | 特定日（デフォルト: 今日） |

**レスポンス例:**

```json
{
  "date": "2025-01-07",
  "planned": [
    {
      "start": "09:00",
      "end": "12:00",
      "task_name": "先行研究調査",
      "genre_color": "#4A90D9"
    }
  ],
  "actual": [
    {
      "start": "09:00",
      "end": "10:35",
      "task_name": "先行研究調査",
      "genre_color": "#4A90D9"
    },
    {
      "start": "10:45",
      "end": "11:30",
      "task_name": "メール対応",
      "genre_color": "#FF6B6B"
    }
  ]
}
```

#### GET /api/v1/dashboard/weekly

週次サマリーを取得する。

**クエリパラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| week_start | date | No | 週の開始日（デフォルト: 今週） |
| group_by | string | No | project, genre |

**レスポンス例:**

```json
{
  "week_start": "2025-01-06",
  "week_end": "2025-01-12",
  "daily": [
    {
      "date": "2025-01-06",
      "day": "Mon",
      "planned_hours": 6.0,
      "actual_hours": 5.5,
      "by_project": [
        {"name": "卒業論文", "hours": 4.0},
        {"name": "授業課題", "hours": 1.5}
      ]
    }
  ],
  "totals": {
    "planned_hours": 30.0,
    "actual_hours": 25.5,
    "by_project": [
      {"name": "卒業論文", "hours": 18.0},
      {"name": "授業課題", "hours": 7.5}
    ],
    "by_genre": [
      {"name": "リサーチ", "hours": 12.0},
      {"name": "コーディング", "hours": 8.0},
      {"name": "執筆", "hours": 5.5}
    ]
  }
}
```

#### GET /api/v1/dashboard/stats

統計データを取得する。

**クエリパラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| period | string | No | week, month, quarter |

**レスポンス例:**

```json
{
  "period": "week",
  "estimation_accuracy": {
    "average_ratio": 1.15,
    "by_genre": [
      {"name": "コーディング", "ratio": 1.3},
      {"name": "執筆", "ratio": 0.9}
    ]
  },
  "time_distribution": {
    "by_genre": [
      {"name": "リサーチ", "hours": 12.0, "percentage": 40},
      {"name": "コーディング", "hours": 10.0, "percentage": 33}
    ],
    "by_project": [
      {"name": "卒業論文", "hours": 18.0, "percentage": 60}
    ]
  },
  "completion_rate": {
    "tasks_completed": 8,
    "tasks_total": 15,
    "percentage": 53
  },
  "context_switches": {
    "average_per_day": 3.2,
    "trend": "decreasing"
  }
}
```

#### GET /api/v1/dashboard/summary

全体サマリーを取得する。

**レスポンス例:**

```json
{
  "today": {
    "planned_hours": 6.0,
    "actual_hours": 2.5,
    "tasks_scheduled": 3
  },
  "this_week": {
    "planned_hours": 30.0,
    "actual_hours": 12.5,
    "target_hours": 30.0
  },
  "urgent": {
    "overdue_tasks": 0,
    "due_this_week": 3,
    "blocked_tasks": 2
  },
  "timer": {
    "is_running": true,
    "task_name": "先行研究調査",
    "elapsed_minutes": 35
  }
}
```

---

## 5. 同期API

外部サービスとの連携。

#### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/v1/sync/gcal/import` | Google Calendar → DB |
| POST | `/api/v1/sync/gcal/export` | DB → Google Calendar |
| GET | `/api/v1/sync/gcal/status` | 同期状態確認 |

#### POST /api/v1/sync/gcal/import

Google Calendarから予定をインポートする。

**リクエストボディ:**

```json
{
  "calendar_id": "primary",
  "date_from": "2025-01-06",
  "date_to": "2025-01-12",
  "import_as": "blocked_time"
}
```

**レスポンス例:**

```json
{
  "imported_events": 5,
  "blocked_times": [
    {"date": "2025-01-07", "start": "14:00", "end": "16:00", "title": "ゼミ"}
  ]
}
```

#### POST /api/v1/sync/gcal/export

スケジュールをGoogle Calendarにエクスポートする。

**リクエストボディ:**

```json
{
  "date_from": "2025-01-13",
  "date_to": "2025-01-19",
  "calendar_id": "primary"
}
```

**レスポンス例:**

```json
{
  "exported_events": 12,
  "created": 10,
  "updated": 2,
  "deleted": 0
}
```

---

## 6. MCP Tools

Claude.ai Integrations用のMCPツール。内部的にはワークフローAPIを呼び出す。

### 6.1 ツール一覧

| ツール名 | 説明 | 対応API |
|---------|------|--------|
| `get_kanban_view` | カンバンデータ取得 | GET `/api/v1/dashboard/kanban` |
| `get_today_schedule` | 今日のスケジュール | GET `/api/v1/dashboard/today` |
| `get_week_schedule` | 週間スケジュール | GET `/api/v1/dashboard/weekly` |
| `get_projects` | プロジェクト一覧 | GET `/api/v1/projects` |
| `get_task_detail` | タスク詳細 | GET `/api/v1/tasks/{id}` |
| `get_summary` | 状況サマリー | GET `/api/v1/dashboard/summary` |
| `create_project` | プロジェクト作成 | POST `/api/v1/projects` |
| `create_task` | タスク作成 | POST `/api/v1/tasks` |
| `update_task` | タスク更新 | PATCH `/api/v1/tasks/{id}` |
| `breakdown_task` | タスク分解 | POST `/api/v1/workflow/tasks/breakdown` |
| `merge_tasks` | タスク統合 | POST `/api/v1/workflow/tasks/merge` |
| `generate_weekly_schedule` | 週次スケジュール生成 | POST `/api/v1/workflow/schedule/generate-weekly` |
| `reschedule` | リスケジュール | POST `/api/v1/workflow/schedule/reschedule` |
| `start_timer` | タイマー開始 | POST `/api/v1/workflow/timer/start` |
| `stop_timer` | タイマー停止 | POST `/api/v1/workflow/timer/stop` |
| `get_timer_status` | タイマー状態 | GET `/api/v1/workflow/timer/status` |
| `complete_task` | タスク完了 | POST `/api/v1/workflow/tasks/complete` |

### 6.2 MCPエンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/mcp/sse` | MCP over SSE（Claude.ai接続用） |
| POST | `/mcp/messages` | MCPメッセージ処理 |

---

## 7. エラーコード一覧

| コード | HTTPステータス | 説明 |
|--------|---------------|------|
| VALIDATION_ERROR | 400 | リクエスト不正 |
| TASK_NOT_FOUND | 404 | タスクが見つからない |
| PROJECT_NOT_FOUND | 404 | プロジェクトが見つからない |
| SCHEDULE_NOT_FOUND | 404 | スケジュールが見つからない |
| TIMER_ALREADY_RUNNING | 409 | タイマーが既に実行中 |
| TIMER_NOT_RUNNING | 409 | タイマーが実行中でない |
| DEPENDENCY_CYCLE | 422 | 依存関係が循環している |
| DEPENDENCY_ERROR | 422 | 依存関係エラー |
| TASK_ALREADY_COMPLETED | 422 | タスクは既に完了 |
| GCAL_API_ERROR | 502 | Google Calendar APIエラー |
| CLAUDE_API_ERROR | 502 | Claude APIエラー |

**エラーレスポンス例:**

```json
{
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Task with id 999 not found",
    "details": {
      "task_id": 999
    }
  }
}
```

---

## 8. 認証・認可

### 8.1 認証方式

- **Bearer Token**: APIキー認証（シンプルな運用想定）
- 将来的にOAuth2対応も検討

### 8.2 ヘッダー

```
Authorization: Bearer {API_KEY}
```

### 8.3 Cloudflare Accessとの連携

Cloudflare Tunnel使用時は、Cloudflare Accessで追加の認証レイヤーを設定可能。

---

## 更新履歴

| 日付 | バージョン | 内容 |
|------|------------|------|
| 2025-01-07 | 1.0 | 初版作成 |
