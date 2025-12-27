#!/usr/bin/env python3
"""Safely add greeting columns using existing DB connection"""
import asyncio
from sqlalchemy import text
from database import get_db_session

async def add_columns():
    print("🔧 Adding multilingual greeting columns...")
    
    async with get_db_session() as db:
        try:
            # Безопасное добавление колонок (IF NOT EXISTS)
            await db.execute(text("""
                ALTER TABLE social_widgets 
                ADD COLUMN IF NOT EXISTS greeting_ru TEXT,
                ADD COLUMN IF NOT EXISTS greeting_en TEXT,
                ADD COLUMN IF NOT EXISTS greeting_kz TEXT,
                ADD COLUMN IF NOT EXISTS greeting_ky TEXT,
                ADD COLUMN IF NOT EXISTS greeting_uz TEXT,
                ADD COLUMN IF NOT EXISTS greeting_uk TEXT
            """))
            
            # Копировать существующие данные в greeting_ru
            result = await db.execute(text("""
                UPDATE social_widgets 
                SET greeting_ru = greeting_message 
                WHERE greeting_ru IS NULL AND greeting_message IS NOT NULL
            """))
            
            await db.commit()
            print(f"✅ Колонки добавлены успешно")
            print(f"✅ Скопировано {result.rowcount} существующих приветствий в greeting_ru")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(add_columns())
