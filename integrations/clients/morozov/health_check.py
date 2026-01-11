"""Проверка статуса всех систем"""
import httpx
from loguru import logger


async def check_all_systems(onec_url: str, onec_user: str, onec_pass: str, 
                           bitrix_url: str, db_url: str) -> str:
    """Проверка всех систем"""
    result = "📊 *СТАТУС СИСТЕМЫ*\n\n"
    
    # 1С OData
    try:
        async with httpx.AsyncClient(timeout=10.0, auth=(onec_user, onec_pass)) as client:
            resp = await client.get(f"{onec_url}/odata/standard.odata/$metadata")
            if resp.status_code == 200:
                result += "✅ *1С OData:* Подключено\n"
            else:
                result += f"⚠️ *1С OData:* Код {resp.status_code}\n"
    except Exception as e:
        result += f"❌ *1С OData:* {str(e)[:30]}\n"
    
    # Bitrix24
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{bitrix_url}/profile")
            if resp.status_code == 200:
                result += "✅ *Bitrix24:* Подключено\n"
            else:
                result += f"⚠️ *Bitrix24:* Код {resp.status_code}\n"
    except Exception as e:
        result += f"❌ *Bitrix24:* {str(e)[:30]}\n"
    
    # PostgreSQL
    try:
        import asyncpg
        # Парсим URL
        conn = await asyncpg.connect(db_url, timeout=5)
        count = await conn.fetchval("SELECT COUNT(*) FROM bitrix_1c_product_mapping")
        await conn.close()
        result += f"✅ *База данных:* ОК ({count} товаров)\n"
    except Exception as e:
        result += f"❌ *База данных:* {str(e)[:30]}\n"
    
    result += "\n_Проверено только что_"
    return result
