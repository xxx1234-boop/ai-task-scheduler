# 研究時間管理システム データベース設計書

## 1. 概要

### 1.1 目的

本設計書は、研究時間管理システムのPostgreSQLデータベース設計を定義する。

### 1.2 設計方針

- **正規化**: 第3正規形を基本とし、パフォーマンスが必要な箇所のみ非正規化
- **論理削除**: タスク・プロジェクトはstatusによる論理削除（archive）
- **履歴管理**: タスク操作はtask_historyで追跡
- **柔軟性**: settingsテーブルでJSONBによる設定管理

### 1.3 命名規則

| 対象 | 規則 | 例 |
|------|------|-----|
| テーブル名 | スネークケース（複数形） | `tasks`, `time_entries` |
| カラム名 | スネークケース | `created_at`, `project_id` |
| 主キー | `id` | `id` |
| 外部キー | `{参照テーブル単数形}_id` | `task_id`, `project_id` |
| 日時カラム | `*_at` | `created_at`, `updated_at` |
| フラグカラム | `is_*` | `is_splittable` |

---

## 2. ER図

```
┌─────────────────┐
│    settings     │
│─────────────────│
│ key (PK)        │
│ value (JSONB)   │
└─────────────────┘

┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    projects     │       │     genres      │       │  task_history   │
│─────────────────│       │─────────────────│       │─────────────────│
│ id (PK)         │       │ id (PK)         │       │ id (PK)         │
│ name            │       │ name            │       │ task_id (FK)    │
│ description     │       │ color           │       │ operation_type  │
│ goal            │       │ created_at      │       │ details (JSONB) │
│ deadline        │       └────────┬────────┘       │ reason          │
│ status          │                │                │ created_at      │
│ created_at      │                │                └────────┬────────┘
│ updated_at      │                │                         │
└────────┬────────┘                │                         │
         │                         │                         │
         │         ┌───────────────┴─────────────────────────┘
         │         │
         ▼         ▼
┌─────────────────────────────────────────────────────────────┐
│                          tasks                               │
│─────────────────────────────────────────────────────────────│
│ id (PK)                                                      │
│ name                                                         │
│ project_id (FK) ─────────────────────────────────► projects │
│ genre_id (FK) ───────────────────────────────────► genres   │
│ status                                                       │
│ deadline                                                     │
│ estimated_hours                                              │
│ actual_hours                                                 │
│ priority                                                     │
│ want_level                                                   │
│ recurrence                                                   │
│ is_splittable                                                │
│ min_work_unit                                                │
│ parent_task_id (FK, self) ───────────────────────► tasks    │
│ decomposition_level                                          │
│ note                                                         │
│ created_at                                                   │
│ updated_at                                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│   schedules     │ │  time_entries   │ │ task_dependencies   │
│─────────────────│ │─────────────────│ │─────────────────────│
│ id (PK)         │ │ id (PK)         │ │ task_id (PK, FK)    │
│ task_id (FK)    │ │ task_id (FK)    │ │ depends_on_task_id  │
│ date            │ │ start_time      │ │   (PK, FK)          │
│ start_time      │ │ end_time        │ └─────────────────────┘
│ end_time        │ │ duration_minutes│
│ planned_hours   │ │ note            │
│ actual_hours    │ │ created_at      │
│ status          │ └─────────────────┘
│ gcal_event_id   │
│ created_at      │
└─────────────────┘
```

---

## 3. テーブル定義

### 3.1 genres（ジャンル）

作業の種類を分類するマスターテーブル。

| カラム名 | データ型 | NULL | デフォルト | 説明 |
|---------|---------|------|-----------|------|
| id | SERIAL | NO | auto | 主キー |
| name | VARCHAR(100) | NO | - | ジャンル名（ユニーク） |
| color | VARCHAR(7) | YES | NULL | 表示色（#RRGGBB形式） |
| created_at | TIMESTAMP | NO | NOW() | 作成日時 |

**制約:**
- PRIMARY KEY: `id`
- UNIQUE: `name`

**インデックス:**
- なし（レコード数が少ないため不要）

---

### 3.2 projects（プロジェクト）

研究プロジェクトを管理するテーブル。

| カラム名 | データ型 | NULL | デフォルト | 説明 |
|---------|---------|------|-----------|------|
| id | SERIAL | NO | auto | 主キー |
| name | VARCHAR(200) | NO | - | プロジェクト名 |
| description | TEXT | YES | NULL | 説明 |
| goal | TEXT | YES | NULL | 目標 |
| deadline | DATE | YES | NULL | 締切日 |
| status | VARCHAR(20) | NO | 'active' | ステータス |
| gcal_calendar_id | VARCHAR(255) | YES | NULL | Google Calendar ID |
| created_at | TIMESTAMP | NO | NOW() | 作成日時 |
| updated_at | TIMESTAMP | NO | NOW() | 更新日時 |

**statusの値:**
| 値 | 説明 |
|----|------|
| active | 進行中 |
| completed | 完了 |
| archived | アーカイブ |

**制約:**
- PRIMARY KEY: `id`
- CHECK: `status IN ('active', 'completed', 'archived')`

**インデックス:**
| インデックス名 | カラム | 種類 |
|---------------|--------|------|
| idx_projects_status | status | BTREE |
| idx_projects_deadline | deadline | BTREE |

---

### 3.3 tasks（タスク）

作業タスクを管理するテーブル。階層構造に対応。

| カラム名 | データ型 | NULL | デフォルト | 説明 |
|---------|---------|------|-----------|------|
| id | SERIAL | NO | auto | 主キー |
| name | VARCHAR(300) | NO | - | タスク名 |
| project_id | INTEGER | YES | NULL | プロジェクトID（FK） |
| genre_id | INTEGER | YES | NULL | ジャンルID（FK） |
| status | VARCHAR(20) | NO | 'todo' | ステータス |
| deadline | TIMESTAMP | YES | NULL | 締切日時 |
| estimated_hours | DECIMAL(5,2) | YES | NULL | 見積もり時間（時間） |
| actual_hours | DECIMAL(5,2) | NO | 0 | 実績時間（時間） |
| priority | VARCHAR(10) | NO | '中' | 優先度 |
| want_level | VARCHAR(10) | NO | '中' | やりたい度 |
| recurrence | VARCHAR(20) | NO | 'なし' | 繰り返し設定 |
| is_splittable | BOOLEAN | NO | TRUE | 分割可能フラグ |
| min_work_unit | DECIMAL(3,1) | NO | 0.5 | 最小作業単位（時間） |
| parent_task_id | INTEGER | YES | NULL | 親タスクID（FK、自己参照） |
| decomposition_level | INTEGER | NO | 0 | 分解レベル（0=トップ）※自動計算（trigger） |
| note | TEXT | YES | NULL | メモ |
| created_at | TIMESTAMP | NO | NOW() | 作成日時 |
| updated_at | TIMESTAMP | NO | NOW() | 更新日時 |

**statusの値:**
| 値 | 説明 |
|----|------|
| todo | 未着手 |
| doing | 作業中 |
| waiting | 待機中（ブロック等） |
| done | 完了 |
| archive | アーカイブ（分解・統合後） |

**priority / want_levelの値:**
| 値 | 説明 |
|----|------|
| 高 | 高い |
| 中 | 中程度 |
| 低 | 低い |

**recurrenceの値:**
| 値 | 説明 |
|----|------|
| なし | 繰り返しなし |
| 毎日 | 毎日 |
| 毎週 | 毎週 |
| 毎月 | 毎月 |

**制約:**
- PRIMARY KEY: `id`
- FOREIGN KEY: `project_id` → `projects(id)` ON DELETE SET NULL
- FOREIGN KEY: `genre_id` → `genres(id)` ON DELETE SET NULL
- FOREIGN KEY: `parent_task_id` → `tasks(id)` ON DELETE SET NULL
- CHECK: `status IN ('todo', 'doing', 'waiting', 'done', 'archive')`
- CHECK: `priority IN ('高', '中', '低')`
- CHECK: `want_level IN ('高', '中', '低')`
- CHECK: `recurrence IN ('なし', '毎日', '毎週', '毎月')`
- CHECK: `estimated_hours >= 0`
- CHECK: `actual_hours >= 0`
- CHECK: `decomposition_level >= 0`

**インデックス:**
| インデックス名 | カラム | 種類 |
|---------------|--------|------|
| idx_tasks_project | project_id | BTREE |
| idx_tasks_genre | genre_id | BTREE |
| idx_tasks_status | status | BTREE |
| idx_tasks_parent | parent_task_id | BTREE |
| idx_tasks_deadline | deadline | BTREE |
| idx_tasks_priority_status | (priority, status) | BTREE（複合） |

---

### 3.4 task_dependencies（タスク依存関係）

タスク間の依存関係を管理する中間テーブル。

| カラム名 | データ型 | NULL | デフォルト | 説明 |
|---------|---------|------|-----------|------|
| task_id | INTEGER | NO | - | タスクID（FK、複合PK） |
| depends_on_task_id | INTEGER | NO | - | 依存先タスクID（FK、複合PK） |

**制約:**
- PRIMARY KEY: `(task_id, depends_on_task_id)`
- FOREIGN KEY: `task_id` → `tasks(id)` ON DELETE CASCADE
- FOREIGN KEY: `depends_on_task_id` → `tasks(id)` ON DELETE CASCADE
- CHECK: `task_id != depends_on_task_id`（自己参照禁止）

**インデックス:**
| インデックス名 | カラム | 種類 |
|---------------|--------|------|
| idx_task_deps_depends_on | depends_on_task_id | BTREE |

---

### 3.5 schedules（スケジュール）

日次のスケジュールを管理するテーブル。

| カラム名 | データ型 | NULL | デフォルト | 説明 |
|---------|---------|------|-----------|------|
| id | SERIAL | NO | auto | 主キー |
| task_id | INTEGER | NO | - | タスクID（FK） |
| date | DATE | NO | - | 日付 |
| start_time | TIME | YES | NULL | 開始時刻 |
| end_time | TIME | YES | NULL | 終了時刻 |
| planned_hours | DECIMAL(4,2) | YES | NULL | 予定時間（時間） |
| actual_hours | DECIMAL(4,2) | NO | 0 | 実績時間（時間） |
| status | VARCHAR(20) | NO | 'scheduled' | ステータス |
| gcal_event_id | VARCHAR(255) | YES | NULL | Google Calendar Event ID |
| created_at | TIMESTAMP | NO | NOW() | 作成日時 |

**statusの値:**
| 値 | 説明 |
|----|------|
| scheduled | 予定 |
| completed | 完了 |
| skipped | スキップ |

**制約:**
- PRIMARY KEY: `id`
- FOREIGN KEY: `task_id` → `tasks(id)` ON DELETE CASCADE
- CHECK: `status IN ('scheduled', 'completed', 'skipped')`
- CHECK: `planned_hours >= 0`
- CHECK: `actual_hours >= 0`
- CHECK: `end_time > start_time`（start_time, end_time両方がNOT NULLの場合）

**インデックス:**
| インデックス名 | カラム | 種類 |
|---------------|--------|------|
| idx_schedules_task | task_id | BTREE |
| idx_schedules_date | date | BTREE |
| idx_schedules_date_status | (date, status) | BTREE（複合） |
| idx_schedules_gcal | gcal_event_id | BTREE |

---

### 3.6 time_entries（時間記録）

タイマーによる時間記録を管理するテーブル。

| カラム名 | データ型 | NULL | デフォルト | 説明 |
|---------|---------|------|-----------|------|
| id | SERIAL | NO | auto | 主キー |
| task_id | INTEGER | NO | - | タスクID（FK） |
| start_time | TIMESTAMP | NO | - | 開始日時 |
| end_time | TIMESTAMP | YES | NULL | 終了日時（NULL=実行中） |
| duration_minutes | INTEGER | YES | NULL | 作業時間（分） |
| note | TEXT | YES | NULL | メモ |
| created_at | TIMESTAMP | NO | NOW() | 作成日時 |

**制約:**
- PRIMARY KEY: `id`
- FOREIGN KEY: `task_id` → `tasks(id)` ON DELETE CASCADE
- CHECK: `end_time IS NULL OR end_time > start_time`
- CHECK: `duration_minutes IS NULL OR duration_minutes >= 0`

**インデックス:**
| インデックス名 | カラム | 種類 |
|---------------|--------|------|
| idx_time_entries_task | task_id | BTREE |
| idx_time_entries_start | start_time | BTREE |
| idx_time_entries_running | end_time | BTREE（部分：WHERE end_time IS NULL） |

---

### 3.7 task_history（タスク履歴）

タスクの操作履歴を管理するテーブル。

| カラム名 | データ型 | NULL | デフォルト | 説明 |
|---------|---------|------|-----------|------|
| id | SERIAL | NO | auto | 主キー |
| task_id | INTEGER | YES | NULL | タスクID（FK） |
| operation_type | VARCHAR(30) | NO | - | 操作種別 |
| details | JSONB | YES | NULL | 操作詳細 |
| reason | TEXT | YES | NULL | 理由 |
| created_at | TIMESTAMP | NO | NOW() | 作成日時 |

**operation_typeの値:**
| 値 | 説明 |
|----|------|
| 作成 | タスク作成 |
| 分解 | タスク分解（1→多） |
| 統合 | タスク統合（多→1） |
| 見積もり変更 | 見積もり時間の変更 |
| ステータス変更 | ステータスの変更 |

**detailsの例:**
```json
// 分解の場合
{
  "original_estimate": 15,
  "child_tasks": [7, 8, 9],
  "total_new_estimate": 15
}

// 統合の場合
{
  "merged_from": [7, 8],
  "original_estimates": [5, 6],
  "new_estimate": 11
}

// ステータス変更の場合
{
  "from": "doing",
  "to": "done",
  "estimated": 15,
  "actual": 14.5
}
```

**制約:**
- PRIMARY KEY: `id`
- FOREIGN KEY: `task_id` → `tasks(id)` ON DELETE SET NULL
- CHECK: `operation_type IN ('作成', '分解', '統合', '見積もり変更', 'ステータス変更')`

**インデックス:**
| インデックス名 | カラム | 種類 |
|---------------|--------|------|
| idx_task_history_task | task_id | BTREE |
| idx_task_history_created | created_at | BTREE |
| idx_task_history_operation | operation_type | BTREE |

---

### 3.8 settings（システム設定）

システム設定をKey-Value形式で管理するテーブル。

| カラム名 | データ型 | NULL | デフォルト | 説明 |
|---------|---------|------|-----------|------|
| key | VARCHAR(100) | NO | - | 設定キー（PK） |
| value | JSONB | YES | NULL | 設定値 |
| updated_at | TIMESTAMP | NO | NOW() | 更新日時 |

**制約:**
- PRIMARY KEY: `key`

**インデックス:**
- なし（主キーのみで十分）

**想定される設定キー:**
| キー | 説明 | 値の例 |
|------|------|--------|
| weekly_available_hours | 週次の作業可能時間 | `{"mon": 6, "tue": 6, ...}` |
| default_work_hours | デフォルト作業時間帯 | `{"start": "09:00", "end": "18:00"}` |
| gcal_settings | Google Calendar設定 | `{"calendar_id": "...", "sync_enabled": true}` |
| scheduling_preferences | スケジューリング設定 | `{"avoid_context_switch": true, ...}` |

---

## 4. DDL（テーブル作成SQL）

```sql
-- ジャンル
CREATE TABLE genres (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    color VARCHAR(7),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- プロジェクト
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    goal TEXT,
    deadline DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'completed', 'archived')),
    gcal_calendar_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_deadline ON projects(deadline);

-- タスク
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    genre_id INTEGER REFERENCES genres(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'todo'
        CHECK (status IN ('todo', 'doing', 'waiting', 'done', 'archive')),
    deadline TIMESTAMP,
    estimated_hours DECIMAL(5,2) CHECK (estimated_hours >= 0),
    actual_hours DECIMAL(5,2) NOT NULL DEFAULT 0 CHECK (actual_hours >= 0),
    priority VARCHAR(10) NOT NULL DEFAULT '中'
        CHECK (priority IN ('高', '中', '低')),
    want_level VARCHAR(10) NOT NULL DEFAULT '中'
        CHECK (want_level IN ('高', '中', '低')),
    recurrence VARCHAR(20) NOT NULL DEFAULT 'なし'
        CHECK (recurrence IN ('なし', '毎日', '毎週', '毎月')),
    is_splittable BOOLEAN NOT NULL DEFAULT TRUE,
    min_work_unit DECIMAL(3,1) NOT NULL DEFAULT 0.5,
    parent_task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    decomposition_level INTEGER NOT NULL DEFAULT 0 CHECK (decomposition_level >= 0),
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_genre ON tasks(genre_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_parent ON tasks(parent_task_id);
CREATE INDEX idx_tasks_deadline ON tasks(deadline);
CREATE INDEX idx_tasks_priority_status ON tasks(priority, status);

-- タスク依存関係
CREATE TABLE task_dependencies (
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on_task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, depends_on_task_id),
    CHECK (task_id != depends_on_task_id)
);

CREATE INDEX idx_task_deps_depends_on ON task_dependencies(depends_on_task_id);

-- スケジュール
CREATE TABLE schedules (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    planned_hours DECIMAL(4,2) CHECK (planned_hours >= 0),
    actual_hours DECIMAL(4,2) NOT NULL DEFAULT 0 CHECK (actual_hours >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled', 'completed', 'skipped')),
    gcal_event_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_time_range CHECK (
        start_time IS NULL OR end_time IS NULL OR end_time > start_time
    )
);

CREATE INDEX idx_schedules_task ON schedules(task_id);
CREATE INDEX idx_schedules_date ON schedules(date);
CREATE INDEX idx_schedules_date_status ON schedules(date, status);
CREATE INDEX idx_schedules_gcal ON schedules(gcal_event_id);

-- 時間記録
CREATE TABLE time_entries (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_minutes INTEGER CHECK (duration_minutes >= 0),
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_entry_time CHECK (
        end_time IS NULL OR end_time > start_time
    )
);

CREATE INDEX idx_time_entries_task ON time_entries(task_id);
CREATE INDEX idx_time_entries_start ON time_entries(start_time);
CREATE INDEX idx_time_entries_running ON time_entries(end_time) WHERE end_time IS NULL;

-- タスク履歴
CREATE TABLE task_history (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    operation_type VARCHAR(30) NOT NULL
        CHECK (operation_type IN ('作成', '分解', '統合', '見積もり変更', 'ステータス変更')),
    details JSONB,
    reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_task_history_task ON task_history(task_id);
CREATE INDEX idx_task_history_created ON task_history(created_at);
CREATE INDEX idx_task_history_operation ON task_history(operation_type);

-- システム設定
CREATE TABLE settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

## 5. トリガー・関数

### 5.1 updated_at自動更新

```sql
-- 更新日時自動更新関数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- projects
CREATE TRIGGER trigger_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- tasks
CREATE TRIGGER trigger_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- settings
CREATE TRIGGER trigger_settings_updated_at
    BEFORE UPDATE ON settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 5.2 decomposition_level自動計算

タスクの階層レベルを自動計算するトリガー。`parent_task_id`に基づいて階層深さを自動的に設定します。

```sql
-- decomposition_level自動計算関数
CREATE OR REPLACE FUNCTION update_decomposition_level_on_change()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.parent_task_id IS NULL THEN
        NEW.decomposition_level := 0;
    ELSE
        SELECT COALESCE(decomposition_level, 0) + 1
        INTO NEW.decomposition_level
        FROM tasks WHERE id = NEW.parent_task_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_decomposition_level
    BEFORE INSERT OR UPDATE OF parent_task_id ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_decomposition_level_on_change();

-- 親変更時に子孫全体を再計算
CREATE OR REPLACE FUNCTION cascade_decomposition_level()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE' AND OLD.parent_task_id IS DISTINCT FROM NEW.parent_task_id) THEN
        WITH RECURSIVE descendants AS (
            SELECT id FROM tasks WHERE parent_task_id = NEW.id
            UNION ALL
            SELECT t.id FROM tasks t
            INNER JOIN descendants d ON t.parent_task_id = d.id
        )
        UPDATE tasks SET parent_task_id = parent_task_id
        WHERE id IN (SELECT id FROM descendants);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_cascade_decomposition
    AFTER UPDATE OF parent_task_id ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION cascade_decomposition_level();
```

**動作:**
- `parent_task_id = NULL` の場合、`decomposition_level = 0`（ルートタスク）
- 親が存在する場合、親の`decomposition_level + 1`
- 親が変更された場合、すべての子孫が自動的に再計算される

### 5.3 time_entries.duration_minutes自動計算

```sql
-- duration_minutes自動計算関数
CREATE OR REPLACE FUNCTION calculate_duration_minutes()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.end_time IS NOT NULL THEN
        NEW.duration_minutes = EXTRACT(EPOCH FROM (NEW.end_time - NEW.start_time)) / 60;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_time_entries_duration
    BEFORE INSERT OR UPDATE ON time_entries
    FOR EACH ROW
    EXECUTE FUNCTION calculate_duration_minutes();
```

### 5.3 tasks.actual_hours自動更新

```sql
-- actual_hours自動更新関数
CREATE OR REPLACE FUNCTION update_task_actual_hours()
RETURNS TRIGGER AS $$
DECLARE
    target_task_id INTEGER;
BEGIN
    -- INSERT/UPDATE時は新しいtask_id、DELETE時は古いtask_id
    IF TG_OP = 'DELETE' THEN
        target_task_id := OLD.task_id;
    ELSE
        target_task_id := NEW.task_id;
    END IF;

    UPDATE tasks
    SET actual_hours = (
        SELECT COALESCE(SUM(duration_minutes), 0) / 60.0
        FROM time_entries
        WHERE task_id = target_task_id
          AND duration_minutes IS NOT NULL
    )
    WHERE id = target_task_id;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_task_actual_hours
    AFTER INSERT OR UPDATE OR DELETE ON time_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_task_actual_hours();
```

---

## 6. 初期データ

### 6.1 ジャンル

```sql
INSERT INTO genres (name, color) VALUES
    ('リサーチ', '#4A90D9'),
    ('コーディング', '#50C878'),
    ('執筆', '#FFB347'),
    ('ミーティング', '#FF6B6B'),
    ('レビュー', '#DDA0DD'),
    ('実験', '#87CEEB'),
    ('データ分析', '#98D8C8'),
    ('その他', '#C0C0C0');
```

### 6.2 システム設定

```sql
INSERT INTO settings (key, value) VALUES
    ('weekly_available_hours', '{"mon": 6, "tue": 6, "wed": 4, "thu": 6, "fri": 6, "sat": 3, "sun": 0}'),
    ('default_work_hours', '{"start": "09:00", "end": "18:00", "lunch_start": "12:00", "lunch_end": "13:00"}'),
    ('scheduling_preferences', '{"avoid_context_switch": true, "min_block_minutes": 30, "prefer_morning_for_focus": true}'),
    ('gcal_settings', '{"sync_enabled": false, "calendar_id": null}');
```

---

## 7. よく使うクエリ例

### 7.1 カンバン用データ取得

```sql
SELECT 
    t.id,
    t.name,
    t.status,
    t.priority,
    t.want_level,
    t.deadline,
    t.estimated_hours,
    t.actual_hours,
    p.name AS project_name,
    g.name AS genre_name,
    g.color AS genre_color,
    (SELECT COUNT(*) FROM task_dependencies td 
     JOIN tasks dep ON td.depends_on_task_id = dep.id 
     WHERE td.task_id = t.id AND dep.status != 'done') AS blocked_by_count
FROM tasks t
LEFT JOIN projects p ON t.project_id = p.id
LEFT JOIN genres g ON t.genre_id = g.id
WHERE t.status IN ('todo', 'doing', 'waiting', 'done')
ORDER BY 
    CASE t.status 
        WHEN 'doing' THEN 1 
        WHEN 'todo' THEN 2 
        WHEN 'waiting' THEN 3 
        WHEN 'done' THEN 4 
    END,
    t.deadline ASC NULLS LAST;
```

### 7.2 実行中タイマーの取得

```sql
SELECT 
    te.id,
    te.task_id,
    te.start_time,
    EXTRACT(EPOCH FROM (NOW() - te.start_time)) / 60 AS elapsed_minutes,
    t.name AS task_name,
    p.name AS project_name
FROM time_entries te
JOIN tasks t ON te.task_id = t.id
LEFT JOIN projects p ON t.project_id = p.id
WHERE te.end_time IS NULL;
```

### 7.3 週次作業時間サマリー

```sql
SELECT 
    DATE(te.start_time) AS date,
    p.name AS project_name,
    g.name AS genre_name,
    SUM(te.duration_minutes) / 60.0 AS hours
FROM time_entries te
JOIN tasks t ON te.task_id = t.id
LEFT JOIN projects p ON t.project_id = p.id
LEFT JOIN genres g ON t.genre_id = g.id
WHERE te.start_time >= DATE_TRUNC('week', CURRENT_DATE)
  AND te.end_time IS NOT NULL
GROUP BY DATE(te.start_time), p.name, g.name
ORDER BY date, project_name;
```

---

## 8. マイグレーション戦略

### 8.1 ツール

- **Alembic**: SQLAlchemyベースのマイグレーションツール
- SQLModelと組み合わせて使用

### 8.2 マイグレーションファイル命名規則

```
YYYYMMDD_HHMMSS_description.py
例: 20250107_120000_initial_schema.py
```

### 8.3 ロールバック方針

- 各マイグレーションにdowngrade()を必ず実装
- 本番適用前にステージング環境でupgrade/downgradeをテスト

---

## 9. バックアップ・リストア

### 9.1 バックアップ

```bash
# 日次バックアップ（cronで実行）
pg_dump -h localhost -U postgres research_tracker > backup_$(date +%Y%m%d).sql

# 圧縮版
pg_dump -h localhost -U postgres research_tracker | gzip > backup_$(date +%Y%m%d).sql.gz
```

### 9.2 リストア

```bash
# リストア
psql -h localhost -U postgres research_tracker < backup_20250107.sql

# 圧縮版からリストア
gunzip -c backup_20250107.sql.gz | psql -h localhost -U postgres research_tracker
```

---

## 更新履歴

| 日付 | バージョン | 内容 |
|------|------------|------|
| 2025-01-07 | 1.0 | 初版作成 |
