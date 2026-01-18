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

def get_admin_keyboard():
    """Admin bot main keyboard"""
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏆 Лидерборд"), KeyboardButton(text="📊 Статус")],
            [KeyboardButton(text="📢 Каналы"), KeyboardButton(text="🌐 Виджет")],
            [KeyboardButton(text="💳 Тарифы"), KeyboardButton(text="🌍 Язык")],
            [KeyboardButton(text="👥 Менеджеры"), KeyboardButton(text="📋 Лиды")],
            [KeyboardButton(text="🔌 Внешняя CRM"), KeyboardButton(text="📊 Внутренняя CRM")],
            [KeyboardButton(text="📈 Лиды за неделю"), KeyboardButton(text="📅 Лиды за месяц")]
        ],
        resize_keyboard=True
    )



router = Router()

def is_admin(user_id: int, bot) -> bool:
    """Check if user is the authorized manager for this bot's company"""
    if not hasattr(bot, 'admin_chat_id') or not bot.admin_chat_id:
        return False
    return str(user_id) == str(bot.admin_chat_id)

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
    if is_admin(message.from_user.id,message.bot):
        await message.answer("🤖 <b>Меню</b>", reply_markup=get_admin_keyboard(), parse_mode='HTML')
        return
    await state.set_state(SalesFlow.qualifying)
    company_id = getattr(message.bot, 'company_id', 1)
    await start_session(message.from_user.id, company_id=company_id)
    
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
    if is_admin(message.from_user.id, message.bot):
        await handle_admin_voice(message, state)
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
        company_id = getattr(message.bot, 'company_id', 1)
        session_id = await start_session(message.from_user.id, company_id=company_id)
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

async def handle_admin_voice(message: types.Message, state: FSMContext):
    """Handle voice messages from manager"""
    status_msg = await message.answer("🎤 Обрабатываю голосовое сообщение...")
    
    try:
        # Download voice file
        voice_file = await message.bot.get_file(message.voice.file_id)
        file_data = io.BytesIO()
        await message.bot.download(voice_file, file_data)
        file_data.seek(0)
        
        # Prepare form data for transcription
        data_form = aiohttp.FormData()
        data_form.add_field('file', file_data, filename='voice.ogg', content_type='audio/ogg')
        data_form.add_field('session_id', 'manager_voice')
        data_form.add_field('user_id', str(message.from_user.id))
        data_form.add_field('username', 'manager')
        data_form.add_field('language', 'ru')  # Manager default language
        
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
                        # Show transcription
                        await message.answer(f"🗣 {transcribed_text}")
                        # Process as manager command
                        await process_admin_command(message, transcribed_text, state)
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

async def process_admin_command(message: types.Message, text: str, state: FSMContext):
    """Process manager text commands"""
    text_lower = text.lower()
    
    if 'внешняя crm' in text_lower:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        company_id = getattr(message.bot, 'company_id', 1)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/sales/companies/all') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        company = next((c for c in data if c.get('id') == company_id), None)
                        if company:
                            enabled = company.get('integration_enabled', False)
                            itype = company.get('integration_type', '')
                            if enabled and itype:
                                text = f"✅ <b>Внешняя CRM {itype.upper()} подключена</b>"
                            else:
                                text = "❌ <b>Внешняя CRM не подключена</b>"
                            kb = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="📘 Bitrix24", callback_data="crm_ext:bitrix24")],
                                [InlineKeyboardButton(text="🟣 Kommo", callback_data="crm_ext:kommo")]
                            ])
                            await message.answer(text, parse_mode='HTML', reply_markup=kb)
        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)[:30]}")

    elif 'внутренняя crm' in text_lower:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        company_id = getattr(message.bot, 'company_id', 1)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/sales/companies/all') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        company = next((c for c in data if c.get('id') == company_id), None)
                        if company:
                            crm_type = company.get('crm_type', '')
                            if crm_type == 'internal':
                                text = "✅ <b>Внутренняя CRM включена</b>"
                            else:
                                text = "❌ <b>Внутренняя CRM не подключена</b>"
                            kb = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="✅ Включить" if crm_type != 'internal' else "❌ Отключить", callback_data="crm_int:toggle")],
                                [InlineKeyboardButton(text="⚙️ Статусы", callback_data="crm_int:statuses")]
                            ])
                            await message.answer(text, parse_mode='HTML', reply_markup=kb)
        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)[:30]}")

    elif 'менеджеры' in text_lower:
        company_id = getattr(message.bot, 'company_id', 1)
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/crm/{company_id}/managers') as resp:
                    if resp.status == 200:
                        managers = await resp.json()
                        # Сортировка по монеткам (убывание)
                        managers = sorted(managers, key=lambda x: x.get('coins', 0), reverse=True)
                        text_msg = "👥 <b>Менеджеры компании</b>\n\n"
                        buttons = []
                        if managers:
                            for i, m in enumerate(managers):
                                coins = m.get('coins', 0)
                                leads = m.get('leads_count', 0)
                                name = m.get('full_name', 'Без имени')
                                user_id = m.get('user_id', 0)
                                medal = ['🥇', '🥈', '🥉'][i] if i < 3 else f"{i+1}."
                                text_msg += f"{medal} {name} — {coins}💰\n"
                                buttons.append([InlineKeyboardButton(text=f"📊 {name}", callback_data=f"mgr_kpi:{user_id}")])
                        else:
                            text_msg += "Пока нет менеджеров\n"
                        text_msg += "\n<i>Нажмите для KPI</i>\n<b>Добавить:</b> /join"
                        kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
                        await message.answer(text_msg, parse_mode='HTML', reply_markup=kb)
                    else:
                        await message.answer("📋 Менеджеры: 0\n\nЧтобы добавить: /join")
        except Exception as e:
            logging.error(f"Managers error: {e}")
            await message.answer("📋 Менеджеры: 0\n\nЧтобы добавить: /join")

    elif 'лидерборд' in text_lower:
        company_id = getattr(message.bot, 'company_id', 1)
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            async with aiohttp.ClientSession() as session:
                url = f'{API_BASE_URL}/crm/{company_id}/leaderboard?period=all&sort=coins'
                async with session.get(url) as resp:
                    leaders = await resp.json() if resp.status == 200 else []
                    if not leaders:
                        await message.answer("🏆 Пусто")
                        return
                    text_msg = "🏆 <b>Лидерборд</b> (Всё время, 💰)\n\n"
                    medals = ['🥇', '🥈', '🥉']
                    for i, m in enumerate(leaders[:10]):
                        medal = medals[i] if i < 3 else f"{i+1}."
                        name = m.get('full_name', '?')
                        coins = m.get('coins', 0)
                        text_msg += f"{medal} {name}\n   💰 Монеты: {coins}\n\n"
                    
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="📅 Неделя", callback_data="alb:week:coins"),
                            InlineKeyboardButton(text="📅 Месяц", callback_data="alb:month:coins"),
                            InlineKeyboardButton(text="📅 Всё ✓", callback_data="alb:all:coins")
                        ],
                        [
                            InlineKeyboardButton(text="💰 Монеты ✓", callback_data="alb:all:coins"),
                            InlineKeyboardButton(text="💵 Сумма", callback_data="alb:all:amount"),
                            InlineKeyboardButton(text="✅ Сделки", callback_data="alb:all:deals")
                        ]
                    ])
                    await message.answer(text_msg, parse_mode='HTML', reply_markup=kb)
        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)[:50]}")

    elif 'статус' in text_lower or 'status' in text_lower:
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
        company_id = getattr(message.bot, 'company_id', 1)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/sales/{company_id}/leads',params={'limit':100},timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status==200:
                        data=await resp.json()
                        leads=data.get('leads',[])
                        from datetime import datetime,timedelta
                        week_ago=datetime.now()-timedelta(days=7)
                        week_leads=[l for l in leads if datetime.fromisoformat(l['created_at'].replace('Z','+00:00'))>week_ago and l.get('contact_info') and (l['contact_info'].get('name') or l['contact_info'].get('phone'))]
                        from collections import Counter
                        sources=Counter(l.get('source','web') for l in week_leads)
                        msg=f"📊 <b>Лиды за неделю</b>\n\nВсего: {len(week_leads)}\n\n<b>По источникам:</b>\n"
                        for source,count in sorted(sources.items(), key=lambda x: (1, int(x[0])) if x[0].isdigit() else (0, x[0].lower())):
                            if source.isdigit():
                                # Get widget name from database
                                try:
                                    async with aiohttp.ClientSession() as sess:
                                        async with sess.get(f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{source}') as r:
                                            if r.status == 200:
                                                w = await r.json()
                                                name = w.get('channel_name', f'Widget #{source}').capitalize()
                                                msg+=f"📸 {name} #{source}: {count}\n"
                                            else:
                                                msg+=f"📸 Widget #{source}: {count}\n"
                                except:
                                    msg+=f"📸 Widget #{source}: {count}\n"
                            else:
                                msg+=f"• {source}: {count}\n"
                        msg+="\n<b>Последние 10:</b>\n"
                        for lead in week_leads[:10]:
                            contact=lead.get('contact_info',{})
                            name=contact.get('name','Не указано')
                            phone=contact.get('phone','Не указан')
                            source=lead.get('source','web')
                            # Get channel name if source is ID
                            if source.isdigit():
                                try:
                                    async with aiohttp.ClientSession() as s:
                                        async with s.get(f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{source}') as r:
                                            if r.status == 200:
                                                wd = await r.json()
                                                source_name = f"{wd.get('channel_name','Widget').capitalize()} #{source}"
                                            else:
                                                source_name = f"Widget #{source}"
                                except:
                                    source_name = f"Widget #{source}"
                            else:
                                source_name = source
                            msg+=f"• {name} ({phone}) - {source_name}\n"
                        await message.answer(msg,parse_mode='HTML')
                    else:
                        await message.answer("⚠️ Не удалось получить лиды")
        except Exception as e:
            logging.error(f"Week leads error: {e}")
            await message.answer("❌ Ошибка")
    elif 'лиды за месяц' in text_lower:
        company_id = getattr(message.bot, 'company_id', 1)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/sales/{company_id}/leads',params={'limit':200},timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status==200:
                        data=await resp.json()
                        leads=data.get('leads',[])
                        from datetime import datetime,timedelta
                        month_ago=datetime.now()-timedelta(days=30)
                        month_leads=[l for l in leads if datetime.fromisoformat(l['created_at'].replace('Z','+00:00'))>month_ago and l.get('contact_info') and (l['contact_info'].get('name') or l['contact_info'].get('phone'))]
                        from collections import Counter
                        sources=Counter(l.get('source','web') for l in month_leads)
                        msg=f"📊 <b>Лиды за месяц</b>\n\nВсего: {len(month_leads)}\n\n<b>По источникам:</b>\n"
                        for source,count in sorted(sources.items(), key=lambda x: (1, int(x[0])) if x[0].isdigit() else (0, x[0].lower())):
                            if source.isdigit():
                                # Get widget name from database
                                try:
                                    async with aiohttp.ClientSession() as sess:
                                        async with sess.get(f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{source}') as r:
                                            if r.status == 200:
                                                w = await r.json()
                                                name = w.get('channel_name', f'Widget #{source}').capitalize()
                                                msg+=f"📸 {name} #{source}: {count}\n"
                                            else:
                                                msg+=f"📸 Widget #{source}: {count}\n"
                                except:
                                    msg+=f"📸 Widget #{source}: {count}\n"
                            else:
                                msg+=f"• {source}: {count}\n"
                        msg+="\n<b>Последние 10:</b>\n"
                        for lead in month_leads[:10]:
                            contact=lead.get('contact_info',{})
                            name=contact.get('name','Не указано')
                            phone=contact.get('phone','Не указан')
                            source=lead.get('source','web')
                            # Get channel name if source is ID
                            if source.isdigit():
                                try:
                                    async with aiohttp.ClientSession() as s:
                                        async with s.get(f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{source}') as r:
                                            if r.status == 200:
                                                wd = await r.json()
                                                source_name = f"{wd.get('channel_name','Widget').capitalize()} #{source}"
                                            else:
                                                source_name = f"Widget #{source}"
                                except:
                                    source_name = f"Widget #{source}"
                            else:
                                source_name = source
                            msg+=f"• {name} ({phone}) - {source_name}\n"
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
                    f'{API_BASE_URL}/sales/{company_id}/leads?limit=50',
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        leads = data.get('leads', [])
                        # Filter out empty leads (no name and no phone)
                        leads = [l for l in leads if l.get('contact_info') and l['contact_info'].get('phone')]
                        
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
                                # Get widget name from database
                                try:
                                    async with aiohttp.ClientSession() as sess:
                                        async with sess.get(f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{source}') as r:
                                            if r.status == 200:
                                                w = await r.json()
                                                name = w.get('channel_name', f'Widget #{source}').capitalize()
                                                emoji_name = f'📸 {name} #{source}'
                                            else:
                                                emoji_name = f'📸 Widget #{source}'
                                except:
                                    emoji_name = f'📸 Widget #{source}'
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
                            # Get channel name if source is ID
                            if source.isdigit():
                                try:
                                    async with aiohttp.ClientSession() as s:
                                        async with s.get(f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{source}') as r:
                                            if r.status == 200:
                                                wd = await r.json()
                                                source = f"{wd.get('channel_name','Widget').capitalize()} #{source}"
                                            else:
                                                source = f"Widget #{source}"
                                except:
                                    source = f"Widget #{source}"
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
                                wtype = w.get('widget_type', 'classic')
                                url_path = 'avatar' if wtype == 'avatar' else 'w'
                                widget_url = f"https://bizdnai.com/{url_path}/{company_id}/{widget_id}"
                                
                                msg_parts.append(f"• {channel_display} (ID: {widget_id})")
                                msg_parts.append(f"  🔗 {widget_url}")
                                
                                buttons.append([
                                    InlineKeyboardButton(text=f"✏️ Edit #{widget_id}", callback_data=f"edit_widget_{widget_id}"),
                                    InlineKeyboardButton(text=f"🗑 Delete #{widget_id}", callback_data=f"delete_widget_{widget_id}")
                                ])
                                buttons.append([
                                    InlineKeyboardButton(text=f"📲 QR код #{widget_id}", callback_data=f"qr_widget_{widget_id}")
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
    
    elif 'тариф' in text_lower:
        company_id = getattr(message.bot, 'company_id', 1)
        text = await format_tier_info(company_id)
        await message.answer(text, parse_mode='HTML')
    
    elif 'меню' in text_lower or 'menu' in text_lower:
        await message.answer("🏠 <b>Главное меню</b>", reply_markup=get_admin_keyboard(), parse_mode='HTML')
    
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
    
    elif ('интеграция' in text_lower or 'integration' in text_lower) and 'внешняя' not in text_lower and 'внутренняя' not in text_lower:
        company_id = getattr(message.bot, 'company_id', 1)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/sales/companies/all') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        companies = data if isinstance(data, list) else []
                        company = next((c for c in companies if c.get('id') == company_id), None)
                        
                        if company:
                            enabled = company.get('integration_enabled', False)
                            itype = company.get('integration_type', 'CRM')
                            
                            if enabled:
                                text = f"✅ <b>Интеграция {itype.upper()} активна</b>\n\n"
                                text += "Лиды из виджетов автоматически отправляются в CRM."
                                btn_text = "❌ Выключить интеграцию"
                            else:
                                text = "❌ <b>Внутренняя CRM не подключена</b>\n\n"
                                text += "Лиды сохраняются, но не обрабатываются!\nПодключите CRM для автоматизации."
                                btn_text = "✅ Включить интеграцию"
                            
                            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn_text, callback_data="toggle_crm_integration")]])
                            
                            await message.answer(text, parse_mode='HTML', reply_markup=kb)
                        else:
                            await message.answer("⚠️ Компания не найдена")
                    else:
                        await message.answer("⚠️ Ошибка получения данных")
        except Exception as e:
            logging.error(f"Integration check error: {e}")
            await message.answer(f"❌ Ошибка: {str(e)[:50]}")
    
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
                                
                                # Button shows current status
                                toggle_text = "✅ ON" if w.get('is_active') else "❌ OFF"
                                
                                buttons.append([
                                    InlineKeyboardButton(text=f"✏️ {domain}", callback_data=f"editwidget_{wid}"),
                                    InlineKeyboardButton(text=toggle_text, callback_data=f"togglewidget_{wid}"),
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
    if not is_admin(message.from_user.id, message.bot):
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
    if not is_admin(message.from_user.id, message.bot):
        await state.clear()
        return
    
    greeting = message.text.strip()
    if greeting.lower() == 'skip':
        greeting = None
    
    data = await state.get_data()
    channel_name_raw = data.get('channel_name', '')
    widget_type = data.get('widget_type', 'classic')
    company_id = message.bot.company_id
    
    await message.answer("⏳ Создаю канал...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{API_BASE_URL}/sales/companies/{company_id}/widgets',
                json={
                    'channel_name': channel_name_raw,
                    'greeting_message': greeting,
                    'widget_type': widget_type
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    wid = result.get('id', '')
                    url_path = 'avatar' if widget_type == 'avatar' else 'w'
                    url = f"https://bizdnai.com/{url_path}/{company_id}/{wid}"
                    type_icon = "🎭" if widget_type == 'avatar' else "📱"
                    
                    await message.answer(
                        f"🎉 <b>Канал создан!</b>\n\n"
                        f"{type_icon} Тип: {'Аватар' if widget_type == 'avatar' else 'Классический'}\n"
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
    if not is_admin(message.from_user.id, message.bot):
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
    if not is_admin(message.from_user.id, message.bot):
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
    if not is_admin(message.from_user.id, message.bot):
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




@router.message(ManagerFlow.editing_social_greeting)
async def process_social_greeting(message: types.Message, state: FSMContext):
    """Process new social widget greeting"""
    if not is_admin(message.from_user.id, message.bot):
        await message.answer("❌ Недостаточно прав")
        return

    data = await state.get_data()
    widget_id = data.get('editing_social_widget_id')
    company_id = getattr(message.bot, 'company_id', 1)
    new_greeting = message.text

    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{widget_id}',
                json={'greeting_message': new_greeting}
            ) as resp:
                if resp.status == 200:
                    await message.answer(
                        f"✅ Приветствие канала #{widget_id} обновлено!\n\n"
                        "AI переводит на все языки...",
                        parse_mode='HTML'
                    )
                else:
                    await message.answer(f"❌ Ошибка обновления (код {resp.status})")
    except Exception as e:
        logging.error(f"Update social greeting error: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:50]}")

    await state.clear()

@router.message(ManagerFlow.editing_social_name)
async def process_social_name(message: types.Message, state: FSMContext):
    """Process new social widget name"""
    if not is_admin(message.from_user.id, message.bot):
        await message.answer("❌ Недостаточно прав")
        return

    data = await state.get_data()
    widget_id = data.get('editing_social_widget_id')
    company_id = getattr(message.bot, 'company_id', 1)
    new_name = message.text

    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{widget_id}',
                json={'channel_name': new_name}
            ) as resp:
                if resp.status == 200:
                    await message.answer(f"✅ Название канала изменено на: {new_name}")
                else:
                    await message.answer(f"❌ Ошибка обновления (код {resp.status})")
    except Exception as e:
        logging.error(f"Update social name error: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:50]}")

    await state.clear()


# === Language Menu Handler ===
@router.message(F.text == "🌍 Язык")
async def manager_language_menu(message: types.Message):
    """Show language selection for manager reports"""
    if not is_admin(message.from_user.id, message.bot):
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    lang_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="manager_lang_ru"),
         InlineKeyboardButton(text="🇺🇸 English", callback_data="manager_lang_en")],
        [InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="manager_lang_kz"),
         InlineKeyboardButton(text="🇰🇬 Кыргызча", callback_data="manager_lang_ky")],
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="manager_lang_uz"),
         InlineKeyboardButton(text="🇺🇦 Українська", callback_data="manager_lang_uk")]
    ])
    
    await message.answer("🌍 Выберите язык для отчётов о лидах:", reply_markup=lang_kb)

@router.callback_query(F.data.startswith("manager_lang_"))
async def set_manager_language_callback(callback: types.CallbackQuery):
    """Handle manager language selection"""
    if not is_admin(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    lang = callback.data.split("_")[-1]
    company_id = getattr(callback.bot, 'company_id', 1)
    
    lang_names = {
        'ru': '🇷🇺 Русский', 'en': '🇺🇸 English', 'kz': '🇰🇿 Қазақша',
        'ky': '🇰🇬 Кыргызча', 'uz': '🇺🇿 O\'zbekcha', 'uk': '🇺🇦 Українська'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f'{API_BASE_URL}/sales/companies/{company_id}/language',
                json={"language": lang},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    await callback.message.edit_text(f"✅ Язык отчётов изменён на: {lang_names.get(lang, lang)}")
                else:
                    await callback.message.edit_text("❌ Ошибка при смене языка")
    except Exception as e:
        logging.error(f"Language change error: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {str(e)[:50]}")
    
    await callback.answer()


# === GENERAL HANDLER (MUST BE LAST) ===

@router.message(ManagerFlow.editing_widget_domain)
async def process_edit_domain(message: types.Message, state: FSMContext):
    """Process editing widget domain"""
    if not is_admin(message.from_user.id, message.bot):
        await state.clear()
        return
    
    domain = message.text.strip().lower().replace('http://', '').replace('https://', '').replace('www.', '')
    if not domain or '.' not in domain:
        await message.answer("❌ Неверный формат домена. Попробуйте ещё раз:")
        return
    
    data = await state.get_data()
    widget_id = data.get('editing_widget_id', '')
    company_id = getattr(message.bot, 'company_id', 1)
    
    status_msg = await message.answer("⏳ Обновляю домен...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f'{API_BASE_URL}/sales/{company_id}/web-widgets/{widget_id}',
                json={'domain': domain},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    await status_msg.delete()
                    await message.answer(
                        f"✅ <b>Домен обновлён!</b>\n\n"
                        f"🌐 Новый домен: {domain}",
                        parse_mode='HTML'
                    )
                else:
                    await status_msg.delete()
                    await message.answer("❌ Ошибка обновления домена")
    except Exception as e:
        await status_msg.delete()
        await message.answer(f"❌ Ошибка: {str(e)[:100]}")
    finally:
        await state.clear()




@router.callback_query(F.data.startswith("crm_ext:"))
async def handle_external_crm(callback: types.CallbackQuery):
    """Handle external CRM settings (Bitrix24, Kommo) - toggle ON/OFF"""
    if not is_admin(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    action = callback.data.split(":")[1]
    company_id = getattr(callback.bot, 'company_id', 1)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Получаем текущий статус
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/companies/all') as resp:
                data = await resp.json()
                company = next((c for c in data if c.get('id') == company_id), None)
                current_enabled = company.get('integration_enabled', False) if company else False
                current_type = company.get('integration_type', '') if company else ''
    except:
        current_enabled = False
        current_type = ''
    
    if action == "bitrix24":
        # Toggle: если уже включен Bitrix24 - выключаем, иначе включаем
        if current_enabled and current_type == 'bitrix24':
            # Выключаем
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(f'{API_BASE_URL}/sales/company/upsert',
                        json={'id': company_id, 'integration_enabled': False})
                await callback.answer("❌ Bitrix24 выключен")
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Включить Bitrix24", callback_data="crm_ext:bitrix24")],
                    [InlineKeyboardButton(text="🟣 Kommo", callback_data="crm_ext:kommo")]
                ])
                await callback.message.edit_text("❌ <b>Bitrix24 выключен</b>\n\nЛиды сохраняются только в BizDNAi.", parse_mode='HTML', reply_markup=kb)
            except Exception as e:
                await callback.answer(f"❌ Ошибка: {str(e)[:30]}", show_alert=True)
        else:
            # Включаем
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(f'{API_BASE_URL}/sales/company/upsert',
                        json={'id': company_id, 'integration_type': 'bitrix24', 'integration_enabled': True})
                await callback.answer("✅ Bitrix24 включён!")
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Выключить Bitrix24", callback_data="crm_ext:bitrix24")],
                    [InlineKeyboardButton(text="🟣 Kommo", callback_data="crm_ext:kommo")]
                ])
                await callback.message.edit_text("✅ <b>Bitrix24 включён!</b>\n\nЛиды автоматически отправляются в Bitrix24.", parse_mode='HTML', reply_markup=kb)
            except Exception as e:
                await callback.answer(f"❌ Ошибка: {str(e)[:30]}", show_alert=True)
    
    elif action == "kommo":
        # Toggle для Kommo
        if current_enabled and current_type == 'kommo':
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(f'{API_BASE_URL}/sales/company/upsert',
                        json={'id': company_id, 'integration_enabled': False})
                await callback.answer("❌ Kommo выключен")
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📘 Bitrix24", callback_data="crm_ext:bitrix24")],
                    [InlineKeyboardButton(text="✅ Включить Kommo", callback_data="crm_ext:kommo")]
                ])
                await callback.message.edit_text("❌ <b>Kommo выключен</b>\n\nЛиды сохраняются только в BizDNAi.", parse_mode='HTML', reply_markup=kb)
            except Exception as e:
                await callback.answer(f"❌ Ошибка: {str(e)[:30]}", show_alert=True)
        else:
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(f'{API_BASE_URL}/sales/company/upsert',
                        json={'id': company_id, 'integration_type': 'kommo', 'integration_enabled': True})
                await callback.answer("✅ Kommo включён!")
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📘 Bitrix24", callback_data="crm_ext:bitrix24")],
                    [InlineKeyboardButton(text="❌ Выключить Kommo", callback_data="crm_ext:kommo")]
                ])
                await callback.message.edit_text("✅ <b>Kommo включён!</b>\n\nЛиды автоматически отправляются в Kommo.", parse_mode='HTML', reply_markup=kb)
            except Exception as e:
                await callback.answer(f"❌ Ошибка: {str(e)[:30]}", show_alert=True)
    
    elif action == "disable":
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(f'{API_BASE_URL}/sales/company/upsert',
                    json={'id': company_id, 'integration_enabled': False})
            await callback.answer("❌ Внешняя CRM отключена")
            await callback.message.edit_text("❌ <b>Внешняя CRM отключена</b>\n\nЛиды сохраняются только в BizDNAi.", parse_mode='HTML')
        except Exception as e:
            await callback.answer(f"❌ Ошибка: {str(e)[:30]}", show_alert=True)

@router.callback_query(F.data == "toggle_crm_integration")
async def toggle_crm_integration_callback(callback: types.CallbackQuery):
    """Toggle CRM integration ON/OFF for manager"""
    if not is_admin(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    company_id = getattr(callback.bot, 'company_id', 1)
    
    try:
        async with aiohttp.ClientSession() as session:
            # Get current status
            async with session.get(f'{API_BASE_URL}/sales/companies/all') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    companies = data if isinstance(data, list) else []
                    company = next((c for c in companies if c.get('id') == company_id), None)
                    
                    if company:
                        new_status = not company.get('integration_enabled', False)
                        
                        # Update in DB
                        async with session.post(
                            f'{API_BASE_URL}/sales/company/upsert',
                            json={'id': company_id, 'integration_enabled': new_status}
                        ) as update_resp:
                            if update_resp.status == 200:
                                status_text = "включена ✅" if new_status else "выключена ❌"
                                await callback.answer(f"Интеграция {status_text}")
                                
                                # Update message
                                itype = company.get('integration_type', 'CRM')
                                if new_status:
                                    text = f"✅ <b>Интеграция {itype.upper()} активна</b>\n\nЛиды из виджетов автоматически отправляются в CRM."
                                    btn_text = "❌ Выключить интеграцию"
                                else:
                                    text = "❌ <b>Интеграция CRM выключена</b>\n\nЛиды сохраняются только в BizDNAi."
                                    btn_text = "✅ Включить интеграцию"
                                
                                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                                kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn_text, callback_data="toggle_crm_integration")]])
                                
                                await callback.message.edit_text(text, parse_mode='HTML', reply_markup=kb)
                            else:
                                await callback.answer("❌ Ошибка обновления", show_alert=True)
                    else:
                        await callback.answer("❌ Компания не найдена", show_alert=True)
    except Exception as e:
        logging.error(f"Toggle CRM integration error: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(ManagerFlow.editing_status_coins)
async def process_status_coins_input(message: types.Message, state: FSMContext):
    """Process new coins value"""
    try:
        coins = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число (например: 50 или -10)")
        return
    
    data = await state.get_data()
    status_id = data.get('editing_status_code')
    company_id = data.get('editing_company_id')
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f'{API_BASE_URL}/crm/{company_id}/statuses/{status_id}',
                json={'coins': coins}
            ) as resp:
                if resp.status == 200:
                    await message.answer(
                        f"✅ Монетки обновлены: {coins} 💰",
                        reply_markup=get_admin_keyboard()
                    )
                else:
                    await message.answer("❌ Ошибка обновления")
    except Exception as e:
        logging.error(f"Update coins: {e}")
        await message.answer("❌ Ошибка сохранения")
    
    await state.clear()


@router.callback_query(F.data.startswith("status_edit:"))
async def edit_status_coins(callback: types.CallbackQuery, state: FSMContext):
    """Start editing status coins"""
    status_code = callback.data.split(":")[1]
    company_id = getattr(callback.bot, 'company_id', 1)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/statuses') as resp:
                if resp.status == 200:
                    statuses = await resp.json()
                    status = next((s for s in statuses if str(s.get('id', s.get('code'))) == status_code), None)
                    if status:
                        await state.update_data(
                            editing_status_code=status_code, 
                            editing_company_id=company_id
                        )
                        await state.set_state(ManagerFlow.editing_status_coins)
                        await callback.message.edit_text(
                            f"Введите новое количество монеток для статуса "
                            f"\"{status['emoji']} {status['name']}\":\n\n"
                            f"Текущее значение: {status['coins']} 💰"
                        )
                        await callback.answer()
                        return
    except Exception as e:
        logging.error(f"Edit status: {e}")
    await callback.answer("❌ Ошибка")


@router.callback_query(F.data.startswith("confirm_deal:"))
async def confirm_deal_callback(callback: types.CallbackQuery):
    """Confirm deal (admin only)"""
    if not is_admin(callback.from_user.id, callback.bot):
        await callback.answer("❌ Только для админа", show_alert=True)
        return
    
    deal_id = int(callback.data.split(":")[1])
    company_id = getattr(callback.bot, 'company_id', 1)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f'{API_BASE_URL}/crm/{company_id}/deals/{deal_id}/confirm'
            ) as resp:
                if resp.status == 200:
                    # Обновить сообщение
                    new_text = callback.message.text + "\n\n✅ <b>Сделка подтверждена!</b>"
                    await callback.message.edit_text(new_text, parse_mode='HTML')
                    await callback.answer("✅ Подтверждено!")
                else:
                    await callback.answer("❌ Ошибка", show_alert=True)
    except Exception as e:
        logging.error(f"Confirm deal: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

@router.message()
async def handle_text(message: types.Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    
    if is_admin(message.from_user.id, message.bot):
        await process_admin_command(message, message.text, state)
        return

    user_id = str(message.from_user.id)
    username = message.from_user.username or f"user_{user_id}"
    
    # Get language for status message
    state_data = await state.get_data()
    language = state_data.get('language', 'ru')
    
    status_messages = {
        'ru': '⏳ Думаю...',
        'en': '⏳ Thinking...',
        'kz': '⏳ Ойланудамын...',
        'ky': '⏳ Ойлонуп жатам...',
        'uz': '⏳ O\'ylayapman...',
        'uk': '⏳ Думаю...'
    }
    
    status_msg = await message.answer(status_messages.get(language, '⏳ Думаю...'))
    
    data = state_data
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
    """Handle Create Widget button - ask for widget type"""
    if not is_admin(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎭 С аватаром", callback_data="widgettype_avatar")],
        [InlineKeyboardButton(text="📱 Классический", callback_data="widgettype_classic")]
    ])
    await callback.message.answer("📝 <b>Выберите тип виджета:</b>", reply_markup=keyboard, parse_mode='HTML')
    await callback.answer()

@router.callback_query(F.data.startswith("widgettype_"))
async def widget_type_callback(callback: types.CallbackQuery, state: FSMContext):
    widget_type = callback.data.replace("widgettype_", "")
    await state.update_data(widget_type=widget_type)
    type_name = "🎭 Аватар" if widget_type == "avatar" else "📱 Классический"
    await state.set_state(ManagerFlow.entering_channel_name)
    await callback.message.edit_text(f"Тип: {type_name}\n\nВведите название канала:", parse_mode='HTML')
    await callback.answer()

@router.callback_query(F.data.startswith("edit_widget_"))
async def edit_widget_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle 'Edit Widget' button - show edit menu for social widget"""
    if not is_admin(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return

    widget_id = callback.data.split("_")[-1]
    company_id = getattr(callback.bot, 'company_id', 1)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{widget_id}') as resp:
                if resp.status == 200:
                    widget = await resp.json()
                    channel_name = widget.get('channel_name', 'Unknown')
                    greeting = (widget.get('greeting_message') or 'Не задано')[:50]
                    
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💬 Изменить приветствие", callback_data=f"editsocialgreeting_{widget_id}")],
                        [InlineKeyboardButton(text="📛 Изменить название", callback_data=f"editsocialname_{widget_id}")],
                        [InlineKeyboardButton(text="« Назад к каналам", callback_data="back_to_channels")]
                    ])
                    
                    await callback.message.edit_text(
                        f"✏️ <b>Редактирование канала #{widget_id}</b>\n\n"
                        f"📛 Название: {channel_name}\n"
                        f"💬 Приветствие: {greeting}...\n\n"
                        "Выберите что хотите изменить:",
                        reply_markup=keyboard,
                        parse_mode='HTML'
                    )
                else:
                    await callback.message.answer("❌ Канал не найден")
    except Exception as e:
        logging.error(f"Edit widget error: {e}")
        await callback.message.answer(f"❌ Ошибка: {str(e)[:50]}")
    
    await callback.answer()
    await callback.answer()

# === QR Code Generator ===
@router.callback_query(F.data.startswith("qr_widget_"))
async def qr_widget_callback(callback: types.CallbackQuery):
    """Generate QR code for social widget URL"""
    if not is_admin(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return

    widget_id = callback.data.split("_")[-1]
    company_id = getattr(callback.bot, 'company_id', 1)
    # Get widget type
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{widget_id}') as r:
                wdata = await r.json() if r.status == 200 else {}
        wtype = wdata.get('widget_type', 'classic')
    except:
        wtype = 'classic'
    url_path = 'avatar' if wtype == 'avatar' else 'w'
    url = f"https://bizdnai.com/{url_path}/{company_id}/{widget_id}"

    try:
        import qrcode
        from aiogram.types import BufferedInputFile
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((250, 250))
        
        # Save to buffer
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Send as photo
        await callback.message.answer_photo(
            photo=BufferedInputFile(buffer.getvalue(), filename=f"qr_{widget_id}.png"),
            caption=f"📲 QR код для канала #{widget_id}\n🔗 {url}"
        )
        await callback.answer("✅ QR код создан")
    except Exception as e:
        logging.error(f"QR generation error: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)[:30]}", show_alert=True)

@router.callback_query(F.data.startswith("delete_widget_"))
async def delete_widget_callback(callback: types.CallbackQuery):
    """Handle 'Delete Widget' button"""
    if not is_admin(callback.from_user.id, callback.bot):
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
    """Show edit menu for web widget"""
    if not is_admin(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    widget_id = callback.data.split("_")[1]
    
    # Show submenu
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Изменить приветствие", callback_data=f"editgreeting_{widget_id}")],
        [InlineKeyboardButton(text="🌐 Изменить домен", callback_data=f"editdomain_{widget_id}")],
        [InlineKeyboardButton(text="« Назад", callback_data=f"back_to_widgets")]
    ])
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование виджета #{widget_id}</b>\n\n"
        "Выберите что хотите изменить:",
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    await callback.answer()

@router.callback_query(F.data.startswith("editgreeting_"))
async def edit_greeting_callback(callback: types.CallbackQuery, state: FSMContext):
    """Start editing greeting"""
    if not is_admin(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    widget_id = callback.data.split("_")[1]
    await state.update_data(editing_widget_id=widget_id)
    await state.set_state(ManagerFlow.editing_widget_greeting)
    
    await callback.message.answer(
        f"💬 <b>Изменение приветствия виджета #{widget_id}</b>\n\n"
        "Введите новое приветствие на русском:\n"
        "(AI переведёт на все языки)",
        parse_mode='HTML'
    )
    await callback.answer()

@router.callback_query(F.data.startswith("editdomain_"))
async def edit_domain_callback(callback: types.CallbackQuery, state: FSMContext):
    """Start editing domain"""
    if not is_admin(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    widget_id = callback.data.split("_")[1]
    await state.update_data(editing_widget_id=widget_id)
    await state.set_state(ManagerFlow.editing_widget_domain)
    
    await callback.message.answer(
        f"🌐 <b>Изменение домена виджета #{widget_id}</b>\n\n"
        "Введите новый домен (например: example.com):",
        parse_mode='HTML'
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_widgets")
async def back_to_widgets_callback(callback: types.CallbackQuery):
    """Return to widgets list"""
    if not is_admin(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    # Trigger widgets command
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data.startswith("togglewidget_"))
async def toggle_webwidget_callback(callback: types.CallbackQuery):
    """Toggle web widget active status"""
    if not is_admin(callback.from_user.id, callback.bot):
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
                    
                    # Refresh widget list with updated status
                    async with session.get(f'{API_BASE_URL}/sales/{company_id}/web-widgets') as resp2:
                        if resp2.status == 200:
                            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                            widgets = await resp2.json()
                            msg = "🌐 <b>Веб-виджеты</b>\n\n"
                            buttons = []
                            
                            if widgets:
                                for w in widgets:
                                    status_icon = '✅' if w.get('is_active') else '❌'
                                    wid = w['id']
                                    domain = w['domain']
                                    greeting = w.get('greeting_ru', 'Не установлено')[:30]
                                    msg += f"{status_icon} <b>{domain}</b> (ID: {wid})\n"
                                    msg += f"   {greeting}...\n\n"
                                    
                                    # Button shows current status
                                    toggle_text = "✅ ON" if w.get('is_active') else "❌ OFF"
                                    
                                    buttons.append([
                                        InlineKeyboardButton(text=f"✏️ {domain}", callback_data=f"editwidget_{wid}"),
                                        InlineKeyboardButton(text=toggle_text, callback_data=f"togglewidget_{wid}"),
                                        InlineKeyboardButton(text="🗑", callback_data=f"delwidget_{wid}")
                                    ])
                            else:
                                msg += "Виджетов пока нет\n"
                            
                            buttons.append([InlineKeyboardButton(text="➕ Создать виджет", callback_data=f"createwidget_{company_id}")])
                            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                            
                            # Update message with new buttons
                            await callback.message.edit_text(msg, reply_markup=keyboard, parse_mode='HTML')
                else:
                    await callback.answer("❌ Ошибка", show_alert=True)
    except Exception as e:
        await callback.answer("❌ Ошибка", show_alert=True)

@router.callback_query(F.data.startswith("delwidget_"))
async def delete_webwidget_callback(callback: types.CallbackQuery):
    """Delete web widget"""
    if not is_admin(callback.from_user.id, callback.bot):
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
    if not is_admin(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    await state.set_state(ManagerFlow.entering_widget_domain)
    await callback.message.answer(
        "🌐 <b>Создание веб-виджета</b>\n\n"
        "Введите домен (например: example.com):",
        parse_mode='HTML'
    )
    await callback.answer()


# === Social Widget Edit Handlers ===
@router.callback_query(F.data.startswith("editsocialgreeting_"))
async def edit_social_greeting_callback(callback: types.CallbackQuery, state: FSMContext):
    """Start editing social widget greeting"""
    if not is_admin(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return

    widget_id = callback.data.split("_")[-1]
    await state.update_data(editing_social_widget_id=widget_id)
    await state.set_state(ManagerFlow.editing_social_greeting)

    await callback.message.answer(
        f"💬 <b>Изменение приветствия канала #{widget_id}</b>\n\n"
        "Введите новое приветствие на русском:\n"
        "(AI автоматически переведёт на все языки)",
        parse_mode='HTML'
    )
    await callback.answer()

@router.callback_query(F.data.startswith("editsocialname_"))
async def edit_social_name_callback(callback: types.CallbackQuery, state: FSMContext):
    """Start editing social widget name"""
    if not is_admin(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return

    widget_id = callback.data.split("_")[-1]
    await state.update_data(editing_social_widget_id=widget_id)
    await state.set_state(ManagerFlow.editing_social_name)

    await callback.message.answer(
        f"📛 <b>Изменение названия канала #{widget_id}</b>\n\n"
        "Введите новое название (например: Instagram, Facebook):",
        parse_mode='HTML'
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_channels")
async def back_to_channels_callback(callback: types.CallbackQuery):
    """Return to channels list"""
    await callback.message.delete()
    await callback.answer()

@router.message(ManagerFlow.editing_social_greeting)
async def process_social_greeting(message: types.Message, state: FSMContext):
    """Process new social widget greeting"""
    if not is_admin(message.from_user.id, message.bot):
        await message.answer("❌ Недостаточно прав")
        return

    data = await state.get_data()
    widget_id = data.get('editing_social_widget_id')
    company_id = getattr(message.bot, 'company_id', 1)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{widget_id}',
                json={'greeting_message': message.text}
            ) as resp:
                if resp.status == 200:
                    await message.answer(f"✅ Приветствие канала #{widget_id} обновлено!")
                else:
                    await message.answer(f"❌ Ошибка обновления (код {resp.status})")
    except Exception as e:
        logging.error(f"Update social greeting error: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:50]}")

    await state.clear()

@router.message(ManagerFlow.editing_social_name)
async def process_social_name(message: types.Message, state: FSMContext):
    """Process new social widget name"""
    if not is_admin(message.from_user.id, message.bot):
        await message.answer("❌ Недостаточно прав")
        return

    data = await state.get_data()
    widget_id = data.get('editing_social_widget_id')
    company_id = getattr(message.bot, 'company_id', 1)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{widget_id}',
                json={'channel_name': message.text}
            ) as resp:
                if resp.status == 200:
                    await message.answer(f"✅ Название канала изменено на: {message.text}")
                else:
                    await message.answer(f"❌ Ошибка обновления (код {resp.status})")
    except Exception as e:
        logging.error(f"Update social name error: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:50]}")

    await state.clear()


# === Tier Command Handler ===
async def format_tier_info(company_id: int) -> str:
    """Format tier info for manager - current tier and usage only"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/{company_id}/tier-usage') as resp:
                if resp.status != 200:
                    return "❌ Ошибка получения данных"
                usage = await resp.json()
        
        text = f"💳 <b>Ваш тариф</b>\n\n"
        text += f"📦 <b>Тариф:</b> {usage['tier_name']}\n"
        
        if usage.get('tier_expiry'):
            text += f"⏰ Действует до: {usage['tier_expiry'][:10]}\n"
        
        text += f"\n📈 <b>Использование этого месяца:</b>\n"
        leads_pct = int(usage['leads_used'] / usage['leads_limit'] * 100) if usage['leads_limit'] > 0 else 0
        text += f"👥 Лиды: {usage['leads_used']}/{usage['leads_limit']} ({leads_pct}%)\n"
        text += f"🌐 Веб-виджеты: {usage['web_widgets_used']}/{usage['web_widgets_limit']}\n"
        text += f"📱 Соц. виджеты: {usage['social_widgets_used']}/{usage['social_widgets_limit']}\n"
        
        text += f"\n─────────────────\n"
        text += f"📄 <b>Все тарифы:</b>\n"
        text += f"🔗 https://bizdnai.com/sales/pricing.html\n"
        text += f"\n📧 Смена тарифа: ceo@bizdnai.com"
        
        # Send pricing email
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(f'{API_BASE_URL}/sales/{company_id}/send-pricing-email')
        except:
            pass
        
        return text
    except Exception as e:
        logging.error(f"Tier info error: {e}")
        return f"❌ Ошибка: {str(e)[:50]}"


# ============ CRM TYPE SELECTION ============

@router.message(F.text == "🔌 Внешняя CRM")
async def admin_external_crm(message: types.Message):
    """External CRM integrations (Bitrix24, Kommo, AmoCRM)"""
    if not is_admin(message.from_user.id, message.bot):
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📘 Bitrix24", callback_data="crm_ext:bitrix24")],
        [InlineKeyboardButton(text="🟣 Kommo (amoCRM)", callback_data="crm_ext:kommo")],
        [InlineKeyboardButton(text="❌ Отключить внешнюю CRM", callback_data="crm_ext:disable")]
    ])
    
    await message.answer(
        "🔌 <b>Внешняя CRM</b>\n\n"
        "Выберите систему для интеграции.\n"
        "Лиды будут автоматически отправляться в выбранную CRM.",
        parse_mode='HTML',
        reply_markup=kb
    )

@router.message(F.text == "📊 Внутренняя CRM")
async def admin_internal_crm(message: types.Message):
    """Internal BizDNAi CRM"""
    if not is_admin(message.from_user.id, message.bot):
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    company_id = getattr(message.bot, 'company_id', 1)
    
    # Get current CRM status
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/stats') as resp:
                if resp.status == 200:
                    stats = await resp.json()
                    total = stats.get('total', 0)
                    today = stats.get('today', 0)
                else:
                    total, today = 0, 0
    except:
        total, today = 0, 0
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Включить внутреннюю CRM", callback_data="crm_int:enable")],
        [InlineKeyboardButton(text="❌ Отключить внутреннюю CRM", callback_data="crm_int:disable")],
        [InlineKeyboardButton(text="⚙️ Настройки статусов", callback_data="crm_int:statuses")],
        [InlineKeyboardButton(text="💰 Настройки монеток", callback_data="crm_int:coins")]
    ])
    
    await message.answer(
        f"📊 <b>Внутренняя CRM BizDNAi</b>\n\n"
        f"📋 Лидов всего: {total}\n"
        f"📅 Лидов сегодня: {today}\n\n"
        f"Функции:\n"
        f"• Статусы лидов с монетками\n"
        f"• Заметки и история\n"
        f"• Лидерборд менеджеров\n"
        f"• AI-анализ клиентов",
        parse_mode='HTML',
        reply_markup=kb
    )

@router.callback_query(F.data.startswith("crm_int:"))
async def handle_internal_crm(callback: types.CallbackQuery):
    """Handle internal CRM settings"""
    action = callback.data.split(":")[1]
    company_id = getattr(callback.bot, 'company_id', 1)
    
    if action == "toggle":
        # Переключить статус
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/sales/companies/all') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        company = next((c for c in data if c.get('id') == company_id), None)
                        current = company.get('crm_type') if company else None
                        new_type = None if current == 'internal' else 'internal'
                        await session.post(f'{API_BASE_URL}/sales/company/upsert', json={'id': company_id, 'crm_type': new_type})
                        if new_type == 'internal':
                            await callback.answer("✅ Внутренняя CRM включена!")
                            await callback.message.edit_text("✅ <b>Внутренняя CRM включена!</b>", parse_mode='HTML')
                        else:
                            await callback.answer("❌ Внутренняя CRM отключена")
                            await callback.message.edit_text("❌ <b>Внутренняя CRM отключена</b>", parse_mode='HTML')
        except Exception as e:
            await callback.answer(f"❌ Ошибка: {str(e)[:30]}")
        return
    
    if action == "enable":
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(f'{API_BASE_URL}/sales/company/upsert', json={'id': company_id, 'crm_type': 'internal'})
            await callback.answer("✅ Внутренняя CRM включена!")
            await callback.message.edit_text("✅ <b>Внутренняя CRM включена!</b>\n\nТеперь менеджеры могут работать с лидами через /join", parse_mode='HTML')
        except:
            await callback.answer("❌ Ошибка")
    
    elif action == "disable":
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(f'{API_BASE_URL}/sales/company/upsert', json={'id': company_id, 'crm_type': None})
            await callback.answer("❌ Внутренняя CRM отключена")
            await callback.message.edit_text("❌ <b>Внутренняя CRM отключена</b>", parse_mode='HTML')
        except:
            await callback.answer("❌ Ошибка")
    
    elif action == "statuses":
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/crm/{company_id}/statuses') as resp:
                    if resp.status == 200:
                        statuses = await resp.json()
                        text = "⚙️ <b>Настройки монеток статусов</b>\n\n"
                        for s in statuses:
                            coins = f"+{s['coins']}" if s['coins'] > 0 else str(s['coins'])
                            text += f"{s['emoji']} {s['name']}: {coins} 💰\n"
                        text += "\n<i>Нажмите для редактирования:</i>"
                        
                        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                        buttons = []
                        row = []
                        for s in statuses:
                            row.append(InlineKeyboardButton(
                                text=f"{s['emoji']} ({s['coins']})",
                                callback_data=f"status_edit:{s.get('id', s.get('code'))}"
                            ))
                            if len(row) == 3:
                                buttons.append(row)
                                row = []
                        if row:
                            buttons.append(row)
                        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="crm_int:back")])
                        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
                        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=kb)
                    else:
                        await callback.answer("❌ Ошибка загрузки")
        except Exception as e:
            logging.error(f"Statuses: {e}")
            await callback.answer("❌ Ошибка")
    
    elif action == "coins":
        await callback.message.edit_text(
            "💰 <b>Настройка монеток</b>\n\n"
            "Монетки начисляются за смену статуса лида.\n\n"
            "Для редактирования используйте API:\n"
            "<code>PATCH /crm/{company_id}/statuses/{status_id}</code>",
            parse_mode='HTML'
        )
        await callback.answer()

@router.callback_query(F.data.startswith("mgr_kpi:"))
async def manager_kpi_callback(callback: types.CallbackQuery):
    """Show manager KPI for admin"""
    user_id = int(callback.data.split(":")[1])
    company_id = getattr(callback.bot, 'company_id', 1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/managers/{user_id}') as resp:
                if resp.status == 200:
                    m = await resp.json()
                    text = f"📊 <b>KPI: {m.get('full_name', '?')}</b>\n\n"
                    text += f"💰 Монетки: {m.get('coins', 0)}\n"
                    text += f"📋 Лидов: {m.get('leads_count', 0)}\n"
                    text += f"✅ Сделок: {m.get('deals_count', 0)}"
                    await callback.message.answer(text, parse_mode='HTML')
                    await callback.answer()
                else:
                    await callback.answer("Ошибка", show_alert=True)
    except Exception as e:
        logging.error(f"KPI error: {e}")
        await callback.answer("Ошибка", show_alert=True)

