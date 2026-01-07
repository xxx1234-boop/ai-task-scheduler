# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered research time management system that helps track research activities by genre and project, with automatic AI-driven scheduling to optimize time allocation based on deadlines and priorities.

**Key Technologies:**
- **Backend**: FastAPI (async) + SQLModel + PostgreSQL 16
- **ORM**: SQLModel (unified SQLAlchemy 2.0 + Pydantic v2)
- **Database**: PostgreSQL with Alembic migrations
- **Dashboard**: Reflex (Python-based web framework)
- **MCP**: Model Context Protocol for Claude.ai integration
- **Deployment**: Docker Compose + Cloudflare Tunnel/Access
- **Python**: 3.11 (DO NOT upgrade to 3.13 - asyncpg/psycopg2-binary compatibility issues)

**UI Architecture:**
- **Claude.ai Artifacts**: Quick view for daily schedules and simple kanban (4-8 tasks)
- **Reflex Dashboard**: Detailed analysis, full kanban, weekly timelines, statistics (read-only)

## Development Commands

### Docker & Services

```bash
# Start all services
docker compose up -d

# Rebuild API container after code changes
docker compose up -d --build api

# View logs
docker compose logs -f api
docker compose logs --tail=50 api

# Restart specific service
docker compose restart api

# Stop all services
docker compose down

# Check service status
docker compose ps
```

### Database Operations

```bash
# Create new migration
docker compose exec api alembic revision --autogenerate -m "description"

# Apply migrations
docker compose exec api alembic upgrade head

# Rollback one migration
docker compose exec api alembic downgrade -1

# Access PostgreSQL directly
docker compose exec db psql -U postgres -d research_tracker

# List all tables
docker compose exec db psql -U postgres -d research_tracker -c "\dt"

# pgweb (database UI)
# Access at http://localhost:8081
```

### API Testing

```bash
# Health check
curl http://localhost:8000/health

# API documentation
# Swagger UI: http://localhost:8000/api/docs
# ReDoc: http://localhost:8000/api/redoc
```

## Architecture & Design Principles

### SQLModel Unified Approach

This project uses **SQLModel** to simplify the stack by combining SQLAlchemy ORM models and Pydantic validation schemas into single class definitions. This eliminates the need for separate `models.py` and `schemas.py` files.

**Example pattern:**
```python
class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=300)
    status: str = Field(default="todo", max_length=20)
    # ... fields serve both as ORM columns and API validation

    # Relationships
    project: Optional[Project] = Relationship(back_populates="tasks")
```

All models are defined in `api/app/models.py`.

### Database Schema Core Entities

**6 Main Tables:**
1. **genres** - Work type classification (リサーチ, コーディング, 執筆, etc.)
2. **projects** - Research projects with deadlines
3. **tasks** - Work items with hierarchical support (parent_task_id for subtasks)
4. **schedules** - Daily schedule entries (AI-generated or manual)
5. **time_entries** - Timer-based time tracking (start_time, end_time, duration_minutes)
6. **settings** - System configuration (JSONB key-value store)

**Key Relationships:**
- Tasks belong to Projects and Genres (optional foreign keys)
- Tasks can have parent Tasks (self-referential hierarchy)
- TimeEntries track actual work time per Task
- Schedules allocate planned time slots for Tasks

**Important Constraints:**
- Task status: `todo`, `doing`, `waiting`, `done`, `archive`
- Priority/want_level: `高`, `中`, `低` (Japanese)
- Recurrence: `なし`, `毎日`, `毎週`, `毎月`

### Async Patterns

All database operations use async/await:

```python
from sqlmodel.ext.asyncio.session import AsyncSession
from app.database import get_session

@router.get("/tasks")
async def get_tasks(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Task))
    tasks = result.scalars().all()
    return {"items": tasks}
```

### MCP (Model Context Protocol) Integration

The system exposes tools via MCP for Claude.ai to operate the system through natural language:

**MCP Endpoints:**
- `GET /mcp/sse` - Server-Sent Events connection for Claude.ai
- `POST /mcp/messages` - Tool invocation handling

**Tool Categories:**
- **Reference**: `get_today_schedule`, `get_week_schedule`, `get_kanban_view`
- **Timer**: `start_timer`, `stop_timer`, `get_timer_status`
- **Tasks**: `create_task`, `update_task`, `complete_task`, `breakdown_task`, `merge_tasks`
- **Schedule**: `generate_weekly_schedule`, `reschedule`

Implementation location: `api/app/mcp/` (to be implemented)

### Cloudflare Tunnel & Access

**Production Deployment Pattern:**
- FastAPI exposed via Cloudflare Tunnel (no port forwarding needed)
- Cloudflare Access provides authentication layer
- Service Token authentication for Claude.ai MCP
- Email/OAuth authentication for human dashboard access

**Hostnames:**
- API + MCP: `api.research-tracker.your-domain.com`
- Dashboard: `dashboard.research-tracker.your-domain.com`

## Configuration

### Environment Variables

The `.env` file (created from `.env.example`) contains:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/research_tracker
DB_HOST=db  # Docker service name, NOT localhost

# API
API_PORT=8000
LOG_LEVEL=info

# Note: CORS_ORIGINS is NOT in .env - defined in config.py
```

**Important:** Database host is `db` (Docker service name), not `localhost`, when running in containers.

### Settings Management

Settings use `pydantic-settings` with field validators:

```python
# api/app/config.py
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/research_tracker"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8081"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        # Handles both comma-separated strings and lists
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
```

## API Design Patterns

### RESTful CRUD + Workflow Separation

**Standard CRUD** (`/api/v1/{resource}`):
- Simple database operations
- Example: `GET /api/v1/tasks`, `PATCH /api/v1/tasks/{id}`

**Workflow APIs** (`/api/v1/workflow/*`):
- Complex business logic involving multiple steps
- Example: `/api/v1/workflow/timer/start` (stops previous timer + starts new)
- Example: `/api/v1/workflow/tasks/breakdown` (archives parent + creates children + transfers dependencies)

**Dashboard APIs** (`/api/v1/dashboard/*`):
- Read-only aggregated data
- Optimized for display/visualization
- Example: `/api/v1/dashboard/kanban`, `/api/v1/dashboard/weekly`

### Service Layer Pattern

Business logic should be extracted into service classes:

```
api/app/services/
├── timer_service.py      # Timer operations (start/stop)
├── task_service.py       # Task CRUD + breakdown/merge
├── schedule_service.py   # AI scheduling logic
├── project_service.py    # Project management
└── dashboard_service.py  # Aggregated queries
```

Routers should be thin wrappers calling service methods.

## Database Migrations

### Alembic Workflow

1. **Modify models** in `api/app/models.py`
2. **Generate migration**: `docker compose exec api alembic revision --autogenerate -m "description"`
3. **Review** generated file in `api/alembic/versions/`
4. **Apply**: `docker compose exec api alembic upgrade head`

**Important:**
- Always import ALL models in `api/alembic/env.py` so autogenerate detects them
- Review auto-generated migrations - they may miss complex constraints
- Database triggers (updated_at, duration calculation) are defined in design docs but not yet implemented

### Model Import Pattern

`api/alembic/env.py` must import all models:

```python
from app.models import Genre, Project, Schedule, Setting, Task, TimeEntry
target_metadata = SQLModel.metadata
```

## Testing Strategy

Tests should use pytest with async support:

```python
# api/tests/test_tasks.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_task():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/tasks", json={...})
        assert response.status_code == 201
```

Run tests: `docker compose exec api pytest`

## Known Issues & Gotchas

### Python Version Lock

**DO NOT upgrade to Python 3.13.** The project uses Python 3.11 because:
- `psycopg2-binary` and `asyncpg` have compilation issues with Python 3.13
- Pre-built wheels are available for 3.11
- Specified in `api/Dockerfile`: `FROM python:3.11-slim`

### CORS Configuration

CORS origins should be managed via `config.py` defaults, NOT via environment variables or docker-compose.yml. The `@field_validator` handles both string (comma-separated) and list formats for flexibility.

### Docker Compose Override

The `docker-compose.yml` uses `command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` to override Dockerfile CMD for development hot-reload.

### SQLModel Field Defaults

When using `Field(default_factory=datetime.now)`, note:
- Database has `DEFAULT NOW()` for `created_at`
- SQLModel also needs `default_factory` for ORM inserts
- These work together (SQLModel for app, SQL for direct DB inserts)

## Design Documentation

Comprehensive design documents in `/docs/design/`:

1. **01-system-overview.md** - Architecture, UI roles, Cloudflare setup, Docker compose structure
2. **02-database-design.md** - Full schema definitions, triggers, indexes, sample queries
3. **03-api-design.md** - REST endpoints, MCP tools, request/response formats, error codes
4. **04-mcp-design.md** - MCP server implementation, tool definitions, conversation patterns

**Refer to these documents when:**
- Implementing new API endpoints
- Adding MCP tools for Claude.ai
- Designing complex queries
- Understanding business logic flows (task breakdown, scheduling, timer operations)

## Current Implementation Status

**Completed (Day 1):**
- ✅ Docker environment (PostgreSQL, FastAPI, pgweb)
- ✅ SQLModel models (6 tables)
- ✅ Alembic migrations
- ✅ Basic FastAPI app with health endpoint
- ✅ Database tables created

**To Do (Phase 1+):**
- [ ] CRUD API routers (projects, tasks, genres, schedules, time_entries, settings)
- [ ] Workflow APIs (timer, task breakdown/merge, scheduling)
- [ ] Dashboard aggregation APIs
- [ ] MCP server implementation
- [ ] Service layer classes
- [ ] Database triggers (updated_at, duration_minutes, actual_hours)
- [ ] Reflex dashboard
- [ ] Google Calendar integration
- [ ] Claude API integration for scheduling
- [ ] Cloudflare Tunnel/Access setup
