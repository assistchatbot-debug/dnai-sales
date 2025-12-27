#!/usr/bin/env python3
import asyncio
from sqlalchemy import text
from database import get_db_session

async def update():
    async with get_db_session() as db:
        # Get all widgets and update their URLs
        result = await db.execute(text("SELECT id, company_id FROM social_widgets WHERE is_active=true"))
        widgets = result.fetchall()
        
        for w in widgets:
            widget_id = w[0]
            company_id = w[1]
            new_url = f"https://bizdnai.com/w/{company_id}/{widget_id}"
            await db.execute(text(f"UPDATE social_widgets SET url='{new_url}' WHERE id={widget_id}"))
            print(f"✅ Updated widget {widget_id}: {new_url}")
        
        await db.commit()
        print("\n✅ All URLs updated!")

asyncio.run(update())
