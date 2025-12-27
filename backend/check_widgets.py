#!/usr/bin/env python3
import asyncio
from sqlalchemy import text
from database import get_db_session

async def check():
    async with get_db_session() as db:
        result = await db.execute(text("SELECT id, company_id, channel_name, is_active FROM social_widgets"))
        widgets = result.fetchall()
        print("=== Виджеты в БД ===")
        for w in widgets:
            print(f"ID: {w[0]}, Company: {w[1]}, Channel: '{w[2]}', Active: {w[3]}")

asyncio.run(check())
