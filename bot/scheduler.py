import asyncio
import logging
import aiohttp
import os

API_BASE_URL = os.environ.get('API_BASE_URL', 'http://backend:8000/sales')

async def reminder_scheduler(bots_dict):
    """Check and send event reminders every minute"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/crm/pending-reminders') as resp:
                    if resp.status == 200:
                        events = await resp.json()
                        for event in events:
                            user_id = event.get('user_id')
                            company_id = event.get('company_id')
                            
                            bot = bots_dict.get(company_id)
                            if not bot:
                                continue
                            
                            emoji = {'call': '📞', 'meeting': '🤝', 'email': '📧', 'task': '📋'}.get(event.get('event_type'), '📋')
                            client = event.get('client_name', 'Клиент')
                            phone = event.get('client_phone', '')
                            dt = event.get('scheduled_at', '')[:16].replace('T', ' ')
                            desc = event.get('description', '')
                            remind = event.get('remind_before', 30)
                            
                            text = f"🔔 <b>Напоминание!</b>\n\n{emoji} через {remind} минут\n👤 Клиент: {client}"
                            if phone:
                                text += f" ({phone})"
                            text += f"\n📅 {dt}"
                            if desc:
                                text += f"\n📝 {desc}"
                            
                            kb = InlineKeyboardMarkup(inline_keyboard=[
                                [
                                    InlineKeyboardButton(text="✅ Выполнено", callback_data=f"edone:{event['id']}"),
                                    InlineKeyboardButton(text="⏰ +15 мин", callback_data=f"edelay:{event['id']}:{event.get('scheduled_at', '')}")
                                ],
                                [InlineKeyboardButton(text="❌ Отменить", callback_data=f"ecancel:{event['id']}")]
                            ])
                            
                            try:
                                await bot.send_message(user_id, text, parse_mode='HTML', reply_markup=kb)
                                await session.patch(f'{API_BASE_URL}/crm/events/{event["id"]}/reminder-sent')
                                logging.info(f"📅 Reminder sent to {user_id}")
                            except Exception as e:
                                logging.error(f"Reminder send error: {e}")
        except Exception as e:
            logging.error(f"Scheduler error: {e}")
        
        await asyncio.sleep(60)
