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

    async def get_product_recommendation(self, user_query: str, history: List[Dict[str, str]], product_catalog: List[Dict[str, Any]], system_prompt: str = None, language: str = "ru") -> str:
        if not self.client: return "AI Service is not configured."
        if not system_prompt:
            system_prompt = f"""You are an expert business consultant for BizDNAii (Corporate AI Assistant).
Your goal is to diagnose the client's business needs by identifying their "pain points" across 21 key business functions.

The 21 Business Functions are:
1. Hiring (Roles, Training, Onboarding)
2. Communications (Internal, Client, Partners)
3. Statistics & Inspections (Reporting, KPIs, Discipline)
4. Marketing (Brand, Identity, Analysis, Content)
5. Advertising (Channels, Campaigns, ROI)
6. Sales (CRM, Loyalty, Growth)
7. Income (POS, Cash Flow)
8. Expenses (Purchasing, Budgeting)
9. Accounting (Inventory, Costing, Reports)
10. Planning (Suppliers, Contracts)
11. Provisioning (Logistics, Storage)
12. Production (Quality, Technology, Service)
13. Certification (Quality Control, Feedback)
14. Training (Manuals, Updates)
15. Correction (Errors, Improvements)
16. Information (PR, Surveys, Image)
17. New Clients (Demos, Presentations)
18. Partnerships (Agents, Branches)
19. Management (Metrics, Tasks, Analysis)
20. Legal (Contracts, Compliance, Security)
21. Founder's Office (Goals, Strategy, Assets)

Strategy:
1. Do NOT list these functions.
2. Ask open-ended questions to identify which Department (I-VII) is the weakest.
3. Narrow down to the specific Function (1-21).
4. Identify the critical pain point.
5. Propose a BizDNAii solution (AI Agents, Automation, Voice Control).
6. Keep responses SHORT and CONVERSATIONAL. One question at a time.
7. Always respond in {language} language."""
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            role = "user" if msg.get("sender") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("text", "")})
        catalog_context = f"\n\nAvailable Products:\n{product_catalog}"
        messages.append({"role": "user", "content": user_query + catalog_context})
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                extra_headers={"HTTP-Referer": "https://bizdnaii.com", "X-Title": "BizDNAii Sales Agent"}
            )
            return response.choices[0].message.content
        except Exception as e:
            import traceback
            print(f"Error calling AI: {e}")
            traceback.print_exc()
            return f"I apologize, but I'm having trouble connecting to my brain right now. Error: {str(e)}"

ai_service = AIService()
