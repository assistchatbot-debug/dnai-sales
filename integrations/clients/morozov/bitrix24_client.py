"""Клиент для работы с Bitrix24 REST API"""
import httpx
from typing import Dict, List, Optional, Any
from loguru import logger
from config import settings


class Bitrix24Client:
    """Клиент для взаимодействия с Bitrix24"""
    
    def __init__(self):
        self.webhook_url = settings.bitrix24_webhook_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def _call_method(self, method: str, params: Dict = None) -> Dict:
        """Вызов метода REST API Bitrix24"""
        url = f"{self.webhook_url}/{method}"
        try:
            response = await self.client.post(url, json=params or {})
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                logger.error(f"Bitrix24 API error: {data['error_description']}")
                raise Exception(f"Bitrix24 API error: {data['error_description']}")
            
            return data.get("result", {})
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling Bitrix24: {e}")
            raise
    
    async def get_deal(self, deal_id: str) -> Dict:
        """Получить данные сделки"""
        logger.info(f"Getting deal {deal_id} from Bitrix24")
        return await self._call_method("crm.deal.get", {"id": deal_id})
    
    async def get_deal_products(self, deal_id: str) -> List[Dict]:
        """Получить товары из сделки"""
        logger.info(f"Getting products for deal {deal_id}")
        result = await self._call_method("crm.deal.productrows.get", {"id": deal_id})
        return result if isinstance(result, list) else []
    
    async def get_product(self, product_id: str) -> Dict:
        """Get full product info from Bitrix24"""
        logger.info(f"Getting product {product_id} from Bitrix24")
        return await self._call_method("crm.product.get", {"id": product_id})
    
    async def get_contact(self, contact_id: str) -> Dict:
        """Получить данные контакта"""
        logger.info(f"Getting contact {contact_id}")
        return await self._call_method("crm.contact.get", {"id": contact_id})
    
    async def update_deal_field(self, deal_id: str, field_name: str, value: Any) -> bool:
        """Обновить поле сделки"""
        logger.info(f"Updating deal {deal_id} field {field_name}")
        try:
            await self._call_method("crm.deal.update", {
                "id": deal_id,
                "fields": {field_name: value}
            })
            return True
        except Exception as e:
            logger.error(f"Failed to update deal field: {e}")
            return False
    
    async def update_product_quantity(self, product_id: str, quantity: int) -> bool:
        """Обновить остаток товара в каталоге"""
        logger.info(f"Updating product {product_id} quantity to {quantity}")
        try:
            await self._call_method("catalog.product.update", {
                "id": product_id,
                "fields": {
                    "quantity": quantity
                }
            })
            return True
        except Exception as e:
            logger.error(f"Failed to update product quantity: {e}")
            return False
    
    async def create_activity(self, deal_id: str, subject: str, description: str) -> bool:
        """Создать активность (комментарий) к сделке"""
        logger.info(f"Creating activity for deal {deal_id}")
        try:
            await self._call_method("crm.activity.add", {
                "fields": {
                    "OWNER_TYPE_ID": 2,
                    "OWNER_ID": deal_id,
                    "TYPE_ID": 4,
                    "SUBJECT": subject,
                    "DESCRIPTION": description,
                    "COMPLETED": "Y",
                    "DIRECTION": 2
                }
            })
            return True
        except Exception as e:
            logger.error(f"Failed to create activity: {e}")
            return False
    
    async def add_deal_comment(self, deal_id: str, comment: str):
        """Add comment to deal timeline"""
        logger.info(f"Adding comment to deal {deal_id}")
        return await self._call_method("crm.timeline.comment.add", {
            "fields": {
                "ENTITY_ID": deal_id,
                "ENTITY_TYPE": "deal",
                "COMMENT": comment
            }
        })
    

    async def get_won_deals(self, date_from: str, date_to: str) -> List[Dict]:
        """Получить выигранные сделки за период"""
        logger.info(f"Getting won deals from {date_from} to {date_to}")
        result = await self._call_method("crm.deal.list", {
            "filter": {
                "STAGE_ID": "WON",
                ">=CLOSEDATE": date_from,
                "<=CLOSEDATE": date_to
            },
            "select": ["ID", "TITLE", "OPPORTUNITY", "ASSIGNED_BY_ID", "CLOSEDATE"]
        })
        return result if isinstance(result, list) else []
    
    async def get_user(self, user_id: str) -> Dict:
        """Получить данные пользователя"""
        result = await self._call_method("user.get", {"ID": user_id})
        return result[0] if result else {}

    async def close(self):
        """Закрыть HTTP клиент"""
        await self.client.aclose()
