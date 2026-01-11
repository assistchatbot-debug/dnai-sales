#!/usr/bin/env python3
"""Тест подключения к рабочей 1С"""
import httpx
import re

# Рабочая база на том же сервере
ONEC_URL = "http://2.133.147.210:8081/company-TOO_H&B_Technology"
ONEC_USER = "odata.user"
ONEC_PASS = "odata12345#"

async def test_connection():
    """Проверка подключения"""
    print(f"🔌 Подключение к: {ONEC_URL}/odata/standard.odata/")
    
    async with httpx.AsyncClient(timeout=10.0, auth=(ONEC_USER, ONEC_PASS)) as client:
        # 1. Проверка metadata
        try:
            resp = await client.get(f"{ONEC_URL}/odata/standard.odata/$metadata")
            if resp.status_code == 200:
                print("✅ OData подключен!")
            else:
                print(f"❌ Ошибка подключения: {resp.status_code}")
                print(resp.text[:500])
                return
        except Exception as e:
            print(f"❌ Не удалось подключиться: {e}")
            return
        
        # 2. Получаем товары с артикулами
        print("\n📦 Получаю товары с артикулами...")
        url = f"{ONEC_URL}/odata/standard.odata/Catalog_%D0%9D%D0%BE%D0%BC%D0%B5%D0%BD%D0%BA%D0%BB%D0%B0%D1%82%D1%83%D1%80%D0%B0?$top=10"
        resp = await client.get(url)
        
        if resp.status_code != 200:
            print(f"❌ Ошибка получения товаров: {resp.status_code}")
            print(resp.text[:500])
            return
        
        # Парсим товары
        codes = re.findall(r'<d:Code>([^<]+)</d:Code>', resp.text)
        artikuls = re.findall(r'<d:Артикул>([^<]*)</d:Артикул>', resp.text)
        names = re.findall(r'<d:Description>([^<]+)</d:Description>', resp.text)
        
        print(f"\n✅ Найдено {len(codes)} товаров:\n")
        for i, (code, art, name) in enumerate(zip(codes, artikuls, names), 1):
            art_status = f"✅ {art}" if art else "❌ пусто"
            print(f"{i}. Код: {code} | Артикул: {art_status} | Название: {name[:40]}")
        
        # Статистика
        filled = sum(1 for a in artikuls if a.strip())
        print(f"\n📊 Артикулов заполнено: {filled}/{len(artikuls)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_connection())
