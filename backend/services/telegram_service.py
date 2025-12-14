import os
import logging
import aiohttp
import re
from typing import List, Dict

class TelegramService:
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        self.manager_chat_id = os.getenv('MANAGER_CHAT_ID')
        self.api_url = f'https://api.telegram.org/bot{self.bot_token}'
        
    def _clean_html_tags(self, text: str) -> str:
        """Remove HTML tags that Telegram can't parse"""
        if not text:
            return text
        # Remove <br>, <br/>, <br />, etc.
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        # Remove other problematic tags
        text = re.sub(r'</?(?:div|span|p)>', '', text, flags=re.IGNORECASE)
        return text
        
    async def send_lead_notification(self, lead_contact: str, conversation_history: List[Dict[str, str]], ai_summary: str, lead_phone: str = None, bot_token: str = None, manager_chat_id: str = None):
        # Use provided tokens or fallback to env
        token = bot_token or self.bot_token
        chat_id = manager_chat_id or self.manager_chat_id
        
        if not token or not chat_id:
            logging.warning('⚠️ Telegram credentials not configured')
            return False

        try:
            logging.info(f'📱 Sending Telegram notification to {chat_id}...')
            api_url = f'https://api.telegram.org/bot{token}'
            
            # Clean AI summary from HTML tags
            clean_summary = self._clean_html_tags(ai_summary)
            
            conversation_text = '\n\n'.join([
                f"{'🧑 Клиент' if msg.get('sender') == 'user' else '🤖 Бот'}: {msg.get('text', '')}"
                for msg in conversation_history[-20:]
            ])

            message = f'''🎯 <b>Новый лид от BizDNAi</b>

👤 <b>Имя:</b> {lead_contact}
📞 <b>Телефон:</b> <code>{lead_phone or "не указан"}</code>

🤖 <b>Анализ AI:</b>
<pre>{clean_summary}</pre>

💬 <b>История диалога:</b>
{conversation_text}

---
<i>Отправлено автоматически от BizDNAi Sales Agent</i>'''

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{api_url}/sendMessage',
                    json={
                        'chat_id': chat_id,
                        'text': message,
                        'parse_mode': 'HTML'
                    }
                ) as resp:
                    if resp.status == 200:
                        logging.info(f'✅ Telegram notification sent successfully')
                        return True
                    else:
                        error_text = await resp.text()
                        logging.error(f'❌ Telegram API error: {resp.status} - {error_text}')
                        return False
            
        except Exception as e:
            logging.error(f'❌ Failed to send Telegram notification: {e}')
            import traceback
            traceback.print_exc()
            return False

telegram_service = TelegramService()
