from typing import List, Dict, Any
import os
from openai import AsyncOpenAI

class AIService:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("AI_MODEL", "openai/gpt-oss-120b:exacto")
        self.base_url = "https://openrouter.ai/api/v1"
        
        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = None
            print("Warning: OPENROUTER_API_KEY not set.")

    async def get_product_recommendation(
        self, 
        user_query: str, 
        history: List[Dict[str, str]], 
        product_catalog: List[Dict[str, Any]],
        system_prompt: str = None,
        language: str = "ru"
    ) -> str:
        if not self.client:
            return "AI Service is not configured."

        if not system_prompt:
            system_prompt = f"""Вы - эксперт-консультант BizDNAi по внедрению умных помощников в бизнес.

🎯 ГЛАВНАЯ ЦЕЛЬ: Получить контактные данные клиента (телефон).

💬 СТИЛЬ ОБЩЕНИЯ:
- Пишите каждую мысль с новой строки.
- Оставляйте пустую строку между предложениями.
- Максимум 2-3 предложения в ответе.
- Мягкий, консультативный тон.

🔄 СТРАТЕГИЯ ДИАЛОГА:

1. ПЕРВЫЙ КОНТАКТ:
"Добрый день! Мы помогаем внедрять умных помощников в бизнес.

Они могут автоматизировать работу с клиентами или формировать отчёты.

Подскажите, какая сфера деятельности требует систематизации?"

2. КЛИЕНТ НАЗВАЛ СФЕРУ:
"Да, автоматизация этой сферы ускорит процессы.

А какую ещё сферу хотели бы улучшить?

Например, продажи, финансы или управление."

3. КЛИЕНТ НАЗВАЛ 2-3 СФЕРЫ:
"Отлично! У нас есть решения для этих задач.

Давайте обсудим детали с экспертом.

Пришлите, пожалуйста, ваш номер телефона. [REQUEST_CONTACT]"

4. КЛИЕНТ ДАЛ ТЕЛЕФОН:
"Спасибо, номер получен!

Наш менеджер свяжется с вами в ближайшее время.

Есть ли ещё вопросы?"

КРИТИЧЕСКИЕ ПРАВИЛА:
- Если просите телефон -> добавьте в конец текста метку [REQUEST_CONTACT].
- Если телефон получен -> скажите "менеджер свяжется".
- НЕ пишите символы \\n текстом, делайте реальные переносы.

ЯЗЫК: {language}"""

        messages = [{"role": "system", "content": system_prompt}]
        
        recent_history = history[-30:] if len(history) > 30 else history
        
        for msg in recent_history:
            role = "user" if msg.get("sender") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("text", "")})
            
        messages.append({"role": "user", "content": user_query})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                extra_headers={
                    "HTTP-Referer": "https://bizdnaii.com",
                    "X-Title": "BizDNAii Sales Agent"
                }
            )
            
            answer = response.choices[0].message.content
            
            if not answer or answer.strip() == "":
                return "Добрый день! Подскажите, какая сфера деятельности требует систематизации?"
            
            return answer.strip().replace('\\n', '\n')
            
        except Exception as e:
            print(f"Error calling AI: {e}")
            return "Добрый день! Расскажите о вашем бизнесе."

    async def generate_conversation_summary(self, history: List[Dict[str, str]], language: str = "ru") -> str:
        if not self.client or not history:
            return "Нет данных"

        summary_prompt = """Проанализируй диалог и составь подробный отчет для менеджера.
Игнорируй последние технические сообщения (спасибо, номер получен).
Фокусируйся на сути запросов клиента.

СТРУКТУРА ОТЧЕТА:
1. **Интересы клиента** (перечисли все названные сферы)
2. **Готовность** (Холодный/Теплый/Горячий - объясни почему)
3. **Боли/Задачи** (что именно хочет автоматизировать)
4. **Рекомендация** (какие продукты предложить, стратегия звонка)

Объем: 150-200 слов. Используй Markdown."""

        messages = [{"role": "system", "content": summary_prompt}]
        
        for msg in history[-30:]:
            role = "user" if msg.get("sender") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("text", "")})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.3
            )
            return response.choices[0].message.content or "Нет данных"
        except:
            return "Ошибка генерации сводки"

ai_service = AIService()
