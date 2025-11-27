from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import SalesFlow
from keyboards import get_start_keyboard, get_recommendation_keyboard
from config import API_BASE_URL, COMPANY_ID
import aiohttp
import logging
import os

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(SalesFlow.qualifying)
    await message.answer("Привет! Я Умный Агент (BizDNAi).\n\n🚀 Я новое поколение корпоративного AI.\n\nЯ помогу подобрать идеальное решение.\nИспользуйте меню, пишите или говорите и я вам отвечу.\n\nДля смены языка используйте /lang", reply_markup=get_start_keyboard())
    
    # Initialize session silently
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        try:
            payload = {
                "message": "start_session", 
                "user_id": str(message.from_user.id),
                "username": message.from_user.username
            }
            async with session.post(f"{API_BASE_URL}/sales/{COMPANY_ID}/chat", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await state.update_data(session_id=data.get("session_id"))
        except Exception as e: logging.error(f"Connection Error: {e}")

@router.message(Command("lang"))
async def cmd_lang(message: types.Message):
    # Simple toggle for now, can be expanded to a menu
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        await message.answer("Для смены языка напишите: 'Switch to English' или 'Переключить на Русский'.")

@router.message(Command("log"))
async def cmd_log(message: types.Message):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        try:
            async with session.get(f"{API_BASE_URL}/logs") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logs = data.get("logs", "No logs")
                    # Split if too long
                    if len(logs) > 4000:
                        logs = logs[-4000:]
                    await message.answer(f"📜 **Backend Logs:**\n\n", parse_mode="Markdown")
                else:
                    await message.answer("Failed to fetch logs.")
        except Exception as e:
            await message.answer(f"Error fetching logs: {e}")

@router.message(F.text == "🚀 Подобрать решение")
async def start_selection(message: types.Message, state: FSMContext):
    await state.set_state(SalesFlow.qualifying)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        try:
            payload = {
                "message": "start_session", 
                "user_id": str(message.from_user.id),
                "username": message.from_user.username
            }
            async with session.post(f"{API_BASE_URL}/sales/{COMPANY_ID}/chat", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await state.update_data(session_id=data.get("session_id"))
        except Exception as e: logging.error(f"Connection Error: {e}")
    await message.answer("Отлично! Расскажите, какая задача стоит перед вами?", reply_markup=types.ReplyKeyboardRemove())

@router.message(SalesFlow.qualifying, F.voice)
async def handle_voice(message: types.Message, state: FSMContext):
    await message.answer("🎧 Слушаю...")
    
    # Get file
    file_id = message.voice.file_id
    file = await message.bot.get_file(file_id)
    file_path = file.file_path
    
    # Download
    file_on_disk = f"{file_id}.ogg"
    await message.bot.download_file(file_path, file_on_disk)
    
    user_data = await state.get_data()
    session_id = user_data.get("session_id")
    
    # Send to API
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        if not session_id:
            await message.answer("Ошибка сессии. Пожалуйста, начните заново с /start")
            return

        data = aiohttp.FormData()
        data.add_field('session_id', str(session_id))
        data.add_field('user_id', str(message.from_user.id))
        if message.from_user.username:
            data.add_field('username', message.from_user.username)
        
        try:
            with open(file_on_disk, 'rb') as f:
                data.add_field('file', f, filename=file_on_disk)
                
                async with session.post(f"{API_BASE_URL}/sales/{COMPANY_ID}/voice", data=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        user_text = result.get("text")
                        ai_response = result.get("response")
                        
                        await message.answer(f"🗣 Вы сказали: \"{user_text}\"")
                        await message.answer(ai_response)
                    else:
                        error_text = await resp.text()
                        logging.error(f"API Error {resp.status}: {error_text}")
                        await message.answer(f"Ошибка обработки голоса сервером: {resp.status}")
        except Exception as e:
            logging.error(f"Voice Error: {e}")
            await message.answer(f"Не удалось отправить голосовое: {e}")
        finally:
            if os.path.exists(file_on_disk):
                os.remove(file_on_disk)

@router.message(SalesFlow.qualifying, F.text)
async def handle_text(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    session_id = user_data.get("session_id")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        try:
            payload = {
                "session_id": session_id, 
                "message": message.text, 
                "user_id": str(message.from_user.id),
                "username": message.from_user.username
            }
            async with session.post(f"{API_BASE_URL}/sales/{COMPANY_ID}/chat", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await message.answer(data.get("response"))
                else: 
                    error_text = await resp.text()
                    logging.error(f"API Error {resp.status}: {error_text}")
                    await message.answer(f"Произошла ошибка при общении с мозгом: {resp.status}")
        except Exception as e:
            logging.error(f"Connection Error: {e}")
            await message.answer(f"Не удалось связаться с сервером: {e}")
