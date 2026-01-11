"""Telegram бот для уведомлений и команд"""
import httpx
from loguru import logger


class TelegramBot:
    """Telegram бот для уведомлений"""
    
    def __init__(self, token: str, chat_id: str = None):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def send_message(self, text: str, chat_id: str = None):
        """Отправить сообщение"""
        target_chat = chat_id or self.chat_id
        
        if not target_chat:
            logger.warning("Chat ID not provided")
            return False
        
        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                "chat_id": target_chat,
                "text": text,
                "parse_mode": "Markdown"
            }
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            logger.info(f"Message sent to Telegram")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def notify_order_created(self, deal_id: str, order_number: str, customer: str):
        """Уведомление о создании накладной"""
        message = f"""✅ *Новая накладная в 1С*

📋 Сделка: `{deal_id}`
📄 Накладная: `{order_number}`
👤 Клиент: {customer}"""
        await self.send_message(message)
    
    async def notify_sync_completed(self, updated: int, errors: int):
        """Уведомление о синхронизации"""
        emoji = "✅" if errors == 0 else "⚠️"
        message = f"""{emoji} *Синхронизация остатков*

📦 Обновлено: {updated}
❌ Ошибок: {errors}"""
        await self.send_message(message)
    
    async def notify_error(self, error_text: str):
        """Уведомление об ошибке"""
        message = f"""🚨 *Ошибка системы*

`{error_text}`"""
        await self.send_message(message)
    
    async def close(self):
        await self.client.aclose()
