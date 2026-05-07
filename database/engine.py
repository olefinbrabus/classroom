from typing import AsyncGenerator
import os
from pathlib import Path

from fastapi.params import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy import Integer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import (
    sessionmaker,
    mapped_column,
    Mapped,
    DeclarativeMeta,
    declarative_base,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = Path(
    os.environ.get("CLASSROOM_DATABASE_PATH", PROJECT_ROOT / "classroom_database.db")
).resolve()
DATABASE_CONNECTION_STRING = f"sqlite+aiosqlite:///{DATABASE_PATH}"

engine: AsyncEngine = create_async_engine(DATABASE_CONNECTION_STRING)

async_session_maker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base: DeclarativeMeta = declarative_base()


class BaseModel(Base):
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    from database.models import User

    yield SQLAlchemyUserDatabase(session, User)
