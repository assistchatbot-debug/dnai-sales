import asyncio
from sqlalchemy import text
from database import get_db_session

async def delete_empty():
    async with get_db_session() as db:
        # Count empty leads
        result = await db.execute(text("""
            SELECT COUNT(*) FROM leads 
            WHERE contact_info IS NULL 
               OR contact_info->>'name' IS NULL 
               OR contact_info->>'phone' IS NULL
        """))
        count = result.scalar()
        print(f"Found {count} empty leads")
        
        # Delete them
        await db.execute(text("""
            DELETE FROM leads 
            WHERE contact_info IS NULL 
               OR (contact_info->>'name' IS NULL AND contact_info->>'phone' IS NULL)
        """))
        await db.commit()
        print(f"✅ Deleted empty leads")

asyncio.run(delete_empty())
