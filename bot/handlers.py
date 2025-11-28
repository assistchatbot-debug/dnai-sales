import logging
import aiohttp
import io
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from config import API_BASE_URL
from states import SalesFlow
from keyboards import get_start_keyboard

router = Router()

async def start_session(user_id: int):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f'{API_BASE_URL}/sales/1/chat', json={
                'message': 'start_session',
                'user_id': str(user_id),
                'username': f'user_{user_id}'
            }) as resp:
                return await resp.json()
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
    user_id = str(message.from_user.id)
    username = message.from_user.username or f"user_{user_id}"
    
    status_msg = await message.answer("🎤 Слушаю...")
    
    try:
        # Download voice file
        voice_file = await message.bot.get_file(message.voice.file_id)
        file_data = io.BytesIO()
        await message.bot.download(voice_file, file_data)
        file_data.seek(0)
        
        # Prepare form data
        data = aiohttp.FormData()
        data.add_field('file', file_data, filename='voice.ogg', content_type='audio/ogg')
        data.add_field('session_id', 'voice_session') # Dummy session id
        data.add_field('user_id', user_id)
        data.add_field('username', username)
        
        async with aiohttp.ClientSession() as session:
             async with session.post(f'{API_BASE_URL}/sales/1/voice', data=data) as resp:
                 if resp.status == 200:
                     result = await resp.json()
                     ai_response = result.get('response', '')
                     await status_msg.delete()
                     await process_backend_response(message, ai_response)
                 else:
                     await status_msg.delete()
                     await message.answer("Ошибка обработки голосового сообщения.")
    except Exception as e:
        logging.error(f"Voice error: {e}")
        await status_msg.delete()
        await message.answer("Произошла ошибка при обработке голоса.")

@router.message()
async def handle_text(message: types.Message, state: FSMContext):
    if message.text.startswith('/'):
        return

    user_id = str(message.from_user.id)
    username = message.from_user.username or f"user_{user_id}"
    
    status_msg = await message.answer("⏳ Думаю...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f'{API_BASE_URL}/sales/1/chat', json={
                'message': message.text,
                'user_id': user_id,
                'username': username
            }) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ai_response = data.get('response', '')
                    await status_msg.delete()
                    await process_backend_response(message, ai_response)
                else:
                    await status_msg.delete()
                    await message.answer("Не удалось связаться с сервером.")
        except Exception as e:
            logging.error(f'Backend connection error: {e}')
            await status_msg.delete()
            await message.answer("Ошибка соединения.")
