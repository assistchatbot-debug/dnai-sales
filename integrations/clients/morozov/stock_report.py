"""Скрипт для отправки остатков в Telegram"""
import httpx
import re
import os
from collections import defaultdict
from loguru import logger


async def get_stock_report(onec_url: str, onec_user: str, onec_pass: str) -> str:
    """Получить отчёт по остаткам из 1С"""
    
    async with httpx.AsyncClient(timeout=60.0, auth=(onec_user, onec_pass)) as client:
        # Получаем записи регистра
        url = f"{onec_url}/odata/standard.odata/AccumulationRegister_%D0%A2%D0%BE%D0%B2%D0%B0%D1%80%D1%8B%D0%9E%D1%80%D0%B3%D0%B0%D0%BD%D0%B8%D0%B7%D0%B0%D1%86%D0%B8%D0%B9%D0%91%D0%A3_RecordType?$top=200"
        resp = await client.get(url)
        
        if resp.status_code != 200:
            return "❌ Ошибка получения остатков из 1С"
        
        # Агрегируем по товарам
        stock = defaultdict(float)
        товар_matches = re.findall(r'<d:Товар_Key>([^<]+)</d:Товар_Key>', resp.text)
        кол_matches = re.findall(r'<d:Количество>([^<]+)</d:Количество>', resp.text)
        type_matches = re.findall(r'<d:RecordType>([^<]+)</d:RecordType>', resp.text)
        
        for tovar_key, qty, rec_type in zip(товар_matches, кол_matches, type_matches):
            q = float(qty)
            if rec_type == 'Receipt':
                stock[tovar_key] += q
            else:
                stock[tovar_key] -= q
        
        # Получаем названия товаров (первые 20)
        names = {}
        for key in list(stock.keys())[:25]:
            if stock[key] > 0:
                try:
                    nom_url = f"{onec_url}/odata/standard.odata/Catalog_%D0%9D%D0%BE%D0%BC%D0%B5%D0%BD%D0%BA%D0%BB%D0%B0%D1%82%D1%83%D1%80%D0%B0(guid'{key}')?$select=Description"
                    r = await client.get(nom_url)
                    if r.status_code == 200:
                        m = re.search(r'<d:Description>([^<]+)</d:Description>', r.text)
                        if m:
                            names[key] = m.group(1)
                except:
                    pass
        
        # Формируем отчёт
        result = "📦 *ОСТАТКИ ТОВАРОВ 1С*\n\n"
        count = 0
        for key, qty in sorted(stock.items(), key=lambda x: -x[1]):
            if qty > 0 and count < 15:
                name = names.get(key, key[:8])[:35]
                result += f"• `{qty:.0f}` шт - {name}\n"
                count += 1
        
        positive_stock = sum(1 for q in stock.values() if q > 0)
        result += f"\n_Всего позиций с остатком: {positive_stock}_"
        
        return result
