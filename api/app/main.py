from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.routers import health, genres, projects, tasks, schedules, time_entries, settings as settings_router, task_dependencies, dashboard
from app.routers.workflow import timer, tasks as workflow_tasks
from app.schemas.common import ErrorResponse

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse.create(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": exc.errors()},
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse.create(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            details={"error": str(exc)},
        ).model_dump(),
    )


# ルーター登録
app.include_router(health.router, tags=["Health"])
app.include_router(genres.router, prefix="/api/v1/genres", tags=["Genres"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(schedules.router, prefix="/api/v1/schedules", tags=["Schedules"])
app.include_router(
    time_entries.router, prefix="/api/v1/time-entries", tags=["Time Entries"]
)
app.include_router(
    settings_router.router, prefix="/api/v1/settings", tags=["Settings"]
)

# Workflow routers
app.include_router(
    timer.router, prefix="/api/v1/workflow/timer", tags=["Workflow - Timer"]
)
app.include_router(
    workflow_tasks.router, prefix="/api/v1/workflow/tasks", tags=["Workflow - Tasks"]
)

# Task dependencies
app.include_router(
    task_dependencies.router, prefix="/api/v1/tasks", tags=["Task Dependencies"]
)

# Dashboard
app.include_router(
    dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"]
)


@app.get("/")
async def root():
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "docs": "/api/docs",
    }
