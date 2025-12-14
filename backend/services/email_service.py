import os
import logging
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.mail.ru')
        self.smtp_port = int(os.getenv('SMTP_PORT', 465))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.manager_email = os.getenv('MANAGER_EMAIL')
        self.executor = ThreadPoolExecutor(max_workers=3)
        
    def _send_email_sync(self, lead_contact: str, conversation_history: List[Dict[str, str]], ai_summary: str, lead_phone: str = None, to_email: str = None):
        """
        Synchronous email sending function (runs in thread pool)
        """
        if not all([self.smtp_user, self.smtp_password, self.manager_email]):
            logging.warning('⚠️ Email credentials not configured')
            return False

        try:
            logging.info(f'📧 Sending email notification to {self.manager_email}...')
            
            # Format conversation history
            conversation_text = '\n\n'.join([
                f"{'👤 Клиент' if msg.get('sender') == 'user' else '🤖 Бот'}: {msg.get('text', '')}"
                for msg in conversation_history[-20:]
            ])

            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'🎯 Новый лид: {lead_contact} - {lead_phone or "телефон не указан"}'  
            msg['From'] = self.smtp_user
            msg['To'] = self.manager_email

            # Plain text version
            text_content = f'''Новый лид от BizDNAi

Имя: {lead_contact}
Телефон: {lead_phone or "не указан"}

Анализ AI:
{ai_summary}

История диалога:
{conversation_text}

---
Отправлено автоматически от BizDNAi Sales Agent
'''

            # HTML version
            html_content = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 10px 10px; }}
        .section {{ background: white; padding: 15px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .phone {{ font-size: 20px; font-weight: bold; color: #667eea; }}
        .summary {{ background: #e8f4f8; padding: 15px; border-left: 4px solid #667eea; margin: 10px 0; white-space: pre-wrap; }}
        .message {{ padding: 10px; margin: 5px 0; border-radius: 5px; }}
        .user {{ background: #e3f2fd; }}
        .bot {{ background: #f3e5f5; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">🎯 Новый лид от BizDNAi</h1>
        </div>
        <div class="content">
            <div class="section">
                <h3>📞 Контактные данные:</h3>
                <p><strong>Имя:</strong> {lead_contact}</p>
                <p class="phone"><strong>Телефон:</strong> {lead_phone or "не указан"}</p>
            </div>
            
            <div class="section">
                <h3>🤖 Анализ AI:</h3>
                <div class="summary">{ai_summary}</div>
            </div>
            
            <div class="section">
                <h3>💬 История диалога:</h3>
'''
            
            # Add conversation messages
            for msg_item in conversation_history[-20:]:
                sender = msg_item.get('sender')
                text = msg_item.get('text', '')
                css_class = 'user' if sender == 'user' else 'bot'
                icon = '👤 Клиент' if sender == 'user' else '🤖 Бот'
                html_content += f'<div class="message {css_class}"><strong>{icon}:</strong> {text}</div>\n'
            
            html_content += '''
            </div>
            
            <div class="footer">
                <p>---</p>
                <p><em>Отправлено автоматически от BizDNAi Sales Agent</em></p>
            </div>
        </div>
    </div>
</body>
</html>
'''

            # Attach both versions
            part1 = MIMEText(text_content, 'plain', 'utf-8')
            part2 = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(part1)
            msg.attach(part2)

            # Send email using SSL (port 465)
            logging.info(f'📧 Connecting to {self.smtp_host}:{self.smtp_port}...')
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30) as server:
                logging.info(f'📧 Logging in as {self.smtp_user}...')
                server.login(self.smtp_user, self.smtp_password)
                logging.info(f'📧 Sending message...')
                server.send_message(msg)
                
            logging.info(f'✅ Email notification sent successfully to {self.manager_email}')
            return True
            
        except smtplib.SMTPException as e:
            logging.error(f'❌ SMTP Error: {e}')
            import traceback
            traceback.print_exc()
            return False
        except Exception as e:
            logging.error(f'❌ Failed to send email notification: {e}')
            import traceback
            traceback.print_exc()
            return False
    
    async def send_lead_notification(self, lead_contact: str, conversation_history: List[Dict[str, str]], ai_summary: str, lead_phone: str = None, to_email: str = None):
        """
        Async wrapper for email sending
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._send_email_sync,
            lead_contact,
            conversation_history,
            ai_summary,
            lead_phone,
            to_email
        )

email_service = EmailService()
