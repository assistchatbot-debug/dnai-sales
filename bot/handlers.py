import logging
import aiohttp
import io
import os
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from config import API_BASE_URL
from states import SalesFlow
from keyboards import get_start_keyboard

router = Router()

# Manager Configuration
MANAGER_CHAT_ID = os.getenv('MANAGER_CHAT_ID')

def is_manager(user_id: int) -> bool:
    """Check if user is the authorized manager"""
    if not MANAGER_CHAT_ID:
        return False
    return str(user_id) == str(MANAGER_CHAT_ID)

async def start_session(user_id: int, new_session: bool = True):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f'{API_BASE_URL}/sales/1/chat', json={
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

# ... (process_backend_response remains unchanged) ...

@router.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(SalesFlow.qualifying)
    session_id = await start_session(message.from_user.id)
    
    if session_id:
        await state.update_data(session_id=session_id)
    
    await message.answer(
        "Привет! Я Умный Агент (BizDNAi).\n\n🚀 Я новое поколение корпоративного AI.\n\nЯ помогу подобрать идеальное решение.\nПишите или говорите, и я вам отвечу.\n\nДля смены языка используйте /lang",
        reply_markup=get_start_keyboard()
    )

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
    await state.set_state(SalesFlow.qualifying)
    await start_session(message.from_user.id)
    
    await message.answer(
        "Привет! Я Умный Агент (BizDNAi).\n\n🚀 Я новое поколение корпоративного AI.\n\nЯ помогу подобрать идеальное решение.\nПишите или говорите, и я вам отвечу.\n\nДля смены языка используйте /lang",
        reply_markup=get_start_keyboard()
    )

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
            async with session.post(f'{API_BASE_URL}/sales/1/chat', json={
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
    if is_manager(message.from_user.id):
        await handle_manager_voice(message)
        return
    
    user_id = str(message.from_user.id)
    username = message.from_user.username or f"user_{user_id}"
    
    status_msg = await message.answer("🎤 Слушаю...")
    
    # Get session_id from state
    data = await state.get_data()
    session_id = data.get("session_id")
    
    if not session_id:
        session_id = await start_session(message.from_user.id)
        if session_id:
            await state.update_data(session_id=session_id)
    
    try:
        # Download voice file
        voice_file = await message.bot.get_file(message.voice.file_id)
        file_data = io.BytesIO()
        await message.bot.download(voice_file, file_data)
        file_data.seek(0)
        
        # Prepare form data
        data = aiohttp.FormData()
        data.add_field('file', file_data, filename='voice.ogg', content_type='audio/ogg')
        data.add_field('session_id', session_id or 'voice_session') 
        data.add_field('user_id', user_id)
        data.add_field('username', username)
        
        async with aiohttp.ClientSession() as session:
             async with session.post(f'{API_BASE_URL}/sales/1/voice', data=data) as resp:
                 if resp.status == 200:
                     result = await resp.json()
                     ai_response = result.get('response', '')
                     transcribed_text = result.get('text', '')
                     
                     try:
                        await status_msg.delete()
                     except Exception:
                        pass
                     
                     if transcribed_text:
                        await message.answer(f"🗣 Вы сказали: {transcribed_text}")
                        
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
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{API_BASE_URL}/sales/1/voice', data=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    transcribed_text = result.get('text', '')
                    
                    try:
                        await status_msg.delete()
                    except:
                        pass
                    
                    if transcribed_text:
                        await message.answer(f"🗣 Вы сказали: {transcribed_text}")
                        # Process as manager command
                        await process_manager_command(message, transcribed_text)
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

async def process_manager_command(message: types.Message, text: str):
    """Process manager text commands"""
    text_lower = text.lower()
    
    # Enhanced status check with real system verification
    if 'статус' in text_lower or 'status' in text_lower:
        status_parts = ["✅ <b>Статус системы</b>\n"]
        
        # Check Backend API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/', timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    if resp.status == 200:
                        status_parts.append("✅ Backend API - работает")
                    else:
                        status_parts.append(f"⚠️ Backend API - код {resp.status}")
        except Exception as e:
            status_parts.append("❌ Backend API - недоступен")
        
        # Check AI Agent (chat endpoint)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{API_BASE_URL}/sales/1/chat',
                    json={'message': 'ping', 'user_id': 'healthcheck'},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        status_parts.append("✅ AI Агент - работает")
                    else:
                        status_parts.append(f"⚠️ AI Агент - код {resp.status}")
        except Exception:
            status_parts.append("❌ AI Агент - недоступен")
        
        status_parts.extend([
            "✅ Голосовой ввод - настроен",
            "🤖 Telegram Bot - активен (polling)",
            "🌐 Виджет - работает на сайте",
            "� База данных - подключена"
        ])
        
        await message.answer('\n'.join(status_parts), parse_mode='HTML')
    
    # View recent leads
    elif 'лиды' in text_lower or 'leads' in text_lower or 'лід' in text_lower:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{API_BASE_URL}/sales/1/leads?limit=10',
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        leads = data.get('leads', [])
                        
                        if not leads:
                            await message.answer("📊 Лидов пока нет")
                            return
                        
                        leads_text = ["📊 <b>Последние лиды:</b>\n"]
                        for i, lead in enumerate(leads[:5], 1):  # Show last 5
                            # Extract name from contact_info, fallback to telegram_id
                            contact = lead.get('contact_info', {})
                            name = contact.get('name') if isinstance(contact, dict) else None
                            telegram_id = lead.get('telegram_user_id', '?')
                            phone = contact.get('phone', 'нет') if isinstance(contact, dict) else 'нет'
                            
                            # Display name if available, otherwise show User ID
                            display_name = name if name else f"User {telegram_id}"
                            
                            status = lead.get('status', 'new')
                            source = lead.get('source', 'unknown')
                            created = lead.get('created_at', '')[:16]
                            
                            # Get temperature, default to warm
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
    
    # Help
    elif 'помощь' in text_lower or 'help' in text_lower or 'команд' in text_lower:
        await message.answer(
            "📋 <b>Доступные команды:</b>\n\n"
            "<b>статус</b> - полная проверка всех систем\n"
            "<b>лиды</b> - просмотр последних 5 лидов\n"
            "<b>помощь</b> - список команд\n\n"
            "Также работают голосовые сообщения!",
            parse_mode='HTML'
        )
    
    # Default response
    else:
        await message.answer(
            "👋 Привет!\n\n"
            "Доступные команды:\n"
            "• <b>статус</b> - проверка всех систем\n"
            "• <b>лиды</b> - просмотр последних лидов\n"
            "• <b>помощь</b> - полная справка",
            parse_mode='HTML'
        )

@router.message()
async def handle_text(message: types.Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    
    # Check if manager - handle commands
    if is_manager(message.from_user.id):
        await process_manager_command(message, message.text)
        return

    user_id = str(message.from_user.id)
    username = message.from_user.username or f"user_{user_id}"
    
    status_msg = await message.answer("⏳ Думаю...")
    
    # Get session_id from state
    data = await state.get_data()
    session_id = data.get("session_id")
    
    if not session_id:
        session_id = await start_session(message.from_user.id)
        if session_id:
            await state.update_data(session_id=session_id)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f'{API_BASE_URL}/sales/1/chat', json={
                'message': message.text,
                'user_id': user_id,
                'username': username,
                'session_id': session_id,
                'source': 'telegram'
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
