#!/usr/bin/env python3
import asyncio
from sqlalchemy import text
from database import get_db_session

async def check():
    async with get_db_session() as db:
        result = await db.execute(text("SELECT id, channel_name, is_active, greeting_ru FROM social_widgets WHERE channel_name='instagram'"))
        widget = result.fetchone()
        if widget:
            print(f"Виджет найден: ID={widget[0]}, Active={widget[2]}, Greeting={widget[3][:50] if widget[3] else 'None'}...")
        else:
            print("Виджет НЕ найден в БД")

asyncio.run(check())
