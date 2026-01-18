from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from models import Company, SalesAgentConfig
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/companies", tags=["companies"])

class CompanyCreate(BaseModel):
    name: str
    subdomain: str
    default_language: str = "ru"

class CompanyResponse(BaseModel):
    id: int
    name: str
    subdomain: str
    class Config:
        orm_mode = True


async def create_default_statuses(db, company_id: int):
    """Create default lead status settings for new company"""
    from sqlalchemy import text
    default_statuses = [
        {'emoji': '🟢', 'name': 'Новый', 'coins': 10, 'sort_order': 1, 'is_final': False},
        {'emoji': '🟡', 'name': 'В работе', 'coins': 20, 'sort_order': 2, 'is_final': False},
        {'emoji': '🔵', 'name': 'Переговоры', 'coins': 30, 'sort_order': 3, 'is_final': False},
        {'emoji': '💰', 'name': 'Ожидает оплаты', 'coins': 50, 'sort_order': 4, 'is_final': False},
        {'emoji': '✅', 'name': 'Завершён', 'coins': 100, 'sort_order': 5, 'is_final': True},
        {'emoji': '❌', 'name': 'Отказ', 'coins': -100, 'sort_order': 6, 'is_final': True},
        {'emoji': '🔄', 'name': 'Повторная сделка', 'coins': 20, 'sort_order': 21, 'is_final': False},
    ]
    for status in default_statuses:
        await db.execute(text("""
            INSERT INTO lead_status_settings (company_id, emoji, name, coins, sort_order, is_final)
            VALUES (:cid, :emoji, :name, :coins, :sort, :final)
        """), {
            'cid': company_id, 'emoji': status['emoji'], 'name': status['name'],
            'coins': status['coins'], 'sort': status['sort_order'], 'final': status['is_final']
        })

@router.post("/", response_model=CompanyResponse)
@limiter.limit("10/minute")
async def create_company(request: Request, company: CompanyCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.subdomain == company.subdomain))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Subdomain already exists")
    new_company = Company(name=company.name, subdomain=company.subdomain, default_language=company.default_language)
    db.add(new_company)
    await db.commit()
    await db.refresh(new_company)
    default_config = SalesAgentConfig(company_id=new_company.id)
    db.add(default_config)
    
    # Создать дефолтные статусы
    await create_default_statuses(db, new_company.id)
    
    await db.commit()
    return new_company

@router.get("/{company_id}", response_model=CompanyResponse)
@limiter.limit("30/minute")
async def get_company(request: Request, company_id: int, db: AsyncSession = Depends(get_db)):
    # Fix N+1 with selectinload
    from sqlalchemy.orm import selectinload
    result = await db.execute(select(Company).options(selectinload(Company.leads)).where(Company.id == company_id))
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company
