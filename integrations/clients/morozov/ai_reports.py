"""ИИ-модуль для генерации отчётов через OpenRouter"""
import httpx
from typing import Dict, List
from loguru import logger
from config import settings
from bitrix24_client import Bitrix24Client
from datetime import datetime, timedelta


class AIReportsService:
    """Сервис для генерации аналитических отчётов с помощью ИИ"""
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_model
        self.client = httpx.AsyncClient(timeout=60.0)
        self.bitrix24 = Bitrix24Client()
    
    async def _call_openrouter(self, messages: List[Dict]) -> str:
        """Вызов OpenRouter API"""
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages
        }
        
        try:
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error calling OpenRouter: {e}")
            raise
    
    async def generate_report(self, query: str) -> str:
        """Генерация отчёта на основе запроса на естественном языке"""
        logger.info(f"Generating AI report for query: {query}")
        
        # Определяем временной диапазон (по умолчанию - последняя неделя)
        date_to = datetime.now()
        date_from = date_to - timedelta(days=7)
        
        # Формируем контекст для ИИ
        context = f"""
У тебя есть данные о сделках из CRM системы Bitrix24 за период с {date_from.strftime('%d.%m.%Y')} по {date_to.strftime('%d.%m.%Y')}.

Пользователь задал вопрос: "{query}"

Проанализируй данные и предоставь детальный отчёт. Включи:
1. Прямой ответ на вопрос
2. Статистику и цифры
3. Выводы и рекомендации (если применимо)

Форматируй ответ в читаемом виде.
"""
        
        messages = [
            {
                "role": "system",
                "content": "Ты - аналитик данных, специализирующийся на анализе продаж. Предоставляй точные, структурированные отчёты."
            },
            {
                "role": "user",
                "content": context
            }
        ]
        
        # Получаем ответ от ИИ
        report = await self._call_openrouter(messages)
        logger.info("AI report generated successfully")
        
        return report
    
    async def close(self):
        """Закрыть HTTP клиенты"""
        await self.client.aclose()
        await self.bitrix24.close()
