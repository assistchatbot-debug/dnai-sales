import logging
import aiohttp
import io
import os
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from config import API_BASE_URL
from states import SalesFlow, ManagerFlow
from keyboards import get_start_keyboard

router = Router()

def is_manager(user_id: int, bot) -> bool:
    """Check if user is the authorized manager for this bot's company"""
    if not hasattr(bot, 'manager_chat_id') or not bot.manager_chat_id:
        return False
    return str(user_id) == str(bot.manager_chat_id)

async def start_session(user_id: int, company_id: int, new_session: bool = True):
    """Start session for specific company"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f'{API_BASE_URL}/sales/{company_id}/chat', json={
                'message': 'start_session',
                'user_id': str(user_id),
                'username': f'user_{user_id}',
                'source': 'telegram',
                'new_session': new_session
            }) as resp:
                data = await resp.json()
                return data.get("session_id")
        except Exception as e:
            logging.error(f'Session start error: {e}')
            return None

async def process_backend_response(message: types.Message, response_text: str):
    """
    Helper to process backend response: check for contact request, 
    show menu if needed, or just show text.
    """
    # Check for [REQUEST_CONTACT] marker
    if '[REQUEST_CONTACT]' in response_text:
        clean_response = response_text.replace('[REQUEST_CONTACT]', '').strip()
        
        # Create contact button
        contact_kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(clean_response, reply_markup=contact_kb)
    
    # Check if conversation seems to be ending (manager will contact)
    elif "менеджер свяжется" in response_text.lower():
        await message.answer(response_text, reply_markup=get_start_keyboard())
        
    else:
        # Normal response - remove keyboard if it was there (or keep it hidden)
        await message.answer(response_text, reply_markup=ReplyKeyboardRemove())

@router.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    # Manager menu with buttons
    if is_manager(message.from_user.id,message.bot):
        from aiogram.types import ReplyKeyboardMarkup,KeyboardButton
        kb=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📊 Статус"),KeyboardButton(text="📋 Лиды")],[KeyboardButton(text="📢 Каналы"),KeyboardButton(text="🌐 Виджет")],[KeyboardButton(text="📊 Лиды за неделю"),KeyboardButton(text="📊 Лиды за месяц")],[KeyboardButton(text="🏠 Меню")]],resize_keyboard=True)
        await message.answer("🤖 <b>Меню</b>",reply_markup=kb,parse_mode='HTML')
        return
    await state.set_state(SalesFlow.qualifying)
    await start_session(message.from_user.id, company_id=1)
    
    # Language selection buttons
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    lang_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_en")],
        [InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang_kz"),
         InlineKeyboardButton(text="🇰🇬 Кыргызча", callback_data="lang_ky")],
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
         InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_uk")]
    ])
    
    await message.answer(
        "Привет! Я Умный Агент (BizDNAi).\n🚀 Я новое поколение корпоративного AI.\n\n"
        "Hello! I'm Smart Agent (BizDNAi).\n🚀 I'm the new generation of corporate AI.\n\n"
        "Выберите язык / Choose language:",
        reply_markup=lang_kb
    )

@router.callback_query(F.data.startswith("lang_"))
async def set_language_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle language selection"""
    lang = callback.data.split("_")[1]
    await state.update_data(language=lang)
    
    greetings = {
        'ru': 'Отлично! Теперь пишите или говорите, и я вам отвечу.',
        'en': 'Great! Now write or speak, and I will answer you.',
        'kz': 'Тамаша! Енді жазыңыз немесе сөйлеңіз, мен сізге жауап беремін.',
        'ky': 'Мыкты! Эми жазыңыз же сүйлөңүз, мен сизге жооп берем.',
        'uz': 'Ajoyib! Endi yozing yoki gapiring, men sizga javob beraman.',
        'uk': 'Чудово! Тепер пишіть або говоріть, і я вам відповім.'
    }
    
    await callback.message.edit_text(greetings.get(lang, greetings['ru']))
    await callback.answer()

@router.message(Command('id'))
async def cmd_id(message: types.Message):
    await message.answer(f"Ваш Chat ID: `{message.chat.id}`\n\nСкопируйте его и отправьте разработчику.")

@router.message(F.contact)
async def handle_contact(message: types.Message, state: FSMContext):
    contact = message.contact
    phone = contact.phone_number
    user_id = str(message.from_user.id)
    username = message.from_user.username or f"user_{user_id}"
    
    status_msg = await message.answer("⏳ Обрабатываю контакт...")
    
    async with aiohttp.ClientSession() as session:
        try:
            company_id = getattr(message.bot, 'company_id', 1)
            async with session.post(f'{API_BASE_URL}/sales/{company_id}/chat', json={
                'message': phone,
                'user_id': user_id,
                'username': username,
                'phone': phone
            }) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response_text = data.get('response', 'Спасибо! Номер получен.')
                    await status_msg.delete()
                    await message.answer(response_text, reply_markup=get_start_keyboard())
                else:
                    await status_msg.delete()
                    await message.answer("Ошибка при отправке контакта.", reply_markup=get_start_keyboard())
        except Exception as e:
            logging.error(f'Backend error: {e}')
            await status_msg.delete()
            await message.answer("Ошибка соединения с сервером.")

@router.message(F.voice)
async def handle_voice(message: types.Message, state: FSMContext):
    # Check if manager - handle separately
    if is_manager(message.from_user.id, message.bot):
        await handle_manager_voice(message)
        return
    
    user_id = str(message.from_user.id)
    username = message.from_user.username or f"user_{user_id}"
    
    # Get language for status message
    state_data = await state.get_data()
    language = state_data.get('language', 'ru')
    
    status_messages = {
        'ru': '🧠 Думаю...',
        'en': '🧠 Thinking...',
        'kz': '🧠 Ойланудамын...',
        'ky': '🧠 Ойлонуп жатам...',
        'uz': '🧠 O\'ylayapman...',
        'uk': '🧠 Думаю...'
    }
    
    status_msg = await message.answer(status_messages.get(language, '🧠 Думаю...'))
    
    # Get session_id from state
    data = await state.get_data()
    session_id = data.get("session_id")
    
    if not session_id:
        session_id = await start_session(message.from_user.id, company_id=1)
        if session_id:
            await state.update_data(session_id=session_id)
    
    try:
        # Download voice file
        voice_file = await message.bot.get_file(message.voice.file_id)
        file_data = io.BytesIO()
        await message.bot.download(voice_file, file_data)
        file_data.seek(0)
        
        # Prepare form data
        data_form = aiohttp.FormData()
        data_form.add_field('file', file_data, filename='voice.ogg', content_type='audio/ogg')
        data_form.add_field('session_id', session_id or 'voice_session') 
        data_form.add_field('user_id', user_id)
        data_form.add_field('username', username)
        
        # Get language from state (default to 'ru')
        state_data = await state.get_data()
        language = state_data.get('language', 'ru')
        data_form.add_field('language', language)
        
        company_id = getattr(message.bot, 'company_id', 1)
        async with aiohttp.ClientSession() as session:
             async with session.post(f'{API_BASE_URL}/sales/{company_id}/voice', data=data_form) as resp:
                 if resp.status == 200:
                     result = await resp.json()
                     ai_response = result.get('response', '')
                     transcribed_text = result.get('text', '')
                     
                     try:
                        await status_msg.delete()
                     except Exception:
                        pass
                     
                     if transcribed_text:
                        you_said_text = {
                            'ru': '🗣 Вы сказали:',
                            'en': '🗣 You said:',
                            'kz': '🗣 Сіз айттыңыз:',
                            'ky': '🗣 Сиз айттыңыз:',
                            'uz': '🗣 Siz aytdingiz:',
                            'uk': '🗣 Ви сказали:'
                        }
                        await message.answer(f"{you_said_text.get(language, '🗣 Вы сказали:')} {transcribed_text}")
                        
                     await process_backend_response(message, ai_response)
                 else:
                     try:
                        await status_msg.delete()
                     except Exception:
                        pass
                     await message.answer("Ошибка обработки голосового сообщения.")
    except Exception as e:
        logging.error(f"Voice error: {e}")
        try:
            await status_msg.delete()
        except Exception:
            pass
        await message.answer("Произошла ошибка при обработке голоса.")

async def handle_manager_voice(message: types.Message):
    """Handle voice messages from manager"""
    status_msg = await message.answer("🎤 Обрабатываю голосовое сообщение...")
    
    try:
        # Download voice file
        voice_file = await message.bot.get_file(message.voice.file_id)
        file_data = io.BytesIO()
        await message.bot.download(voice_file, file_data)
        file_data.seek(0)
        
        # Prepare form data for transcription
        data = aiohttp.FormData()
        data.add_field('file', file_data, filename='voice.ogg', content_type='audio/ogg')
        data.add_field('session_id', 'manager_voice')
        data.add_field('user_id', str(message.from_user.id))
        data.add_field('username', 'manager')
        
        company_id = getattr(message.bot, 'company_id', 1)
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{API_BASE_URL}/sales/{company_id}/voice', data=data_form) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    transcribed_text = result.get('text', '')
                    
                    try:
                        await status_msg.delete()
                    except:
                        pass
                    
                    if transcribed_text:
                        you_said_text = {
                            'ru': '🗣 Вы сказали:',
                            'en': '🗣 You said:',
                            'kz': '🗣 Сіз айттыңыз:',
                            'ky': '🗣 Сиз айттыңыз:',
                            'uz': '🗣 Siz aytdingiz:',
                            'uk': '🗣 Ви сказали:'
                        }
                        await message.answer(f"{you_said_text.get(language, '🗣 Вы сказали:')} {transcribed_text}")
                        # Process as manager command
                        await process_manager_command(message, transcribed_text, state)
                    else:
                        await message.answer("❌ Не удалось распознать голос")
                else:
                    try:
                        await status_msg.delete()
                    except:
                        pass
                    await message.answer("❌ Ошибка обработки голоса")
    except Exception as e:
        logging.error(f"Manager voice error: {e}")
        try:
            await status_msg.delete()
        except:
            pass
        await message.answer(f"❌ Ошибка: {str(e)}")

async def process_manager_command(message: types.Message, text: str, state: FSMContext):
    """Process manager text commands"""
    text_lower = text.lower()
    
    if 'статус' in text_lower or 'status' in text_lower:
        company_id = getattr(message.bot, 'company_id', 1)
        logging.info(f"🏢 MULTITENANCY: Manager checking status for company {company_id}")
        
        status_parts = ["📊 <b>Статус системы</b>\n"]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{API_BASE_URL}/sales/{company_id}/chat',
                    json={'message': 'ping', 'user_id': 'healthcheck'},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        status_parts.append("✅ AI Агент - работает")
                    else:
                        status_parts.append(f"⚠️ AI Агент - код {resp.status}")
        except Exception as e:
            logging.error(f"AI status check failed: {e}")
            status_parts.append("❌ AI Агент - недоступен")
        
        status_parts.append("🤖 Telegram Bot - активен (polling)")
        
        await message.answer('\n'.join(status_parts), parse_mode='HTML')
    
    elif 'лиды за неделю' in text_lower:
        company_id=1
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/sales/{company_id}/leads',params={'limit':100},timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status==200:
                        data=await resp.json()
                        leads=data.get('leads',[])
                        from datetime import datetime,timedelta
                        week_ago=datetime.now()-timedelta(days=7)
                        week_leads=[l for l in leads if datetime.fromisoformat(l['created_at'].replace('Z','+00:00'))>week_ago]
                        from collections import Counter
                        sources=Counter(l.get('source','web') for l in week_leads)
                        msg=f"📊 <b>Лиды за неделю</b>\n\nВсего: {len(week_leads)}\n\n<b>По источникам:</b>\n"
                        for source,count in sorted(sources.items(), key=lambda x: (1, int(x[0])) if x[0].isdigit() else (0, x[0].lower())):
                            if source.isdigit():
                                msg+=f"📸 Instagram #{source}: {count}\n"
                            else:
                                msg+=f"• {source}: {count}\n"
                        msg+="\n<b>Последние 10:</b>\n"
                        for lead in week_leads[:10]:
                            contact=lead.get('contact_info',{})
                            name=contact.get('name','Не указано')
                            phone=contact.get('phone','Не указан')
                            source=lead.get('source','web')
                            msg+=f"• {name} ({phone}) - {source}\n"
                        await message.answer(msg,parse_mode='HTML')
                    else:
                        await message.answer("⚠️ Не удалось получить лиды")
        except Exception as e:
            logging.error(f"Week leads error: {e}")
            await message.answer("❌ Ошибка")
    elif 'лиды за месяц' in text_lower:
        company_id=1
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/sales/{company_id}/leads',params={'limit':200},timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status==200:
                        data=await resp.json()
                        leads=data.get('leads',[])
                        from datetime import datetime,timedelta
                        month_ago=datetime.now()-timedelta(days=30)
                        month_leads=[l for l in leads if datetime.fromisoformat(l['created_at'].replace('Z','+00:00'))>month_ago]
                        from collections import Counter
                        sources=Counter(l.get('source','web') for l in month_leads)
                        msg=f"📊 <b>Лиды за месяц</b>\n\nВсего: {len(month_leads)}\n\n<b>По источникам:</b>\n"
                        for source,count in sorted(sources.items(), key=lambda x: (1, int(x[0])) if x[0].isdigit() else (0, x[0].lower())):
                            if source.isdigit():
                                msg+=f"📸 Instagram #{source}: {count}\n"
                            else:
                                msg+=f"• {source}: {count}\n"
                        msg+="\n<b>Последние 10:</b>\n"
                        for lead in month_leads[:10]:
                            contact=lead.get('contact_info',{})
                            name=contact.get('name','Не указано')
                            phone=contact.get('phone','Не указан')
                            source=lead.get('source','web')
                            msg+=f"• {name} ({phone}) - {source}\n"
                        await message.answer(msg,parse_mode='HTML')
                    else:
                        await message.answer("⚠️ Не удалось получить лиды")
        except Exception as e:
            logging.error(f"Month leads error: {e}")
            await message.answer("❌ Ошибка")
    
    elif 'лиды' in text_lower or 'leads' in text_lower or 'лід' in text_lower:
        company_id = getattr(message.bot, 'company_id', 1)
        logging.info(f"🏢 MULTITENANCY: Manager viewing leads for company {company_id}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{API_BASE_URL}/sales/{company_id}/leads?limit=10',
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        leads = data.get('leads', [])
                        
                        if not leads:
                            await message.answer("📊 Лидов пока нет")
                            return
                        
                        async with session.get(
                            f'{API_BASE_URL}/sales/{company_id}/leads/stats',
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as stats_resp:
                            stats_data = await stats_resp.json() if stats_resp.status == 200 else {}
                        
                        total = stats_data.get('total', len(leads))
                        by_source = stats_data.get('by_source', {})
                        
                        stats_text = "📊 <b>Статистика лидов</b>\n"
                        stats_text += f"Всего: {total} (все время)\n\n"
                        
                        source_emojis = {
                            'telegram': '📱 Telegram',
                            'web': '🌐 Веб-сайт',
                            'instagram': '📸 Instagram',
                            'facebook': '📘 Facebook',
                            'vk': '🔵 ВКонтакте'
                        }
                        
                        def sort_key(item):
                            source = item[0]
                            if source.isdigit():
                                return (1, int(source))
                            return (0, source.lower())
                        
                        for source, count in sorted(by_source.items(), key=sort_key):
                            if source.isdigit():
                                emoji_name = f'📸 Instagram #{source}'
                            else:
                                emoji_name = source_emojis.get(source, f'📍 {source.capitalize()}')
                            stats_text += f"{emoji_name}: {count}\n"
                        
                        leads_text = [stats_text + "\n<b>Последние 5 лидов:</b>\n"]
                        for i, lead in enumerate(leads[:5], 1):
                            contact = lead.get('contact_info', {})
                            name = contact.get('name') if isinstance(contact, dict) else None
                            telegram_id = lead.get('telegram_user_id', '?')
                            phone = contact.get('phone', 'нет') if isinstance(contact, dict) else 'нет'
                            
                            display_name = name if name else f"User {telegram_id}"
                            
                            status = lead.get('status', 'new')
                            source = lead.get('source', 'unknown')
                            created = lead.get('created_at', '')[:16]
                            
                            temp = contact.get('temperature', '🌤 теплый') if isinstance(contact, dict) else '🌤 теплый'
                            
                            leads_text.append(
                                f"{i}. ID: {lead.get('id', '?')}\n"
                                f"   Клиент: {display_name}\n"
                                f"   Телефон: {phone}\n"
                                f"   Температура: {temp}\n"
                                f"   Статус: {status} | {source}\n"
                                f"   Создан: {created}\n"
                            )
                        
                        await message.answer('\n'.join(leads_text), parse_mode='HTML')
                    else:
                        await message.answer(f"⚠️ Не удалось получить лиды (код {resp.status})")
        except Exception as e:
            await message.answer(f"❌ Ошибка получения лидов: {str(e)[:50]}")
    
    elif 'каналы' in text_lower or 'channels' in text_lower:
        company_id = message.bot.company_id
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/sales/companies/{company_id}/widgets') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        widgets = data.get('widgets', [])
                        
                        msg_parts = ["📢 <b>Каналы распространения</b>\n"]
                        msg_parts.append("📱 Telegram: ✅ Активен")
                        msg_parts.append("🌐 Widget: ✅ Работает\n")
                        
                        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                        buttons = []
                        
                        if widgets:
                            msg_parts.append("<b>Социальные сети:</b>")
                            for w in widgets:
                                channel_name = w['channel_name']
                                channel_display = channel_name.capitalize()
                                widget_id = w['id']
                                widget_url = f"https://bizdnai.com/w/{company_id}/{widget_id}"
                                
                                msg_parts.append(f"• {channel_display} (ID: {widget_id})")
                                msg_parts.append(f"  🔗 {widget_url}")
                                
                                buttons.append([
                                    InlineKeyboardButton(text=f"✏️ Edit #{widget_id}", callback_data=f"edit_widget_{widget_id}"),
                                    InlineKeyboardButton(text=f"🗑 Delete #{widget_id}", callback_data=f"delete_widget_{widget_id}")
                                ])
                        else:
                            msg_parts.append("<i>Социальных каналов пока нет</i>")
                        
                        buttons.append([
                            InlineKeyboardButton(text="➕ Создать канал", callback_data=f"create_widget_{company_id}")
                        ])
                        
                        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                        await message.answer('\n'.join(msg_parts), reply_markup=keyboard, parse_mode='HTML')
                    else:
                        await message.answer("⚠️ Не удалось получить список каналов")
        except Exception as e:
            logging.error(f"Channels command error: {e}")
            await message.answer(f"❌ Ошибка: {str(e)[:50]}")
    
    elif 'меню' in text_lower or 'menu' in text_lower:
        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📊 Статус"), KeyboardButton(text="📋 Лиды")],
                [KeyboardButton(text="📢 Каналы"), KeyboardButton(text="🌐 Виджет")],
                [KeyboardButton(text="📊 Лиды за неделю"), KeyboardButton(text="📊 Лиды за месяц")],
                [KeyboardButton(text="🏠 Меню")]
            ],
            resize_keyboard=True
        )
        await message.answer("🏠 <b>Главное меню</b>", reply_markup=kb, parse_mode='HTML')
    
    elif 'помощь' in text_lower or 'help' in text_lower or 'команд' in text_lower:
        await message.answer(
            "📋 <b>Доступные команды:</b>\n\n"
            "<b>📊 Статус</b> - проверка всех систем\n"
            "<b>📋 Лиды</b> - просмотр последних лидов\n"
            "<b>📢 Каналы</b> - список социальных каналов\n"
            "<b>создать канал</b> - создать новый канал\n\n"
            "💡 Также работают голосовые сообщения!\n\n"
            "Используйте кнопки меню для быстрого доступа.",
            parse_mode='HTML'
        )
    
    elif 'виджет' in text_lower or 'widget' in text_lower:
        company_id = getattr(message.bot, 'company_id', 1)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/sales/{company_id}/web-widgets') as resp:
                    if resp.status == 200:
                        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                        widgets = await resp.json()
                        msg = "🌐 <b>Веб-виджеты</b>\n\n"
                        buttons = []
                        
                        if widgets:
                            for w in widgets:
                                status = '✅' if w.get('is_active') else '❌'
                                wid = w['id']
                                domain = w['domain']
                                greeting = w.get('greeting_ru', 'Не установлено')[:30]
                                msg += f"{status} <b>{domain}</b> (ID: {wid})\n"
                                msg += f"   {greeting}...\n\n"
                                
                                buttons.append([
                                    InlineKeyboardButton(text=f"✏️ {domain}", callback_data=f"editwidget_{wid}"),
                                    InlineKeyboardButton(text="🔄", callback_data=f"togglewidget_{wid}"),
                                    InlineKeyboardButton(text="🗑", callback_data=f"delwidget_{wid}")
                                ])
                        else:
                            msg += "Виджетов пока нет\n"
                        
                        buttons.append([InlineKeyboardButton(text="➕ Создать виджет", callback_data=f"createwidget_{company_id}")])
                        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                        await message.answer(msg, reply_markup=keyboard, parse_mode='HTML')
                    else:
                        await message.answer("⚠️ Ошибка получения виджетов")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)[:50]}")
    
    else:
        pass


@router.message(ManagerFlow.entering_channel_name)
async def process_channel_name(message: types.Message, state: FSMContext):
    """Process channel name input"""
    if not is_manager(message.from_user.id, message.bot):
        await state.clear()
        return
    
    channel_name = message.text.strip()
    if not channel_name:
        await message.answer("❌ Название не может быть пустым. Попробуйте ещё раз:")
        return
    
    await state.update_data(channel_name=channel_name)
    await state.set_state(ManagerFlow.entering_greeting)
    
    await message.answer(
        f"✅ Канал: <b>{channel_name}</b>\n\n"
        "📝 Введите приветственное сообщение для этого канала\n"
        "(или напишите 'skip' для стандартного):",
        parse_mode='HTML'
    )

@router.message(ManagerFlow.entering_greeting)
async def process_greeting(message: types.Message, state: FSMContext):
    """Process greeting and create widget"""
    if not is_manager(message.from_user.id, message.bot):
        await state.clear()
        return
    
    greeting = message.text.strip()
    if greeting.lower() == 'skip':
        greeting = None
    
    data = await state.get_data()
    channel_name_raw = data.get('channel_name', '')
    company_id = message.bot.company_id
    
    await message.answer("⏳ Создаю канал...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{API_BASE_URL}/sales/companies/{company_id}/widgets',
                json={
                    'channel_name': channel_name_raw,
                    'greeting_message': greeting
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    url = result.get('url', '')
                    name = result.get('channel_name', '')
                    
                    await message.answer(
                        f"🎉 <b>Канал создан!</b>\n\n"
                        f"📱 Название: {channel_name_raw}\n"
                        f"🔗 URL: {url}\n"
                        f"💬 Приветствие: {greeting or 'стандартное'}\n\n"
                        f"Разместите эту ссылку в {channel_name_raw}!",
                        parse_mode='HTML'
                    )
                elif resp.status == 400:
                    error = await resp.json()
                    await message.answer(f"⚠️ {error.get('detail', 'Ошибка')}")
                else:
                    await message.answer(f"❌ Ошибка {resp.status}")
    except Exception as e:
        logging.error(f"Create widget error: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:50]}")
    finally:
        await state.clear()


# === FSM Handlers for Web Widget (MUST BE BEFORE GENERAL HANDLER) ===

@router.message(ManagerFlow.entering_widget_domain)
async def process_widget_domain(message: types.Message, state: FSMContext):
    """Process domain input"""
    if not is_manager(message.from_user.id, message.bot):
        await state.clear()
        return
    
    domain = message.text.strip().lower().replace('http://', '').replace('https://', '').replace('www.', '')
    if not domain or '.' not in domain:
        await message.answer("❌ Неверный формат. Попробуйте ещё раз:")
        return
    
    await state.update_data(widget_domain=domain)
    await state.set_state(ManagerFlow.entering_widget_greeting)
    await message.answer(f"✅ Домен: <b>{domain}</b>\n\nВведите приветствие на русском:", parse_mode='HTML')

@router.message(ManagerFlow.entering_widget_greeting)
async def process_widget_greeting(message: types.Message, state: FSMContext):
    """Process greeting and create widget"""
    if not is_manager(message.from_user.id, message.bot):
        await state.clear()
        return
    
    greeting_ru = message.text.strip()
    if not greeting_ru:
        await message.answer("❌ Приветствие не может быть пустым")
        return
    
    data = await state.get_data()
    domain = data.get('widget_domain', '')
    company_id = getattr(message.bot, 'company_id', 1)
    
    status_msg = await message.answer("⏳ Создаю виджет...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{API_BASE_URL}/sales/{company_id}/web-widgets',
                json={'domain': domain, 'greeting_ru': greeting_ru},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    await status_msg.delete()
                    await message.answer(
                        f"🎉 <b>Виджет создан!</b>\n\n"
                        f"🌐 Домен: {domain}\n"
                        f"💬 Приветствие: {greeting_ru}\n\n"
                        f"✅ Виджет активен на {domain}",
                        parse_mode='HTML'
                    )
                else:
                    await status_msg.delete()
                    await message.answer("❌ Ошибка создания виджета")
    except Exception as e:
        await status_msg.delete()
        await message.answer(f"❌ Ошибка: {str(e)[:100]}")
    finally:
        await state.clear()

@router.message(ManagerFlow.editing_widget_greeting)
async def process_edit_greeting(message: types.Message, state: FSMContext):
    """Process editing widget greeting"""
    if not is_manager(message.from_user.id, message.bot):
        await state.clear()
        return
    
    greeting_ru = message.text.strip()
    if not greeting_ru:
        await message.answer("❌ Приветствие не может быть пустым")
        return
    
    data = await state.get_data()
    widget_id = data.get('editing_widget_id', '')
    company_id = getattr(message.bot, 'company_id', 1)
    
    status_msg = await message.answer("⏳ Обновляю...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f'{API_BASE_URL}/sales/{company_id}/web-widgets/{widget_id}',
                json={'greeting_ru': greeting_ru},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    await status_msg.delete()
                    await message.answer(
                        f"✅ <b>Виджет обновлён!</b>\n\n"
                        f"💬 Новое приветствие: {greeting_ru}",
                        parse_mode='HTML'
                    )
                else:
                    await status_msg.delete()
                    await message.answer("❌ Ошибка обновления")
    except Exception as e:
        await status_msg.delete()
        await message.answer(f"❌ Ошибка: {str(e)[:100]}")
    finally:
        await state.clear()


# === GENERAL HANDLER (MUST BE LAST) ===

@router.message()
async def handle_text(message: types.Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    
    if is_manager(message.from_user.id, message.bot):
        await process_manager_command(message, message.text, state)
        return

    user_id = str(message.from_user.id)
    username = message.from_user.username or f"user_{user_id}"
    
    status_msg = await message.answer("⏳ Думаю...")
    
    data = await state.get_data()
    session_id = data.get("session_id")
    
    if not session_id:
        company_id = getattr(message.bot, 'company_id', 1)
        session_id = await start_session(message.from_user.id, company_id)
        if session_id:
            await state.update_data(session_id=session_id)
    
    company_id = getattr(message.bot, 'company_id', 1)
    async with aiohttp.ClientSession() as session:
        try:
            state_data = await state.get_data()
            language = state_data.get('language', 'ru')
            
            async with session.post(f'{API_BASE_URL}/sales/{company_id}/chat', json={
                'message': message.text,
                'user_id': user_id,
                'username': username,
                'session_id': session_id,
                'source': 'telegram',
                'language': language
            }) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ai_response = data.get('response', '')
                    try:
                        await status_msg.delete()
                    except Exception:
                        pass
                    await process_backend_response(message, ai_response)
                else:
                    try:
                        await status_msg.delete()
                    except Exception:
                        pass
                    await message.answer("Не удалось связаться с сервером.")
        except Exception as e:
            logging.error(f'Backend connection error: {e}')
            try:
                await status_msg.delete()
            except Exception:
                pass
            await message.answer("Ошибка соединения.")


# === Callback Handlers ===

@router.callback_query(F.data.startswith("create_widget_"))
async def create_widget_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle 'Create Widget' button"""
    if not is_manager(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    await state.set_state(ManagerFlow.entering_channel_name)
    await callback.message.answer(
        "📝 <b>Создание канала</b>\n\n"
        "Введите название канала (например: Instagram, Facebook, ВКонтакте):",
        parse_mode='HTML'
    )
    await callback.answer()

@router.callback_query(F.data.startswith("edit_widget_"))
async def edit_widget_callback(callback: types.CallbackQuery):
    """Handle 'Edit Widget' button"""
    if not is_manager(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    widget_id = callback.data.split("_")[-1]
    await callback.message.answer(
        f"✏️ Редактирование канала #{widget_id}\n\n"
        "🚧 В разработке...",
        parse_mode='HTML'
    )
    await callback.answer()

@router.callback_query(F.data.startswith("delete_widget_"))
async def delete_widget_callback(callback: types.CallbackQuery):
    """Handle 'Delete Widget' button"""
    if not is_manager(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    channel_name = callback.data.split("_", 2)[-1]
    company_id = callback.bot.company_id
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{channel_name}',
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    await callback.message.answer("✅ Канал удалён")
                    await callback.message.delete()
                else:
                    await callback.message.answer(f"❌ Ошибка удаления (код {resp.status})")
    except Exception as e:
        logging.error(f"Delete widget error: {e}")
        await callback.message.answer(f"❌ Ошибка: {str(e)[:50]}")
    
    await callback.answer()


# === Web Widget Callback Handlers ===

@router.callback_query(F.data.startswith("editwidget_"))
async def edit_webwidget_callback(callback: types.CallbackQuery, state: FSMContext):
    """Edit web widget greeting"""
    if not is_manager(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    widget_id = callback.data.split("_")[1]
    await state.update_data(editing_widget_id=widget_id)
    await state.set_state(ManagerFlow.editing_widget_greeting)
    
    await callback.message.answer(
        f"✏️ <b>Редактирование виджета #{widget_id}</b>\n\n"
        "Введите новое приветствие на русском:\n"
        "(AI переведёт на все языки)",
        parse_mode='HTML'
    )
    await callback.answer()

@router.callback_query(F.data.startswith("togglewidget_"))
async def toggle_webwidget_callback(callback: types.CallbackQuery):
    """Toggle web widget active status"""
    if not is_manager(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    widget_id = callback.data.split("_")[1]
    company_id = getattr(callback.bot, 'company_id', 1)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(f'{API_BASE_URL}/sales/{company_id}/web-widgets/{widget_id}/toggle') as resp:
                if resp.status == 200:
                    result = await resp.json()
                    status = '✅ Включен' if result.get('is_active') else '❌ Выключен'
                    await callback.answer(f"Статус: {status}", show_alert=True)
                else:
                    await callback.answer("❌ Ошибка", show_alert=True)
    except Exception as e:
        await callback.answer("❌ Ошибка", show_alert=True)

@router.callback_query(F.data.startswith("delwidget_"))
async def delete_webwidget_callback(callback: types.CallbackQuery):
    """Delete web widget"""
    if not is_manager(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    widget_id = callback.data.split("_")[1]
    company_id = getattr(callback.bot, 'company_id', 1)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(f'{API_BASE_URL}/sales/{company_id}/web-widgets/{widget_id}') as resp:
                if resp.status == 200:
                    await callback.answer("✅ Виджет удалён", show_alert=True)
                    await callback.message.delete()
                else:
                    await callback.answer("❌ Ошибка", show_alert=True)
    except Exception as e:
        await callback.answer("❌ Ошибка", show_alert=True)

@router.callback_query(F.data.startswith("createwidget_"))
async def create_webwidget_callback(callback: types.CallbackQuery, state: FSMContext):
    """Start creating web widget"""
    if not is_manager(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    await state.set_state(ManagerFlow.entering_widget_domain)
    await callback.message.answer(
        "🌐 <b>Создание веб-виджета</b>\n\n"
        "Введите домен (например: example.com):",
        parse_mode='HTML'
    )
    await callback.answer()
