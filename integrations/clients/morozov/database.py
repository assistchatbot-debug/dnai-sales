"""Модуль работы с базой данных"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Text, Integer
from datetime import datetime
from config import settings


# Конвертация URL для asyncpg
db_url = settings.database_url
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Конвертация sslmode в ssl для asyncpg
db_url = db_url.replace("sslmode=require", "ssl=require")

# Создание движка БД
engine = create_async_engine(db_url, echo=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс для моделей"""
    pass


class ProductMapping(Base):
    """Маппинг номенклатуры между 1С и Битрикс24"""
    __tablename__ = "bitrix_1c_product_mapping"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    bitrix24_product_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    bitrix24_product_name: Mapped[str] = mapped_column(String(500))
    onec_product_code: Mapped[str] = mapped_column(String(100), index=True)
    onec_product_name: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SyncLog(Base):
    """Лог синхронизаций"""
    __tablename__ = "bitrix_1c_sync_log"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    sync_type: Mapped[str] = mapped_column(String(50))
    direction: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    entity_id: Mapped[str] = mapped_column(String(100), nullable=True)
    request_data: Mapped[str] = mapped_column(Text, nullable=True)
    response_data: Mapped[str] = mapped_column(Text, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StockSnapshot(Base):
    """Снимок остатков товаров"""
    __tablename__ = "bitrix_1c_stock_snapshot"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    product_code: Mapped[str] = mapped_column(String(100), index=True)
    product_name: Mapped[str] = mapped_column(String(500))
    quantity: Mapped[int] = mapped_column(Integer)
    warehouse: Mapped[str] = mapped_column(String(200))
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


async def init_db():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Получение сессии БД"""
    async with async_session_maker() as session:
        yield session
