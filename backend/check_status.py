#!/usr/bin/env python3
import asyncio
from sqlalchemy import text
from database import get_db_session

async def check():
    async with get_db_session() as db:
        result = await db.execute(text("SELECT is_active FROM social_widgets WHERE channel_name='instagram'"))
        widget = result.fetchone()
        print(f"is_active = {widget[0]}")

asyncio.run(check())
