#!/usr/bin/env python3
import asyncio
from sqlalchemy import text
from database import get_db_session

async def check():
    async with get_db_session() as db:
        result = await db.execute(text("""
            SELECT id, channel_name, is_active, 
                   LEFT(greeting_message, 30) as greeting_preview
            FROM social_widgets 
            WHERE company_id = 1
            ORDER BY id
        """))
        widgets = result.fetchall()
        print("=== Виджеты в БД ===")
        for w in widgets:
            status = "✅" if w[2] else "❌"
            print(f"{status} ID={w[0]}, Channel={w[1]}, Active={w[2]}, Greeting={w[3]}...")

asyncio.run(check())
