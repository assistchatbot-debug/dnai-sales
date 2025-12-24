from typing import List, Dict, Any
import os
from openai import AsyncOpenAI

class AIService:
    def __init__(self):
        # Use custom AI Agent
        self.agent_url = os.getenv("AI_AGENT_URL")
        self.agent_key = os.getenv("AI_AGENT_KEY")
        
        if self.agent_url and self.agent_key:
            self.client = AsyncOpenAI(
                api_key=self.agent_key, 
                base_url=self.agent_url + "/api/v1/"
            )
            print(f"✅ AI Agent configured: {self.agent_url}")
        else:
            self.client = None
            print("⚠️ AI Agent not configured - check AI_AGENT_URL and AI_AGENT_KEY")

    async def get_product_recommendation(self, user_query: str, history: List[Dict[str, str]], product_catalog: List[Dict[str, Any]], system_prompt: str = None, language: str = "ru") -> str:
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

ai_service = AIService()
