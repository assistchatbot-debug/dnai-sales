#!/usr/bin/env python3
import asyncio
from sqlalchemy import text
from database import get_db_session

async def reactivate():
    async with get_db_session() as db:
        await db.execute(text("""
            UPDATE social_widgets 
            SET is_active = true 
            WHERE channel_name='instagram' AND company_id=1
        """))
        await db.commit()
        print("✅ Виджет реактивирован")

asyncio.run(reactivate())
