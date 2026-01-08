"""MCP tool definitions with JSON Schema."""

MCP_TOOLS = [
    # ===== Reference Tools (7) =====
    {
        "name": "get_today_schedule",
        "description": "今日のスケジュールとタイマー状態を取得します。予定されているタスク、計画時間、実績時間を確認できます。",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_week_schedule",
        "description": "週間スケジュールを取得します。日別の計画時間と実績時間、プロジェクト・ジャンル別の集計を確認できます。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "week_start": {
                    "type": "string",
                    "format": "date",
                    "description": "週の開始日（YYYY-MM-DD形式）。指定しない場合は今週。",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_kanban_view",
        "description": "カンバンビューを取得します。タスクをTodo/Doing/Waiting/Doneのステータス別に表示します。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "プロジェクトIDでフィルタリング（オプション）",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_projects",
        "description": "プロジェクト一覧を取得します。アクティブ/非アクティブでフィルタリング可能です。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "is_active": {
                    "type": "boolean",
                    "description": "アクティブなプロジェクトのみ取得する場合はtrue",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_task_detail",
        "description": "タスクの詳細情報を取得します。依存関係、時間記録、スケジュールを含みます。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "タスクID",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "get_summary",
        "description": "全体サマリーを取得します。今日と今週の進捗、緊急タスク、タイマー状態を一覧表示します。",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_timer_status",
        "description": "現在のタイマー状態を取得します。稼働中のタイマーがあれば経過時間も表示します。",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # ===== Timer Tools (2) =====
    {
        "name": "start_timer",
        "description": "タスクのタイマーを開始します。別のタイマーが稼働中の場合は自動停止します。task_idまたはtask_nameのいずれかを指定してください。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "タスクID",
                },
                "task_name": {
                    "type": "string",
                    "description": "タスク名（部分一致で検索）",
                },
            },
            "required": [],
        },
    },
    {
        "name": "stop_timer",
        "description": "稼働中のタイマーを停止します。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "note": {
                    "type": "string",
                    "description": "作業メモ（オプション）",
                },
            },
            "required": [],
        },
    },
    # ===== Task Tools (5) =====
    {
        "name": "create_task",
        "description": "新しいタスクを作成します。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "タスク名",
                },
                "description": {
                    "type": "string",
                    "description": "タスクの詳細説明（Markdown対応）",
                },
                "project_id": {
                    "type": "integer",
                    "description": "プロジェクトID",
                },
                "genre_id": {
                    "type": "integer",
                    "description": "ジャンルID",
                },
                "estimated_hours": {
                    "type": "number",
                    "description": "見積もり時間（時間単位）",
                },
                "priority": {
                    "type": "string",
                    "enum": ["高", "中", "低"],
                    "description": "優先度",
                },
                "want_level": {
                    "type": "string",
                    "enum": ["高", "中", "低"],
                    "description": "やりたい度",
                },
                "deadline": {
                    "type": "string",
                    "format": "date-time",
                    "description": "締め切り（ISO 8601形式）",
                },
            },
            "required": ["name", "description"],
        },
    },
    {
        "name": "update_task",
        "description": "既存のタスクを更新します。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "タスクID",
                },
                "name": {
                    "type": "string",
                    "description": "タスク名",
                },
                "status": {
                    "type": "string",
                    "enum": ["todo", "doing", "waiting", "done", "archive"],
                    "description": "ステータス",
                },
                "estimated_hours": {
                    "type": "number",
                    "description": "見積もり時間",
                },
                "priority": {
                    "type": "string",
                    "enum": ["高", "中", "低"],
                    "description": "優先度",
                },
                "want_level": {
                    "type": "string",
                    "enum": ["高", "中", "低"],
                    "description": "やりたい度",
                },
                "deadline": {
                    "type": "string",
                    "format": "date-time",
                    "description": "締め切り",
                },
                "note": {
                    "type": "string",
                    "description": "メモ",
                },
                "description": {
                    "type": "string",
                    "description": "タスクの詳細説明（Markdown対応）",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "complete_task",
        "description": "タスクを完了状態にします。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "タスクID",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "breakdown_task",
        "description": "タスクを複数のサブタスクに分解します。元のタスクはアーカイブされます。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "分解するタスクID",
                },
                "subtasks": {
                    "type": "array",
                    "description": "サブタスクのリスト",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "サブタスク名",
                            },
                            "estimated_hours": {
                                "type": "number",
                                "description": "見積もり時間",
                            },
                            "genre_id": {
                                "type": "integer",
                                "description": "ジャンルID",
                            },
                        },
                        "required": ["name"],
                    },
                },
                "reason": {
                    "type": "string",
                    "description": "分解理由",
                },
            },
            "required": ["task_id", "subtasks"],
        },
    },
    {
        "name": "merge_tasks",
        "description": "複数のタスクを1つに統合します。元のタスクはアーカイブされます。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_ids": {
                    "type": "array",
                    "description": "統合するタスクIDのリスト（2つ以上）",
                    "items": {
                        "type": "integer",
                    },
                    "minItems": 2,
                },
                "merged_name": {
                    "type": "string",
                    "description": "統合後のタスク名",
                },
                "reason": {
                    "type": "string",
                    "description": "統合理由",
                },
            },
            "required": ["task_ids", "merged_name"],
        },
    },
    {
        "name": "add_task_dependency",
        "description": "タスク間の依存関係を追加します。task_idがdepends_on_task_idの完了を待つ関係になります。循環依存は自動検出されエラーになります。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "依存元のタスクID（待つ側）",
                },
                "depends_on_task_id": {
                    "type": "integer",
                    "description": "依存先のタスクID（先に完了すべき側）",
                },
            },
            "required": ["task_id", "depends_on_task_id"],
        },
    },
    {
        "name": "remove_task_dependency",
        "description": "タスク間の依存関係を削除します。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "依存元のタスクID",
                },
                "depends_on_task_id": {
                    "type": "integer",
                    "description": "依存先のタスクID",
                },
            },
            "required": ["task_id", "depends_on_task_id"],
        },
    },
    # ===== Project Tool (1) =====
    {
        "name": "create_project",
        "description": "新しいプロジェクトを作成します。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "プロジェクト名",
                },
                "description": {
                    "type": "string",
                    "description": "プロジェクトの詳細説明（Markdown対応）",
                },
                "goal": {
                    "type": "string",
                    "description": "プロジェクトの目標（descriptionのエイリアス）",
                },
                "deadline": {
                    "type": "string",
                    "format": "date-time",
                    "description": "締め切り",
                },
            },
            "required": ["name", "description"],
        },
    },
    # ===== Schedule Tools (2) =====
    {
        "name": "generate_weekly_schedule",
        "description": "AIによる週間スケジュール自動生成（未実装）。タスクの優先度、締め切り、見積もり時間を考慮して最適なスケジュールを生成します。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "week_start": {
                    "type": "string",
                    "format": "date",
                    "description": "週の開始日（YYYY-MM-DD形式）",
                },
                "sync_to_gcal": {
                    "type": "boolean",
                    "description": "Googleカレンダーと同期するか",
                },
            },
            "required": [],
        },
    },
    {
        "name": "reschedule",
        "description": "特定の日のスケジュールを再生成（未実装）。予定変更やキャンセルに対応します。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "format": "date",
                    "description": "再スケジュールする日付（YYYY-MM-DD形式）",
                },
                "reason": {
                    "type": "string",
                    "description": "再スケジュール理由",
                },
                "blocked_times": {
                    "type": "array",
                    "description": "ブロックする時間帯のリスト",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start": {
                                "type": "string",
                                "format": "time",
                                "description": "開始時間（HH:MM形式）",
                            },
                            "end": {
                                "type": "string",
                                "format": "time",
                                "description": "終了時間（HH:MM形式）",
                            },
                        },
                        "required": ["start", "end"],
                    },
                },
            },
            "required": ["date"],
        },
    },
]
