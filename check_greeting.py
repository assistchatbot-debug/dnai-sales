#!/usr/bin/env python3
import asyncio
from sqlalchemy import text
from database import get_db_session

async def check():
    async with get_db_session() as db:
        result = await db.execute(text("""
            SELECT 
                greeting_message,
                greeting_ru,
                greeting_en,
                greeting_kz
            FROM social_widgets 
            WHERE channel_name='instagram' AND company_id=1
        """))
        widget = result.fetchone()
        if widget:
            print("=== Приветствия в БД ===")
            print(f"greeting_message: {widget[0]}")
            print(f"greeting_ru: {widget[1]}")
            print(f"greeting_en: {widget[2]}")
            print(f"greeting_kz: {widget[3]}")
        else:
            print("Виджет не найден")

asyncio.run(check())
