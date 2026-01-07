from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings

# 非同期エンジン作成
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.LOG_LEVEL == "debug",
    future=True,
    pool_pre_ping=True,
)

# セッションファクトリ
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# FastAPI依存性
async def get_session():
    async with async_session() as session:
        yield session
