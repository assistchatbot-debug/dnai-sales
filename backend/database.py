from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine, 
    class_=AsyncSession,
    expire_on_commit=False  # ИСПРАВЛЕНИЕ: отключаем автоматическое обновление после commit
)

async def get_db():
    async with SessionLocal() as session:
        yield session

Base = declarative_base()


# Context manager for background tasks
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_session():
    async with SessionLocal() as session:
        yield session
