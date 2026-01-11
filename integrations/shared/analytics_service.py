"""Сервис аналитики продаж - универсальный для всех CRM"""
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict


class AnalyticsService:
    """Аналитика продаж (Bitrix24/KOMMO)"""
    
    def __init__(self, crm_client):
        self.crm = crm_client
        self._user_cache = {}
    
    def _get_period_dates(self, period: str) -> tuple:
        """Даты начала и конца периода"""
        today = datetime.now()
        if period == 'day':
            date_from = today.strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        elif period == 'week':
            date_from = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        else:  # month
            date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        return date_from, date_to
    
    async def get_user_name(self, user_id: str) -> str:
        """Получить имя пользователя с кэшированием"""
        if user_id not in self._user_cache:
            user = await self.crm.get_user(user_id)
            name = f"{user.get('NAME', '')} {user.get('LAST_NAME', '')}".strip()
            self._user_cache[user_id] = name or f"ID:{user_id}"
        return self._user_cache[user_id]
    
    async def get_sales_report(self, period: str) -> Dict:
        """Отчёт по продажам за период"""
        date_from, date_to = self._get_period_dates(period)
        deals = await self.crm.get_won_deals(date_from, date_to)
        
        managers = defaultdict(lambda: {"sum": 0, "count": 0})
        total_sum = 0
        
        for deal in deals:
            manager_id = str(deal.get("ASSIGNED_BY_ID", "0"))
            amount = float(deal.get("OPPORTUNITY", 0))
            managers[manager_id]["sum"] += amount
            managers[manager_id]["count"] += 1
            total_sum += amount
        
        # Добавляем имена менеджеров
        for manager_id in managers:
            managers[manager_id]["name"] = await self.get_user_name(manager_id)
        
        # Сортируем по сумме
        sorted_managers = sorted(managers.items(), key=lambda x: x[1]["sum"], reverse=True)
        
        return {
            "period": period,
            "date_from": date_from,
            "date_to": date_to,
            "total_sum": total_sum,
            "deals_count": len(deals),
            "managers": sorted_managers
        }
    
    async def get_top_products(self, period: str, limit: int = 5) -> Dict:
        """Топ товаров за период"""
        date_from, date_to = self._get_period_dates(period)
        deals = await self.crm.get_won_deals(date_from, date_to)
        
        products = defaultdict(lambda: {"qty": 0, "sum": 0, "name": ""})
        
        for deal in deals:
            deal_products = await self.crm.get_deal_products(deal["ID"])
            for p in deal_products:
                prod_id = str(p.get("PRODUCT_ID", "0"))
                qty = float(p.get("QUANTITY", 1))
                price = float(p.get("PRICE", 0))
                products[prod_id]["qty"] += qty
                products[prod_id]["sum"] += qty * price
                products[prod_id]["name"] = p.get("PRODUCT_NAME", f"Товар {prod_id}")
        
        # Сортируем по количеству
        sorted_products = sorted(products.items(), key=lambda x: x[1]["qty"], reverse=True)[:limit]
        
        total_qty = sum(p["qty"] for _, p in sorted_products)
        
        return {
            "period": period,
            "date_from": date_from,
            "date_to": date_to,
            "products": sorted_products,
            "total_qty": total_qty
        }
