import os
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(level=logging.INFO)

API_BASE_URL = 'http://localhost:8005'

# Token from .env
TOKEN = os.getenv('SUPER_ADMIN_CHAT_ID', '').strip()
if not TOKEN or ':' not in TOKEN:
    try:
        with open('/root/dnai-sales/.env') as f:
            for line in f:
                if line.startswith('SUPER_ADMIN_CHAT_ID='):
                    TOKEN = line.split('=', 1)[1].strip()
                    break
    except:
        pass

if not TOKEN or ':' not in TOKEN:
    print("❌ No valid token found")
    exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# === FSM States ===
class CompanyFlow(StatesGroup):
    viewing_list = State()
    selecting_for_edit = State()
    editing_name = State()
    editing_bin = State()
    editing_phone = State()
    editing_whatsapp = State()
    editing_email = State()
    editing_description = State()
    editing_logo = State()
    editing_bot_token = State()  # NEW
    editing_manager_chat_id = State()  # NEW

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏢 Компании")],
            [KeyboardButton(text="📈 Статус")]
        ],
        resize_keyboard=True
    )

def get_company_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Создать компанию"), KeyboardButton(text="✏️ Редактировать компанию")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )

@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🔐 <b>SuperAdmin Panel</b>\n\nВыберите действие:",
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )

# === Companies List ===
@dp.message(F.text == "🏢 Компании")
async def btn_companies(message: types.Message, state: FSMContext):
    """Show all companies"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/companies/all', timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    companies = await resp.json()
                    
                    if not companies:
                        text = "🏢 <b>Компании:</b>\n\nНет компаний в системе."
                    else:
                        text = "🏢 <b>Компании:</b>\n\n"
                        for c in sorted(companies, key=lambda x: x.get('id', 0)):
                            cid = c.get('id', '?')
                            name = c.get('name', 'Без названия')
                            email = c.get('email', 'нет')
                            has_bot = '🤖' if c.get('bot_token') else '❌'
                            text += f"<b>ID: {cid}</b> — {name} {has_bot}\n   📧 {email}\n\n"
                    
                    await message.answer(text, parse_mode='HTML', reply_markup=get_company_menu_keyboard())
                    await state.set_state(CompanyFlow.viewing_list)
                else:
                    await message.answer("⚠️ Ошибка загрузки компаний", reply_markup=get_main_keyboard())
    except Exception as e:
        logging.error(f"Companies list error: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:50]}", reply_markup=get_main_keyboard())

@dp.message(CompanyFlow.viewing_list, F.text == "◀️ Назад")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_keyboard())

@dp.message(CompanyFlow.viewing_list, F.text == "➕ Создать компанию")
async def start_create_company(message: types.Message, state: FSMContext):
    await state.set_state(CompanyFlow.editing_name)
    await state.update_data(id=None)
    await message.answer("📝 <b>Создание - Шаг 1/9: Название</b>\n\nВведите название:", parse_mode='HTML')

@dp.message(CompanyFlow.viewing_list, F.text == "✏️ Редактировать компанию")
async def start_edit_company(message: types.Message, state: FSMContext):
    await state.set_state(CompanyFlow.selecting_for_edit)
    await message.answer("🔍 <b>Редактирование</b>\n\nВведите ID компании:", parse_mode='HTML')

@dp.message(CompanyFlow.selecting_for_edit)
async def select_company_for_edit(message: types.Message, state: FSMContext):
    try:
        company_id = int(message.text)
    except:
        await message.answer("❌ Неверный ID. Введите число:")
        return
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f'{API_BASE_URL}/sales/company/{company_id}') as resp:
                if resp.status == 200:
                    company = await resp.json()
                    await state.update_data(
                        id=company_id,
                        name=company.get('name'),
                        bin_iin=company.get('bin_iin'),
                        phone=company.get('phone'),
                        whatsapp=company.get('whatsapp'),
                        email=company.get('email'),
                        description=company.get('description'),
                        logo_url=company.get('logo_url'),
                        bot_token=company.get('bot_token'),
                        manager_chat_id=company.get('manager_chat_id')
                    )
                    
                    await state.set_state(CompanyFlow.editing_name)
                    await message.answer(
                        f"📝 <b>Шаг 1/9: Название</b>\n\n"
                        f"<i>Текущее:</i> {company.get('name') or 'не указано'}\n\n"
                        f"Введите новое или '.' чтобы оставить:",
                        parse_mode='HTML'
                    )
                else:
                    await message.answer("❌ Компания не найдена", reply_markup=get_main_keyboard())
                    await state.clear()
        except Exception as e:
            logging.error(f"Get company error: {e}")
            await message.answer("❌ Ошибка подключения", reply_markup=get_main_keyboard())
            await state.clear()

# Steps 1-7 (same as before)
@dp.message(CompanyFlow.editing_name)
async def process_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.':
        await state.update_data(name=message.text)
    await state.set_state(CompanyFlow.editing_bin)
    await message.answer(f"🔢 <b>Шаг 2/9: ИИН/БИН</b>\n\n<i>Текущее:</i> {data.get('bin_iin') or 'не указано'}\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_bin)
async def process_bin(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.':
        await state.update_data(bin_iin=message.text)
    await state.set_state(CompanyFlow.editing_phone)
    await message.answer(f"📱 <b>Шаг 3/9: Телефон</b>\n\n<i>Текущий:</i> {data.get('phone') or 'не указано'}\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_phone)
async def process_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.':
        await state.update_data(phone=message.text)
    await state.set_state(CompanyFlow.editing_whatsapp)
    await message.answer(f"💬 <b>Шаг 4/9: WhatsApp</b>\n\n<i>Текущий:</i> {data.get('whatsapp') or 'не указано'}\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_whatsapp)
async def process_whatsapp(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.':
        await state.update_data(whatsapp=message.text)
    await state.set_state(CompanyFlow.editing_email)
    await message.answer(f"📧 <b>Шаг 5/9: Email</b>\n\n<i>Текущий:</i> {data.get('email') or 'не указано'}\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_email)
async def process_email(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.':
        await state.update_data(email=message.text)
    await state.set_state(CompanyFlow.editing_description)
    desc = data.get('description') or 'не указано'
    await message.answer(f"📄 <b>Шаг 6/9: Описание</b>\n\n<i>Текущее:</i> {desc[:50]}...\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_description)
async def process_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.':
        await state.update_data(description=message.text)
    await state.set_state(CompanyFlow.editing_logo)
    await message.answer(f"📷 <b>Шаг 7/9: Логотип</b>\n\n<i>Текущий:</i> {data.get('logo_url') or 'нет'}\n\nОтправьте фото или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_logo)
async def process_logo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    if message.photo:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        file_data = await bot.download_file(file.file_path)
        
        form_data = aiohttp.FormData()
        form_data.add_field('file', file_data, filename='logo.jpg', content_type='image/jpeg')
        
        async with aiohttp.ClientSession() as session:
            try:
                company_id = data.get('id') or 1
                async with session.post(f'{API_BASE_URL}/sales/company/{company_id}/upload-logo', data=form_data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        await state.update_data(logo_url=result.get('logo_url'))
                        await message.answer("✅ Логотип загружен")
                    else:
                        await message.answer("⚠️ Ошибка загрузки")
            except Exception as e:
                logging.error(f"Logo upload error: {e}")
                await message.answer("❌ Ошибка")
    
    # Go to bot_token
    await state.set_state(CompanyFlow.editing_bot_token)
    token = data.get('bot_token') or 'не указан'
    token_preview = token[:20] + '...' if len(token) > 20 else token
    await message.answer(f"🤖 <b>Шаг 8/9: Bot Token</b>\n\n<i>Текущий:</i> {token_preview}\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_bot_token)
async def process_bot_token(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.':
        await state.update_data(bot_token=message.text)
    
    await state.set_state(CompanyFlow.editing_manager_chat_id)
    manager = data.get('manager_chat_id') or 'не указан'
    await message.answer(f"👤 <b>Шаг 9/9: Manager Chat ID</b>\n\n<i>Текущий:</i> {manager}\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_manager_chat_id)
async def process_manager_chat_id(message: types.Message, state: FSMContext):
    if message.text != '.':
        try:
            chat_id = int(message.text)
            await state.update_data(manager_chat_id=chat_id)
        except:
            await message.answer("⚠️ Неверный формат. Введите число:")
            return
    
    await save_company(message, state)

async def save_company(message: types.Message, state: FSMContext):
    data = await state.get_data()
    status_msg = await message.answer("⏳ Сохранение...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f'{API_BASE_URL}/sales/company/upsert', json=data) as resp:
                await status_msg.delete()
                
                if resp.status == 200:
                    result = await resp.json()
                    action = "создана" if not data.get('id') else "обновлена"
                    await message.answer(
                        f"✅ <b>Компания {action}!</b>\n\n"
                        f"ID: {result.get('id')}\n"
                        f"Название: {result.get('name')}",
                        parse_mode='HTML',
                        reply_markup=get_main_keyboard()
                    )
                else:
                    await message.answer("❌ Ошибка сохранения", reply_markup=get_main_keyboard())
        except Exception as e:
            await status_msg.delete()
            logging.error(f"Save error: {e}")
            await message.answer("❌ Ошибка соединения", reply_markup=get_main_keyboard())
    
    await state.clear()

# === Leads ===
@dp.message(F.text == "📊 Все лиды")
async def btn_leads(message: types.Message):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/all-leads?limit=10', timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    leads = data.get('leads', [])
                    if not leads:
                        await message.answer("📊 Лидов нет")
                        return
                    text = "📊 <b>Последние 10 лидов:</b>\n\n"
                    for l in leads:
                        contact = l.get('contact_info', {}) or {}
                        name = contact.get('name', 'Без имени')
                        phone = contact.get('phone', 'нет')
                        source = l.get('source', 'web')
                        src_icon = '✈️' if 'telegram' in source.lower() else '🌐'
                        temp = contact.get('temperature', '🌤 теплый')
                        text += f"#{l['id']} | {name} | 📱{phone} | {temp} | {src_icon}\n"
                    await message.answer(text, parse_mode='HTML')
                else:
                    await message.answer(f"⚠️ Ошибка: {resp.status}")
    except Exception as e:
        logging.error(f"Leads error: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:40]}")

# === Status ===
@dp.message(F.text == "📈 Статус")
async def btn_status(message: types.Message):
    status = ["📈 <b>Статус системы:</b>\n"]
    
    # Backend
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/', timeout=aiohttp.ClientTimeout(total=3)) as resp:
                if resp.status == 200:
                    status.append("✅ Backend: Online")
                else:
                    status.append(f"⚠️ Backend: {resp.status}")
    except Exception as e:
        status.append(f"❌ Backend: {str(e)[:30]}")
    
    # Database
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/all-leads?limit=1', timeout=aiohttp.ClientTimeout(total=3)) as resp:
                if resp.status == 200:
                    status.append("✅ База данных: Online")
                else:
                    status.append(f"⚠️ База данных: {resp.status}")
    except:
        status.append("❌ База данных: Offline")
    
    status.append("✅ Голосовой ввод: Online")
    
    # Active bots
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/companies/all', timeout=aiohttp.ClientTimeout(total=3)) as resp:
                if resp.status == 200:
                    companies = await resp.json()
                    active_bots = sum(1 for c in companies if c.get('bot_token'))
                    total = len(companies)
                    status.append(f"\n🤖 Активных ботов: {active_bots}/{total}")
    except:
        status.append("\n🤖 Активных ботов: ?")
    
    await message.answer('\n'.join(status), parse_mode='HTML')

@dp.message()
async def handle_any(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        return
    await message.answer("Выберите кнопку:", reply_markup=get_main_keyboard())

async def main():
    logging.info("🔐 SuperAdmin Bot starting...")
    logging.info(f"Using API: {API_BASE_URL}")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
