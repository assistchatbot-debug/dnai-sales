"""Telegram бот для уведомлений и аналитики"""
import httpx
import json
from loguru import logger
from shared.analytics_service import AnalyticsService


class TelegramBot:
    """Telegram бот для уведомлений и аналитики"""
    
    def __init__(self, token: str, chat_id: str = None, crm_client=None):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.client = httpx.AsyncClient(timeout=30.0)
        self.analytics = AnalyticsService(crm_client) if crm_client else None
    
    def get_analytics_keyboard(self):
        """Клавиатура аналитики"""
        return {
            "inline_keyboard": [
                [{"text": "📈 Статус", "callback_data": "status"}],
                [{"text": "💰 Продажи за день", "callback_data": "sales_day"}],
                [{"text": "💰 Продажи за неделю", "callback_data": "sales_week"}],
                [{"text": "💰 Продажи за месяц", "callback_data": "sales_month"}],
                [{"text": "🏆 Товары недели", "callback_data": "top_week"}],
                [{"text": "🏆 Товары месяца", "callback_data": "top_month"}]
            ]
        }
    
    async def send_message(self, text: str, chat_id: str = None, reply_markup: dict = None):
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
            if reply_markup:
                payload["reply_markup"] = json.dumps(reply_markup)
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            logger.info("Message sent to Telegram")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def send_analytics_menu(self, chat_id: str = None):
        """Отправить меню аналитики"""
        await self.send_message(
            "📊 *Аналитика продаж*\n\nВыберите отчёт:",
            chat_id,
            self.get_analytics_keyboard()
        )
    
    async def handle_callback(self, callback_data: str, chat_id: str):
        """Обработка нажатий кнопок"""
        if not self.analytics:
            await self.send_message("❌ Аналитика недоступна", chat_id)
            return
        
        if callback_data == "status":
            await self.send_message("✅ Система работает", chat_id)
        
        elif callback_data.startswith("sales_"):
            period = callback_data.split("_")[1]
            await self.send_sales_report(period, chat_id)
        
        elif callback_data.startswith("top_"):
            period = callback_data.split("_")[1]
            await self.send_top_products(period, chat_id)
    
    async def send_sales_report(self, period: str, chat_id: str):
        """Отправка отчёта по продажам"""
        try:
            await self.send_message("⏳ Загружаю данные...", chat_id)
            report = await self.analytics.get_sales_report(period)
            
            period_names = {"day": "день", "week": "неделю", "month": "месяц"}
            
            msg = f"💰 *Продажи за {period_names.get(period, period)}*\n"
            msg += f"📅 {report['date_from']} — {report['date_to']}\n\n"
            msg += f"📊 Общая сумма: *{report['total_sum']:,.0f} ₸*\n"
            msg += f"📦 Сделок: {report['deals_count']}\n\n"
            msg += "👥 *Менеджеры:*\n"
            
            for i, (_, m) in enumerate(report['managers'][:10], 1):
                msg += f"{i}. {m['name']} — {m['sum']:,.0f} ₸ ({m['count']} сд.)\n"
            
            await self.send_message(msg, chat_id)
        except Exception as e:
            logger.error(f"Sales report error: {e}")
            await self.send_message(f"❌ Ошибка: {e}", chat_id)
    
    async def send_top_products(self, period: str, chat_id: str):
        """Отправка топ товаров"""
        try:
            await self.send_message("⏳ Загружаю данные...", chat_id)
            report = await self.analytics.get_top_products(period, limit=5)
            
            period_names = {"week": "неделю", "month": "месяц"}
            
            msg = f"🏆 *Топ-5 товаров за {period_names.get(period, period)}*\n"
            msg += f"📅 {report['date_from']} — {report['date_to']}\n\n"
            
            for i, (_, p) in enumerate(report['products'], 1):
                msg += f"{i}. {p['name']} — {p['qty']:.0f} шт / {p['sum']:,.0f} ₸\n"
            
            msg += f"\n📊 Всего продано: {report['total_qty']:.0f} шт"
            
            await self.send_message(msg, chat_id)
        except Exception as e:
            logger.error(f"Top products error: {e}")
            await self.send_message(f"❌ Ошибка: {e}", chat_id)
    
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
        message = f"🚨 *Ошибка:* `{error_text}`"
        await self.send_message(message)
    
    async def close(self):
        await self.client.aclose()
