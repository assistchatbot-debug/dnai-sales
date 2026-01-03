import logging
from typing import List, Dict, Any
import os
import aiohttp
from openai import AsyncOpenAI

# OpenRouter для анализа (не Flowise)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "openai/gpt-oss-120b:exacto" 

class AIService:
    def __init__(self, company_id: int = None, ai_endpoint: str = None, ai_api_key: str = None):
        # Priority: 1) Provided params 2) .env fallback
        self.agent_url = ai_endpoint or os.getenv("AI_AGENT_URL")
        self.agent_key = ai_api_key or os.getenv("AI_AGENT_KEY")
        self.company_id = company_id
        
        if self.agent_url and self.agent_key:
            self.client = AsyncOpenAI(
                api_key=self.agent_key, 
                base_url=self.agent_url + "/api/v1/"
            )
            source = "DB" if (ai_endpoint and ai_api_key) else ".env"
            print(f"✅ AI Agent configured from {source}: {self.agent_url[:50]}...")
        else:
            self.client = None
            print("⚠️ AI Agent not configured - check company AI settings or .env")

    async def get_product_recommendation(self, user_query: str, history: List[Dict[str, str]], product_catalog: List[Dict[str, Any]], system_prompt: str = None, language: str = "ru") -> str:
        # 🤖 MULTITENANCY LOG для КАЖДОГО запроса
        source = "DB" if self.company_id else ".env"
        logging.info(f"🤖 MULTITENANCY AI REQUEST from {source}, company_id={self.company_id}")
        
        if not self.client:
            return "AI Agent not configured."
        
        # Build messages for agent - send ONLY user messages
        # Agent has its own flow, don't confuse it with our bot responses
        messages = []
        
        # Add BOTH user AND assistant messages from history
        for msg in history[-20:]:
            text = msg.get("text", "")
            if text and text not in ['received', 'sent']:
                role = "user" if msg.get("sender") == "user" else "assistant"
                messages.append({"role": role, "content": text})
        
        # Add current user message with lang parameter
        import json
        # Map language codes (kz -> kk for Kazakh)
        lang_map = {'kz': 'kk', 'ky': 'ky', 'uz': 'uz', 'uk': 'uk', 'en': 'en', 'ru': 'ru'}
        mapped_lang = lang_map.get(language, 'ru')
        msg_with_lang = json.dumps({"message": user_query, "lang": mapped_lang}, ensure_ascii=False)
        messages.append({"role": "user", "content": msg_with_lang})
        
        # Debug logging
        print(f"🔍 History: {len(history)} messages")
        print(f"🔍 Last 3: {[m.get('text','')[:40] for m in history[-3:]]}")
        print(f"🔍 Sending to AI: {msg_with_lang[:100]}")
        
        # DEBUG: Log FULL conversation being sent to AI
        logging.info(f"🔍 AI Debug: Sending {len(messages)} messages to {self.agent_url[:50]}")
        logging.info(f"📨 FULL MESSAGES TO AI:")
        for i, msg in enumerate(messages):
            role = msg.get('role', '?')
            text = msg.get('content', '')[:100]  # First 100 chars
            logging.info(f"   [{i}] {role}: {text}")
        
        try:
            response = await self.client.chat.completions.create(
                model="n/a",
                messages=messages,
                extra_body={"include_retrieval_info": False}
            )
            
            if not response.choices or not response.choices[0].message:
                print("⚠️ AI empty response")
                return "Какую сферу хотели бы автоматизировать?"
            
            answer = response.choices[0].message.content
            print(f"✅ AI response: {answer[:50]}...")
            return answer.strip() if answer else "Какую сферу хотели бы автоматизировать?"
            
        except Exception as e:
            print(f"❌ AI Error: {e}")
            return "Какую сферу хотели бы автоматизировать?"

    async def generate_conversation_summary(self, history: List[Dict[str, str]], language: str = "ru", manager_language: str = "ru") -> str:
        """Generate summary using OpenRouter API (not Flowise agent)"""
        if not history:
            return "Нет данных для анализа"
        
        print(f"📊 Generating summary for {len(history)} messages via OpenRouter")
        
        # Язык отчёта
        lang_names = {'ru': 'русском', 'en': 'английском', 'kz': 'казахском', 'ky': 'кыргызском', 'uz': 'узбекском', 'uk': 'украинском'}
        lang_text = lang_names.get(manager_language, 'русском')
        
        # Build prompt for summary
        summary_prompt = f"""Проанализируй диалог с клиентом и создай детальный отчёт для менеджера.
ВАЖНО: Отчёт должен быть СТРОГО на {lang_text} языке!

## КРИТЕРИИ ОПРЕДЕЛЕНИЯ ГОТОВНОСТИ ЛИДА:

### 🔥 ГОРЯЧИЙ лид:
- Быстро даёт имя и телефон без уговоров
- Отвечает на вопросы оперативно и развёрнуто
- Явно выражает желание воспользоваться услугами
- Интересуется ценами, сроками, условиями сотрудничества
- Минимум возражений, готов к следующему шагу

### 🌡️ ТЁПЛЫЙ лид:
- Отвечает, но с паузами, не сразу
- Задаёт уточняющие/дополнительные вопросы
- Даёт имя и телефон, но после нескольких сообщений
- Проявляет интерес, но ещё сравнивает варианты
- Есть небольшие сомнения или вопросы

### ❄️ ХОЛОДНЫЙ лид:
- Отвечает неохотно, односложно
- Задаёт много вопросов, но не даёт информацию о себе
- Не даёт имя и/или телефон, или даёт с большим сопротивлением
- Не выражает явного интереса к услугам
- Много возражений, скептицизм

## ФОРМАТ ОТЧЁТА:

### 1. Температура лида
[Горячий/Тёплый/Холодный] — краткое обоснование (1-2 предложения)

### 2. Контактные данные
- Имя: [указано/не указано]
- Телефон: [указан/не указан]
- Как охотно дал данные: [сразу/после уговоров/отказался]

### 3. Интересы клиента
- Какие сферы/услуги интересуют
- Конкретные задачи или боли клиента

### 4. На что обратить внимание менеджеру
- Ключевые возражения или сомнения клиента
- Что НЕ вызвало интерес (если упоминалось)
- Триггерные точки для продажи

### 5. Рекомендация по дальнейшим действиям
- Конкретный следующий шаг для менеджера

Объём: 150-250 слов. Пиши по делу, без воды."""

        # Формируем историю диалога
        dialog_text = ""
        for msg in history[-30:]:
            role = "Клиент" if msg.get("sender") == "user" else "Бот"
            dialog_text += f"{role}: {msg.get('text', '')}\n"
        
        messages = [
            {"role": "system", "content": summary_prompt},
            {"role": "user", "content": f"Вот диалог для анализа:\n\n{dialog_text}"}
        ]
        
        logging.info(f"🔍 OpenRouter: Sending summary request, lang={manager_language}")
        
        # Используем OpenRouter напрямую через aiohttp
        if not OPENROUTER_API_KEY:
            logging.error("❌ OPENROUTER_API_KEY not set!")
            return "Ошибка: OpenRouter API не настроен"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": OPENROUTER_MODEL,
                        "messages": messages,
                        "max_tokens": 1000
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logging.error(f"❌ OpenRouter error: {resp.status} - {error_text[:200]}")
                        return f"Ошибка API: {resp.status}"
                    
                    data = await resp.json()
                    summary = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    print(f"✅ Summary via OpenRouter: {len(summary) if summary else 0} chars")
                    return summary.strip() if summary else "Нет данных"
                    
        except Exception as e:
            print(f"❌ Summary Error: {e}")
            return f"Ошибка генерации: {str(e)}"

# Default AI service instance (uses .env)
ai_service = AIService()

def get_ai_service(company_id: int = None, ai_endpoint: str = None, ai_api_key: str = None):
    """Get AI service instance with company-specific or default settings"""
    if ai_endpoint and ai_api_key:
        return AIService(company_id=company_id, ai_endpoint=ai_endpoint, ai_api_key=ai_api_key)
    return ai_service
