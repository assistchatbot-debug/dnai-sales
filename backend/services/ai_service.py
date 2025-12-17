import logging
from typing import List, Dict, Any
import os
from openai import AsyncOpenAI

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
        
        # Add only user messages from history
        for msg in history[-20:]:
            if msg.get("sender") == "user":
                text = msg.get("text", "")
                if text and text not in ['received', 'sent']:
                    messages.append({"role": "user", "content": text})
        
        # Add current user message with lang parameter
        import json
        msg_with_lang = json.dumps({"message": user_query, "lang": language}, ensure_ascii=False)
        messages.append({"role": "user", "content": msg_with_lang})
        
        # Debug logging
        print(f"🔍 History: {len(history)} messages")
        print(f"🔍 Last 3: {[m.get('text','')[:40] for m in history[-3:]]}")
        print(f"🔍 Sending to AI: {msg_with_lang[:100]}")
        
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

    async def generate_conversation_summary(self, history: List[Dict[str, str]], language: str = "ru") -> str:
        if not self.client or not history:
            return "Нет данных для анализа"
        
        print(f"📊 Generating summary for {len(history)} messages")
        
        # Build prompt for summary
        summary_prompt = """Проанализируй диалог с клиентом и создай краткий отчёт.

Формат:
1. Интересы клиента - какие сферы назвал
2. Готовность - Холодный/Тёплый/Горячий
3. Рекомендации менеджеру

Объём: 100-150 слов."""

        messages = [{"role": "system", "content": summary_prompt}]
        
        for msg in history[-30:]:
            role = "user" if msg.get("sender") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("text", "")})
        
        try:
            response = await self.client.chat.completions.create(
                model="n/a",
                messages=messages,
                extra_body={"include_retrieval_info": False}
            )
            
            if not response.choices or not response.choices[0].message:
                return "Ошибка: пустой ответ AI"
            
            summary = response.choices[0].message.content
            print(f"✅ Summary: {len(summary) if summary else 0} chars")
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
