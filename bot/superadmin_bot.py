import os
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import subprocess

logging.basicConfig(level=logging.INFO)
API_BASE_URL = 'http://localhost:8005'

TOKEN = os.getenv('SUPER_ADMIN_CHAT_ID', '').strip()
if not TOKEN or ':' not in TOKEN:
    try:
        with open('/root/dnai-sales/.env') as f:
            for line in f:
                if line.startswith('SUPER_ADMIN_CHAT_ID='):
                    TOKEN = line.split('=', 1)[1].strip()
                    break
    except: pass

if not TOKEN or ':' not in TOKEN:
    print("❌ No valid token found")
    exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()

class CompanyFlow(StatesGroup):
    viewing_list = State()
    selecting_for_edit = State()
    selecting_for_web_avatar = State()
    entering_company_avatar_limit = State()
    editing_name = State()
    editing_bin = State()
    editing_phone = State()
    editing_whatsapp = State()
    editing_email = State()
    editing_description = State()
    editing_logo = State()
    editing_bot_token = State()
    editing_manager_chat_id = State()
    editing_ai_endpoint = State()
    editing_ai_api_key = State()
    selecting_company_for_tier = State()
    selecting_tier = State()
    entering_tier_days = State()
    selecting_company_for_extend = State()
    entering_extend_days = State()
    # Integration states
    editing_integration_type = State()
    editing_onec_url = State()
    editing_onec_user = State()
    editing_onec_pass = State()
    editing_bitrix_webhook = State()
    editing_kommo_subdomain = State()
    editing_kommo_client_id = State()
    editing_kommo_client_secret = State()
    editing_kommo_refresh_token = State()

def get_main_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📊 Компании"), KeyboardButton(text="📈 Лиды")],[KeyboardButton(text="💳 Тарифы"), KeyboardButton(text="⚙️ Статус")],[KeyboardButton(text="🌐 Виджет"), KeyboardButton(text="🔌 Интеграции")],[KeyboardButton(text="🏠 Меню")]], resize_keyboard=True)

def get_company_menu_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="➕ Создать компанию"), KeyboardButton(text="✏️ Редактировать компанию")],[KeyboardButton(text="📋 Список компаний"), KeyboardButton(text="🎭 Web Avatar")],[KeyboardButton(text="🎯 Установить тариф"), KeyboardButton(text="⏰ Продлить тариф")],[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)

def get_temp_icon(temp):
    t = str(temp).lower()
    if 'hot' in t or 'горяч' in t or '🔥' in t:
        return '🔥'
    elif 'warm' in t or 'тепл' in t or '🌤' in t:
        return '🌤'
    else:
        return '❄️'

@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔐 <b>SuperAdmin Panel</b>\n\nВыберите действие:", parse_mode='HTML', reply_markup=get_main_keyboard())

@dp.message(F.text == "◀️ Назад")
async def btn_back_global(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_keyboard())

@dp.message(F.text == "📋 Список компаний")
async def btn_list_companies(message: types.Message, state: FSMContext):
    await state.clear()
    await btn_companies(message, state)


class TierEdit(StatesGroup):
    waiting_price = State()
    waiting_leads = State()
    waiting_avatar_limit = State()
    waiting_ai_price = State()

@dp.message(F.text == "💳 Тарифы")
async def btn_tiers(message: types.Message, state: FSMContext):
    await state.clear()
    try:
        async with aiohttp.ClientSession() as session:
            # Тарифы подписки
            async with session.get(f'{API_BASE_URL}/sales/tiers') as resp:
                tiers = await resp.json() if resp.status == 200 else []
            # Пакеты AI
            async with session.get(f'{API_BASE_URL}/sales/ai-packages') as resp:
                packages = await resp.json() if resp.status == 200 else []
            
            lines = ["💳 <b>Месячные тарифы</b>", ""]
            buttons = []
            for t in tiers:
                avatar_limit = t.get('avatar_limit', 0)
                lines.append(f"<b>{t['name_ru']}</b> — ${t['price_usd']}/мес | {t['leads_limit']} лидов | 🎭{avatar_limit}")
                buttons.append([
                    InlineKeyboardButton(text=f"💰 {t['tier']}", callback_data=f"tierprice_{t['tier']}"),
                    InlineKeyboardButton(text=f"👥 {t['tier']}", callback_data=f"tierleads_{t['tier']}"),
                    InlineKeyboardButton(text=f"🎭 {t['tier']}", callback_data=f"tieravatar_{t['tier']}")
                ])
            
            lines.append("")
            lines.append("🤖 <b>Пакеты AI (разово)</b>")
            lines.append("")
            for p in packages:
                lines.append(f"<b>{p['name_ru']}</b> — ${p['price_usd']}")
                buttons.append([
                    InlineKeyboardButton(text=f"🤖 {p['package']}", callback_data=f"aiprice_{p['package']}")
                ])
            
            lines.append("")
            lines.append("<i>💰 цена, 👥 лиды, 🎭 аватары, 🤖 AI пакеты</i>")
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
            await message.answer("\n".join(lines), parse_mode='HTML', reply_markup=kb)
    except Exception as e:
        await message.answer(f"❌ {str(e)[:50]}")

@dp.callback_query(F.data.startswith("tierprice_"))
async def cb_price(callback: types.CallbackQuery, state: FSMContext):
    tier = callback.data.replace("tierprice_", "")
    await state.update_data(tier=tier)
    await state.set_state(TierEdit.waiting_price)
    await callback.message.answer(f"💰 Введите новую цену для {tier.upper()} (число):")
    await callback.answer()

@dp.callback_query(F.data.startswith("tierleads_"))
async def cb_leads(callback: types.CallbackQuery, state: FSMContext):
    tier = callback.data.replace("tierleads_", "")
    await state.update_data(tier=tier)
    await state.set_state(TierEdit.waiting_leads)
    await callback.message.answer(f"👥 Введите лимит лидов для {tier.upper()} (число):")
    await callback.answer()


@dp.callback_query(F.data.startswith("tieravatar_"))
async def cb_avatar(callback: types.CallbackQuery, state: FSMContext):
    tier = callback.data.replace("tieravatar_", "")
    await state.update_data(tier=tier)
    await state.set_state(TierEdit.waiting_avatar_limit)
    await callback.message.answer(f"🎭 Введите лимит аватаров для {tier.upper()} (число):")
    await callback.answer()


@dp.callback_query(F.data.startswith("aiprice_"))
async def cb_aiprice(callback: types.CallbackQuery, state: FSMContext):
    pkg = callback.data.replace("aiprice_", "")
    await state.update_data(pkg=pkg)
    await state.set_state(TierEdit.waiting_ai_price)
    await callback.message.answer(f"🤖 Введите новую цену для {pkg.upper()} (число):")
    await callback.answer()

@dp.message(TierEdit.waiting_price)
async def proc_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text.strip())
        data = await state.get_data()
        async with aiohttp.ClientSession() as session:
            await session.patch(f'{API_BASE_URL}/sales/tiers/{data["tier"]}', json={'price_usd': price})
        await message.answer(f"✅ Цена {data['tier'].upper()} = ${price}/мес", reply_markup=get_main_keyboard())
    except:
        await message.answer("❌ Введите число")
        return
    await state.clear()

@dp.message(TierEdit.waiting_leads)
async def proc_leads(message: types.Message, state: FSMContext):
    try:
        limit = int(message.text.strip())
        data = await state.get_data()
        async with aiohttp.ClientSession() as session:
            await session.patch(f'{API_BASE_URL}/sales/tiers/{data["tier"]}', json={'leads_limit': limit})
        await message.answer(f"✅ Лимит {data['tier'].upper()} = {limit}/мес", reply_markup=get_main_keyboard())
    except:
        await message.answer("❌ Введите число")
        return
    await state.clear()


@dp.message(TierEdit.waiting_avatar_limit)
async def proc_avatar_limit(message: types.Message, state: FSMContext):
    try:
        limit = int(message.text.strip())
        data = await state.get_data()
        async with aiohttp.ClientSession() as session:
            await session.patch(f'{API_BASE_URL}/sales/tiers/{data["tier"]}', json={'avatar_limit': limit})
        await message.answer(f"✅ Аватаров {data['tier'].upper()} = {limit}", reply_markup=get_main_keyboard())
    except:
        await message.answer("❌ Введите число")
        return
    await state.clear()


@dp.message(TierEdit.waiting_ai_price)
async def proc_ai_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text.strip())
        data = await state.get_data()
        async with aiohttp.ClientSession() as session:
            await session.patch(f'{API_BASE_URL}/sales/ai-packages/{data["pkg"]}', json={'price_usd': price})
        await message.answer(f"✅ AI пакет {data['pkg'].upper()} = ${price}", reply_markup=get_main_keyboard())
    except:
        await message.answer("❌ Введите число")
        return
    await state.clear()


@dp.message(F.text == "🌐 Виджет")
async def btn_widget(message: types.Message, state: FSMContext):
    """Send widget embed code"""
    await state.clear()
    
    # Экранированный код для HTML
    embed_code = '&lt;script src="https://bizdnai.com/widget-source/bizdnaii-widget.js"&gt;&lt;/script&gt;'
    
    text = f"""🌐 <b>Код для вставки виджета</b>

Скопируйте этот код и вставьте на любую страницу сайта перед закрывающим тегом &lt;/body&gt;:

<code>{embed_code}</code>

✅ Виджет автоматически появится в правом нижнем углу страницы."""
    
    await message.answer(text, parse_mode='HTML', reply_markup=get_main_keyboard())

@dp.message(F.text == "📊 Компании")
async def btn_companies(message: types.Message, state: FSMContext):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/companies/all', timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    companies = await resp.json()
                    if not companies:
                        text = "🏢 <b>Компании:</b>\n\nНет компаний."
                    else:
                        text = "🏢 <b>Компании:</b>\n\n"
                        for c in sorted(companies, key=lambda x: x.get('id', 0)):
                            cid = c.get('id', '?')
                            name = c.get('name', 'Без названия')
                            has_bot = '🤖' if c.get('bot_token') else '❌'
                            tier = c.get('tier', 'free')
                            tier_icon = '💎' if tier != 'free' else '🆓'
                            web_avatar = '🎭' if c.get('web_avatar_enabled') else ''
                            text += f"<b>ID: {cid}</b> — {name} {has_bot} {tier_icon}{tier} {web_avatar}\n"
                    await message.answer(text, parse_mode='HTML', reply_markup=get_company_menu_keyboard())
                    await state.set_state(CompanyFlow.viewing_list)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)[:50]}", reply_markup=get_main_keyboard())

@dp.message(CompanyFlow.viewing_list, F.text == "➕ Создать компанию")
async def start_create_company(message: types.Message, state: FSMContext):
    await state.set_state(CompanyFlow.editing_name)
    await state.update_data(id=None)
    await message.answer("📝 <b>Создание - Шаг 1/11: Название</b>\n\nВведите название:", parse_mode='HTML')

@dp.message(CompanyFlow.viewing_list, F.text == "✏️ Редактировать компанию")
async def start_edit_company(message: types.Message, state: FSMContext):
    await state.set_state(IntegrationFlow.selecting_company)
    await message.answer("🔍 <b>Редактирование</b>\n\nВведите ID компании:", parse_mode='HTML')

@dp.message(CompanyFlow.selecting_for_edit)
async def select_company_for_edit(message: types.Message, state: FSMContext):
    try:
        company_id = int(message.text)
    except:
        await message.answer("❌ Неверный ID")
        return
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f'{API_BASE_URL}/sales/companies/all') as resp:
                if resp.status == 200:
                    companies = await resp.json()
                    company = next((c for c in companies if c['id'] == company_id), None)
                    if not company:
                        await message.answer("❌ Не найдена", reply_markup=get_main_keyboard())
                        await state.clear()
                        return
                    await state.update_data(id=company_id, name=company.get('name'), bin_iin=company.get('bin_iin'), phone=company.get('phone'), whatsapp=company.get('whatsapp'), email=company.get('email'), description=company.get('description'), logo_url=company.get('logo_url'), bot_token=company.get('bot_token'), manager_chat_id=company.get('manager_chat_id'), ai_endpoint=company.get('ai_endpoint'), ai_api_key=company.get('ai_api_key'))
                    await state.set_state(CompanyFlow.editing_name)
                    await message.answer(f"📝 <b>Шаг 1/11: Название</b>\n\n<i>Текущее:</i> {company.get('name') or 'нет'}\n\nВведите новое или '.':", parse_mode='HTML')
        except:
            await message.answer("❌ Ошибка", reply_markup=get_main_keyboard())
            await state.clear()

@dp.message(CompanyFlow.editing_name)
async def process_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.': await state.update_data(name=message.text)
    await state.set_state(CompanyFlow.editing_bin)
    await message.answer(f"🔢 <b>Шаг 2/11: ИИН/БИН</b>\n\n<i>Текущее:</i> {data.get('bin_iin') or 'нет'}\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_bin)
async def process_bin(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.': await state.update_data(bin_iin=message.text)
    await state.set_state(CompanyFlow.editing_phone)
    await message.answer(f"📱 <b>Шаг 3/11: Телефон</b>\n\n<i>Текущий:</i> {data.get('phone') or 'нет'}\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_phone)
async def process_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.': await state.update_data(phone=message.text)
    await state.set_state(CompanyFlow.editing_whatsapp)
    await message.answer(f"💬 <b>Шаг 4/11: WhatsApp</b>\n\n<i>Текущий:</i> {data.get('whatsapp') or 'нет'}\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_whatsapp)
async def process_whatsapp(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.': await state.update_data(whatsapp=message.text)
    await state.set_state(CompanyFlow.editing_email)
    await message.answer(f"📧 <b>Шаг 5/11: Email</b>\n\n<i>Текущий:</i> {data.get('email') or 'нет'}\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_email)
async def process_email(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.': await state.update_data(email=message.text)
    await state.set_state(CompanyFlow.editing_description)
    await message.answer(f"📄 <b>Шаг 6/11: Описание</b>\n\n<i>Текущее:</i> {(data.get('description') or 'нет')[:50]}...\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_description)
async def process_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.': await state.update_data(description=message.text)
    await state.set_state(CompanyFlow.editing_logo)
    await message.answer(f"📷 <b>Шаг 7/11: Логотип</b>\n\nОтправьте фото/документ или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_logo)
async def process_logo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.photo or message.document:
        try:
            if message.photo:
                file = await bot.get_file(message.photo[-1].file_id)
                file_data = await bot.download_file(file.file_path)
                ext, ct = 'jpg', 'image/jpeg'
            else:
                file = await bot.get_file(message.document.file_id)
                file_data = await bot.download_file(file.file_path)
                ext, ct = 'png', 'image/png'
            form_data = aiohttp.FormData()
            form_data.add_field('file', file_data, filename=f'logo.{ext}', content_type=ct)
            async with aiohttp.ClientSession() as session:
                async with session.post(f'{API_BASE_URL}/sales/company/{data.get("id") or 1}/upload-logo', data=form_data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        await state.update_data(logo_url=result.get('logo_url'))
                        await message.answer("✅ Загружен")
        except: pass
    await state.set_state(CompanyFlow.editing_bot_token)
    token = data.get('bot_token') or 'нет'
    await message.answer(f"🤖 <b>Шаг 8/11: Bot Token</b>\n\n<i>Текущий:</i> {token[:20]}...\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_bot_token)
async def process_bot_token(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.': await state.update_data(bot_token=message.text)
    await state.set_state(CompanyFlow.editing_manager_chat_id)
    await message.answer(f"👤 <b>Шаг 9/11: Manager Chat ID</b>\n\n<i>Текущий:</i> {data.get('manager_chat_id') or 'нет'}\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_manager_chat_id)
async def process_manager_chat_id(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.':
        try: await state.update_data(manager_chat_id=int(message.text))
        except:
            await message.answer("⚠️ Неверный формат")
            return
    await state.set_state(CompanyFlow.editing_ai_endpoint)
    await message.answer(f"🤖 <b>Шаг 10/11: AI Endpoint</b>\n\n<i>Текущий:</i> {data.get('ai_endpoint') or 'нет'}\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_ai_endpoint)
async def process_ai_endpoint(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text != '.': await state.update_data(ai_endpoint=message.text)
    await state.set_state(CompanyFlow.editing_ai_api_key)
    api_key = data.get('ai_api_key') or 'нет'
    await message.answer(f"🔑 <b>Шаг 11/11: AI API Key</b>\n\n<i>Текущий:</i> {api_key[:20]}...\n\nВведите или '.':", parse_mode='HTML')

@dp.message(CompanyFlow.editing_ai_api_key)
async def process_ai_api_key(message: types.Message, state: FSMContext):
    if message.text != '.': await state.update_data(ai_api_key=message.text)
    data = await state.get_data()
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f'{API_BASE_URL}/sales/company/upsert', json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    await message.answer(f"✅ <b>Сохранено!</b>\n\nID: {result.get('id')}\nНазвание: {result.get('name')}", parse_mode='HTML', reply_markup=get_main_keyboard())
                    
                    # Auto-restart Manager bot to load new company
                    try:
                        restart_result = subprocess.run(
                            ['docker-compose', '-f', '/root/dnai-sales/docker-compose.yml', 'restart', 'bot'],
                            cwd='/root/dnai-sales',
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        if restart_result.returncode == 0:
                            await message.answer("🔄 Manager бот перезапущен. Компания активирована!")
                        else:
                            await message.answer(f"⚠️ Не удалось перезапустить Manager бот:\n{restart_result.stderr[:100]}")
                    except Exception as restart_error:
                        await message.answer(f"❌ Ошибка перезапуска: {str(restart_error)[:100]}")
                else:
                    await message.answer("❌ Ошибка", reply_markup=get_main_keyboard())
        except:
            await message.answer("❌ Ошибка соединения", reply_markup=get_main_keyboard())
    await state.clear()

@dp.message(F.text == "📈 Лиды")
async def btn_leads(message: types.Message):
    try:
        async with aiohttp.ClientSession() as session:
            companies = {}
            try:
                async with session.get(f'{API_BASE_URL}/sales/companies/all', timeout=aiohttp.ClientTimeout(total=3)) as cr:
                    if cr.status == 200:
                        for c in await cr.json():
                            companies[c['id']] = c['name']
            except: pass
            
            async with session.get(f'{API_BASE_URL}/sales/all-leads?limit=15', timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    leads = data.get('leads', [])
                    if not leads:
                        await message.answer("📊 Лидов нет")
                        return
                    text = "📊 <b>Последние лиды:</b>\n\n"
                    for l in leads:
                        contact = l.get('contact_info', {}) or {}
                        phone = contact.get('phone') or '-'
                        name = contact.get('name') or contact.get('username') or ''
                        company_id = l.get('company_id', 0)
                        company_name = companies.get(company_id, f'#{company_id}')
                        temp_icon = get_temp_icon(l.get('temperature', 'warm'))
                        src = '✈️' if 'telegram' in l.get('source', '').lower() else '🌐'
                        if name:
                            text += f"{src} <b>{company_name}</b> | {name} | 📱{phone} {temp_icon}\n"
                        else:
                            text += f"{src} <b>{company_name}</b> | 📱{phone} {temp_icon}\n"
                    await message.answer(text, parse_mode='HTML')
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)[:40]}")

@dp.message(F.text == "⚙️ Статус")
async def btn_status(message: types.Message):
    status = ["📈 <b>Статус системы:</b>\n"]
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/', timeout=aiohttp.ClientTimeout(total=3)) as resp:
                status.append("✅ Backend API: Online" if resp.status == 200 else f"⚠️ Backend: {resp.status}")
    except: status.append("❌ Backend API: Offline")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/docs', timeout=aiohttp.ClientTimeout(total=3)) as resp:
                status.append("✅ FastAPI Docs: Online" if resp.status == 200 else f"⚠️ FastAPI: {resp.status}")
    except: status.append("❌ FastAPI: Offline")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/all-leads?limit=1', timeout=aiohttp.ClientTimeout(total=3)) as resp:
                status.append("✅ PostgreSQL: Online" if resp.status == 200 else f"⚠️ PostgreSQL: {resp.status}")
    except: status.append("❌ PostgreSQL: Offline")
    
    status.append("✅ Whisper (голос): Ready")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/companies/all', timeout=aiohttp.ClientTimeout(total=3)) as resp:
                if resp.status == 200:
                    companies = await resp.json()
                    active = sum(1 for c in companies if c.get('bot_token'))
                    status.append(f"\n🏢 Компаний: {len(companies)}")
                    status.append(f"🤖 С ботами: {active}")
                    # Tier breakdown
                    tiers = {}
                    for c in companies:
                        t = c.get('tier', 'free')
                        tiers[t] = tiers.get(t, 0) + 1
                    tier_str = ', '.join([f"{k}: {v}" for k, v in sorted(tiers.items())])
                    status.append(f"💎 Тарифы: {tier_str}")
    except: pass
    
    await message.answer('\n'.join(status), parse_mode='HTML')

@dp.message(F.text == "🎭 Web Avatar")
async def start_web_avatar(message: types.Message, state: FSMContext):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/companies/all', timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    companies = await resp.json()
                    if not companies:
                        await message.answer("📋 Нет компаний")
                        return
                    text = "🎭 <b>Web Avatar</b>\n\nВыберите компанию:\n\n"
                    for i, c in enumerate(companies, 1):
                        enabled = '✅' if c.get('web_avatar_enabled') else '❌'
                        text += f"{i}. {c['name']} — {enabled}\n"
                    await state.update_data(companies=companies)
                    await state.set_state(CompanyFlow.selecting_for_web_avatar)
                    await message.answer(text, parse_mode='HTML')
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)[:40]}")

@dp.message(CompanyFlow.selecting_for_web_avatar)
async def select_web_avatar(message: types.Message, state: FSMContext):
    try:
        num = int(message.text.strip()) - 1
        data = await state.get_data()
        companies = data.get('companies', [])
        if 0 <= num < len(companies):
            company = companies[num]
            current_status = company.get('web_avatar_enabled', False)
            tier = company.get('tier', 'free')
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/sales/tiers') as resp:
                    tiers = await resp.json() if resp.status == 200 else []
            
            tier_limit = next((t.get('avatar_limit', 0) for t in tiers if t.get('tier') == tier), 0)
            override_limit = company.get('avatar_limit')
            current_limit = override_limit if override_limit is not None else tier_limit
            
            status_text = '✅ Включён' if current_status else '❌ Выключен'
            btn_text = '❌ Выключить' if current_status else '✅ Включить'
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=btn_text, callback_data=f"toggle_avatar_{company['id']}")]
            ])
            
            await state.update_data(company_id=company['id'], company_name=company['name'])
            await message.answer(
                f"🎭 <b>Web Avatar для {company['name']}</b>\n\n"
                f"Статус: {status_text}\n"
                f"Тариф: {tier} (лимит по тарифу: {tier_limit})\n"
                f"Текущий лимит: {current_limit}\n\n"
                f"Введите новый лимит (число) или '.' для пропуска:",
                reply_markup=kb, parse_mode='HTML'
            )
            await state.set_state(CompanyFlow.entering_company_avatar_limit)
        else:
            await message.answer("❌ Неверный номер")
            await state.clear()
    except ValueError:
        await message.answer("❌ Введите номер")
        await state.clear()

@dp.message(CompanyFlow.entering_company_avatar_limit)
async def enter_company_avatar_limit(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text.strip() != '.':
        try:
            limit = int(message.text.strip())
            async with aiohttp.ClientSession() as session:
                await session.post(f'{API_BASE_URL}/sales/company/upsert', json={'id': data['company_id'], 'avatar_limit': limit})
            await message.answer(f"✅ Лимит аватаров для {data['company_name']} = {limit}", reply_markup=get_company_menu_keyboard())
        except ValueError:
            await message.answer("❌ Введите число или '.'")
            return
    else:
        await message.answer("✅ Лимит не изменён", reply_markup=get_company_menu_keyboard())
    await state.clear()


@dp.callback_query(lambda c: c.data.startswith('toggle_avatar_'))
async def toggle_avatar_callback(callback: types.CallbackQuery):
    company_id = int(callback.data.split('_')[2])
    async with aiohttp.ClientSession() as session:
        # Получаем текущий статус
        async with session.get(f'{API_BASE_URL}/sales/companies/all') as resp:
            companies = await resp.json()
            company = next((c for c in companies if c['id'] == company_id), None)
            if company:
                new_status = not company.get('web_avatar_enabled', False)
                # Обновляем
                await session.post(f'{API_BASE_URL}/sales/company/upsert', 
                                  json={'id': company_id, 'web_avatar_enabled': new_status})
                status_text = '✅ Включён' if new_status else '❌ Выключен'
                await callback.answer(f"Web Avatar: {status_text}")
                await callback.message.edit_text(
                    f"🎭 Web Avatar для {company['name']}: {status_text}\n\nВведите лимит или '.' для пропуска:"
                )

@dp.message(F.text == "🎯 Установить тариф")
async def start_set_tier(message: types.Message, state: FSMContext):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/companies/all', timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    companies = await resp.json()
                    if not companies:
                        await message.answer("📋 Нет компаний")
                        return
                    text = "🎯 <b>Установить тариф</b>\n\nВыберите компанию:\n\n"
                    for i, c in enumerate(companies, 1):
                        tier = c.get('tier', 'free')
                        expiry = c.get('tier_expiry')
                        if expiry and expiry != 'None': expiry = str(expiry)[:10]
                        else: expiry = '∞' if tier == 'free' else 'N/A'
                        text += f"{i}. {c['name']} — {tier} (до: {expiry})\n"
                    await state.update_data(companies=companies)
                    await state.set_state(CompanyFlow.selecting_company_for_tier)
                    await message.answer(text, parse_mode='HTML')
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)[:40]}")

@dp.message(CompanyFlow.selecting_company_for_tier)
async def select_company_for_tier(message: types.Message, state: FSMContext):
    try:
        num = int(message.text.strip()) - 1
        data = await state.get_data()
        companies = data.get('companies', [])
        if 0 <= num < len(companies):
            company = companies[num]
            await state.update_data(selected_company=company)
            await state.set_state(IntegrationFlow.editing_settings)
            kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="free"), KeyboardButton(text="basic")],[KeyboardButton(text="pro"), KeyboardButton(text="enterprise")],[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)
            await state.set_state(CompanyFlow.selecting_tier)
            await message.answer(f"🎯 Компания: <b>{company['name']}</b>\n\nВыберите тариф:", parse_mode='HTML', reply_markup=kb)
        else:
            await message.answer("❌ Неверный номер")
    except ValueError:
        await message.answer("❌ Введите номер")

@dp.message(CompanyFlow.selecting_tier)
async def select_tier(message: types.Message, state: FSMContext):
    tier = message.text.strip().lower()
    if tier not in ['free', 'basic', 'pro', 'enterprise']:
        await message.answer("❌ Выберите тариф")
        return
    await state.update_data(new_tier=tier)
    await state.set_state(CompanyFlow.entering_tier_days)
    await message.answer(f"📅 Тариф: <b>{tier}</b>\n\nВведите дней:", parse_mode='HTML', reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="7"), KeyboardButton(text="14"), KeyboardButton(text="30")],[KeyboardButton(text="90"), KeyboardButton(text="180"), KeyboardButton(text="365")]], resize_keyboard=True))

@dp.message(CompanyFlow.entering_tier_days)
async def enter_tier_days(message: types.Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if days <= 0 or days > 3650:
            await message.answer("❌ От 1 до 3650")
            return
        data = await state.get_data()
        company = data.get('selected_company', {})
        tier = data.get('new_tier', 'free')
        from datetime import datetime, timedelta
        expiry = (datetime.now() + timedelta(days=days)).isoformat()
        async with aiohttp.ClientSession() as session:
            async with session.patch(f"{API_BASE_URL}/sales/companies/{company['id']}/tier", json={'tier': tier, 'tier_expiry': expiry}, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    await message.answer(f"✅ Установлен!\n\n🏢 {company['name']}\n🎯 {tier}\n📅 {days} дней\n⏰ До: {expiry[:10]}", reply_markup=get_company_menu_keyboard())
                else:
                    await message.answer(f"⚠️ Ошибка: {resp.status}")
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число")
    except Exception as e:
        await message.answer(f"❌ {str(e)[:40]}")
        await state.clear()

@dp.message(F.text == "⏰ Продлить тариф")
async def start_extend_tier(message: types.Message, state: FSMContext):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/companies/all', timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    companies = await resp.json()
                    companies_with_tier = [c for c in companies if c.get('tier', 'free') != 'free']
                    if not companies_with_tier:
                        await message.answer("📋 Нет компаний с платным тарифом", reply_markup=get_company_menu_keyboard())
                        return
                    text = "⏰ <b>Продлить тариф</b>\n\n"
                    for i, c in enumerate(companies_with_tier, 1):
                        expiry = c.get('tier_expiry')
                        if expiry and expiry != 'None': expiry = str(expiry)[:10]
                        else: expiry = 'N/A'
                        text += f"{i}. {c['name']} — {c.get('tier')} (до: {expiry})\n"
                    await state.update_data(companies=companies_with_tier)
                    await state.set_state(CompanyFlow.selecting_company_for_extend)
                    await message.answer(text, parse_mode='HTML')
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)[:40]}")

@dp.message(CompanyFlow.selecting_company_for_extend)
async def select_company_for_extend(message: types.Message, state: FSMContext):
    try:
        num = int(message.text.strip()) - 1
        data = await state.get_data()
        companies = data.get('companies', [])
        if 0 <= num < len(companies):
            company = companies[num]
            await state.update_data(selected_company=company)
            await state.set_state(IntegrationFlow.editing_settings)
            await state.set_state(CompanyFlow.entering_extend_days)
            await message.answer(f"⏰ Продление: <b>{company['name']}</b>\n\nВведите дней:", parse_mode='HTML', reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="7"), KeyboardButton(text="14"), KeyboardButton(text="30")],[KeyboardButton(text="90"), KeyboardButton(text="180"), KeyboardButton(text="365")]], resize_keyboard=True))
    except ValueError:
        await message.answer("❌ Введите номер")

@dp.message(CompanyFlow.entering_extend_days)
async def enter_extend_days(message: types.Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if days <= 0 or days > 3650:
            await message.answer("❌ От 1 до 3650")
            return
        data = await state.get_data()
        company = data.get('selected_company', {})
        from datetime import datetime, timedelta
        current_expiry = company.get('tier_expiry')
        base = datetime.now()
        if current_expiry and current_expiry != 'None':
            try:
                base = datetime.fromisoformat(str(current_expiry).replace('Z', '+00:00'))
                if base.replace(tzinfo=None) < datetime.now(): base = datetime.now()
            except: pass
        new_expiry = (base + timedelta(days=days)).isoformat()
        async with aiohttp.ClientSession() as session:
            async with session.patch(f"{API_BASE_URL}/sales/companies/{company['id']}/tier", json={'tier_expiry': new_expiry}, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    await message.answer(f"✅ Продлён!\n\n🏢 {company['name']}\n➕ {days} дней\n⏰ До: {new_expiry[:10]}", reply_markup=get_company_menu_keyboard())
                else:
                    await message.answer(f"⚠️ Ошибка: {resp.status}")
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число")
    except Exception as e:
        await message.answer(f"❌ {str(e)[:40]}")
        await state.clear()


@dp.message(F.text == "🔌 Интеграции")
async def btn_integrations(message: types.Message, state: FSMContext):
    """Manage integrations"""
    await state.clear()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/companies/all') as resp:
                if resp.status == 200:
                    companies = await resp.json()
                    if not companies:
                        await message.answer("📋 Нет компаний")
                        return
                    text = "🔌 <b>Интеграции 1С-CRM</b>\n\nВыберите компанию:\n\n"
                    for i, c in enumerate(companies, 1):
                        enabled = '✅' if c.get('integration_enabled') else '❌'
                        itype = c.get('integration_type') or 'нет'
                        text += f"{i}. {c['name']} — {enabled} {itype}\n"
                    await state.update_data(companies=companies)
                    await state.set_state(IntegrationFlow.selecting_company)
                    await message.answer(text, parse_mode='HTML')
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)[:40]}")


class IntegrationFlow(StatesGroup):
    selecting_company = State()
    editing_type = State()
    editing_settings = State()
    editing_onec_url = State()
    editing_onec_username = State()
    editing_onec_password = State()
    editing_bitrix_webhook = State()
    editing_kommo_subdomain = State()
    editing_kommo_client_id = State()
    editing_kommo_client_secret = State()
    editing_kommo_refresh_token = State()

@dp.message(IntegrationFlow.selecting_company)
async def select_integration_company(message: types.Message, state: FSMContext):
    """Выбор компании для настройки интеграции"""
    try:
        num = int(message.text.strip()) - 1
        data = await state.get_data()
        companies = data.get('companies', [])
        if 0 <= num < len(companies):
            company = companies[num]
            
            # Показываем текущие настройки
            enabled = '✅ Включена' if company.get('integration_enabled') else '❌ Выключена'
            itype = company.get('integration_type') or 'не выбран'
            
            text = f"🔌 <b>Интеграция: {company['name']}</b>\n\n"
            text += f"Статус: {enabled}\n"
            text += f"Тип CRM: {itype}\n\n"
            
            if company.get('onec_base_url'):
                text += f"1С: {company['onec_base_url'][:50]}...\n"
            if company.get('bitrix24_webhook_url'):
                text += f"Bitrix24: {company['bitrix24_webhook_url'][:50]}...\n"
            if company.get('kommo_subdomain'):
                text += f"KOMMO: {company['kommo_subdomain']}\n"
            
            # Кнопки управления
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="❌ Выключить" if company.get('integration_enabled') else "✅ Включить",
                    callback_data=f"toggle_int_{company['id']}"
                )],
                [InlineKeyboardButton(text="⚙️ Настроить", callback_data=f"setup_int_{company['id']}")]
            ])
            
            await state.update_data(selected_company=company)
            await state.set_state(IntegrationFlow.editing_settings)
            await message.answer(text, parse_mode='HTML', reply_markup=kb)
        else:
            await message.answer("❌ Неверный номер")
    except ValueError:
        await message.answer("❌ Введите номер")

@dp.callback_query(lambda c: c.data.startswith('toggle_int_'))
async def toggle_integration(callback: types.CallbackQuery):
    """Включить/выключить интеграцию"""
    company_id = int(callback.data.split('_')[2])
    async with aiohttp.ClientSession() as session:
        try:
            # Получаем компанию
            async with session.get(f'{API_BASE_URL}/sales/companies/all') as resp:
                companies = await resp.json()
                company = next((c for c in companies if c['id'] == company_id), None)
                if company:
                    new_status = not company.get('integration_enabled', False)
                    # Обновляем
                    await session.post(f'{API_BASE_URL}/sales/company/upsert', 
                                      json={'id': company_id, 'integration_enabled': new_status})
                    status_text = '✅ Включена' if new_status else '❌ Выключена'
                    await callback.answer(f"Интеграция: {status_text}")
                    # Показываем обновленный статус с кнопками
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="❌ Выключить" if new_status else "✅ Включить",
                            callback_data=f"toggle_int_{company_id}"
                        )],
                        [InlineKeyboardButton(text="⚙️ Настроить", callback_data=f"setup_int_{company_id}")]
                    ])
                    await callback.message.edit_text(
                        f"🔌 Интеграция для {company['name']}: {status_text}",
                        reply_markup=kb
                    )
        except Exception as e:
            await callback.answer(f"❌ Ошибка: {str(e)[:40]}")

@dp.callback_query(lambda c: c.data.startswith('setup_int_'))
async def setup_integration(callback: types.CallbackQuery, state: FSMContext):
    """Настройка интеграции"""
    company_id = int(callback.data.split('_')[2])
    
    text = "⚙️ <b>Настройка интеграции</b>\n\nВыберите тип CRM:\n\n"
    text += "1️⃣ Bitrix24\n"
    text += "2️⃣ KOMMO\n"
    text += "3️⃣ AmoCRM\n\n"
    text += "Введите номер:"
    
    await state.update_data(company_id=company_id)
    await state.set_state(IntegrationFlow.editing_type)
    await callback.message.answer(text, parse_mode='HTML')
    await callback.answer()

@dp.message(IntegrationFlow.editing_type)
async def process_integration_type(message: types.Message, state: FSMContext):
    """Сохранение типа CRM и начало настройки 1С"""
    types_map = {'1': 'bitrix24', '2': 'kommo', '3': 'amocrm'}
    itype = types_map.get(message.text.strip())
    
    if not itype:
        await message.answer("❌ Введите 1, 2 или 3")
        return
    
    await state.update_data(integration_type=itype)
    await state.set_state(IntegrationFlow.editing_onec_url)
    await message.answer(
        f"✅ Тип CRM: {itype.upper()}\n\n"
        f"<b>Шаг 1/3: 1С OData URL</b>\n\n"
        f"Пример: http://2.133.147.210:8081/company_Technology\n\n"
        f"Введите URL 1С:",
        parse_mode='HTML'
    )

@dp.message(IntegrationFlow.editing_onec_url)
async def process_onec_url(message: types.Message, state: FSMContext):
    """Ввод 1С URL"""
    await state.update_data(onec_base_url=message.text.strip())
    await state.set_state(IntegrationFlow.editing_onec_username)
    await message.answer("<b>Шаг 2/3: 1С Username</b>\n\nВведите логин:", parse_mode='HTML')

@dp.message(IntegrationFlow.editing_onec_username)
async def process_onec_username(message: types.Message, state: FSMContext):
    """Ввод 1С username"""
    await state.update_data(onec_username=message.text.strip())
    await state.set_state(IntegrationFlow.editing_onec_password)
    await message.answer("<b>Шаг 3/3: 1С Password</b>\n\nВведите пароль:", parse_mode='HTML')

@dp.message(IntegrationFlow.editing_onec_password)
async def process_onec_password(message: types.Message, state: FSMContext):
    """Ввод 1С password и переход к настройке CRM"""
    await state.update_data(onec_password=message.text.strip())
    
    data = await state.get_data()
    itype = data.get('integration_type')
    
    if itype == 'bitrix24':
        await state.set_state(IntegrationFlow.editing_bitrix_webhook)
        await message.answer(
            "<b>Bitrix24 Webhook URL</b>\n\n"
            "Пример: https://company.bitrix24.ru/rest/1/xxxxx/\n\n"
            "Введите webhook:",
            parse_mode='HTML'
        )
    elif itype in ['kommo', 'amocrm']:
        await state.set_state(IntegrationFlow.editing_kommo_subdomain)
        await message.answer(
            f"<b>{itype.upper()} Subdomain</b>\n\n"
            f"Пример: mycompany\n\n"
            f"Введите subdomain:",
            parse_mode='HTML'
        )

@dp.message(IntegrationFlow.editing_bitrix_webhook)
async def process_bitrix_webhook(message: types.Message, state: FSMContext):
    """Ввод Bitrix24 webhook и сохранение"""
    await state.update_data(bitrix24_webhook_url=message.text.strip())
    await save_integration_settings(message, state)

@dp.message(IntegrationFlow.editing_kommo_subdomain)
async def process_kommo_subdomain(message: types.Message, state: FSMContext):
    """Ввод KOMMO subdomain"""
    await state.update_data(kommo_subdomain=message.text.strip())
    await state.set_state(IntegrationFlow.editing_kommo_client_id)
    await message.answer("<b>KOMMO Client ID</b>\n\nВведите:", parse_mode='HTML')

@dp.message(IntegrationFlow.editing_kommo_client_id)
async def process_kommo_client_id(message: types.Message, state: FSMContext):
    """Ввод KOMMO client ID"""
    await state.update_data(kommo_client_id=message.text.strip())
    await state.set_state(IntegrationFlow.editing_kommo_client_secret)
    await message.answer("<b>KOMMO Client Secret</b>\n\nВведите:", parse_mode='HTML')

@dp.message(IntegrationFlow.editing_kommo_client_secret)
async def process_kommo_client_secret(message: types.Message, state: FSMContext):
    """Ввод KOMMO client secret"""
    await state.update_data(kommo_client_secret=message.text.strip())
    await state.set_state(IntegrationFlow.editing_kommo_refresh_token)
    await message.answer("<b>KOMMO Refresh Token</b>\n\nВведите:", parse_mode='HTML')

@dp.message(IntegrationFlow.editing_kommo_refresh_token)
async def process_kommo_refresh_token(message: types.Message, state: FSMContext):
    """Ввод KOMMO refresh token и сохранение"""
    await state.update_data(kommo_refresh_token=message.text.strip())
    await save_integration_settings(message, state)

async def save_integration_settings(message: types.Message, state: FSMContext):
    """Сохранение всех настроек интеграции"""
    data = await state.get_data()
    company_id = data.get('company_id')
    
    # Подготавливаем данные для сохранения
    save_data = {
        'id': company_id,
        'integration_enabled': True,
        'integration_type': data.get('integration_type'),
        'onec_enabled': True,
        'onec_base_url': data.get('onec_base_url'),
        'onec_username': data.get('onec_username'),
        'onec_password': data.get('onec_password')
    }
    
    # Добавляем CRM-специфичные поля
    if data.get('bitrix24_webhook_url'):
        save_data['bitrix24_webhook_url'] = data.get('bitrix24_webhook_url')
    if data.get('kommo_subdomain'):
        save_data['kommo_subdomain'] = data.get('kommo_subdomain')
        save_data['kommo_client_id'] = data.get('kommo_client_id')
        save_data['kommo_client_secret'] = data.get('kommo_client_secret')
        save_data['kommo_refresh_token'] = data.get('kommo_refresh_token')
    
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(f'{API_BASE_URL}/sales/company/upsert', json=save_data)
            itype = data.get('integration_type', '').upper()
            await message.answer(
                f"✅ <b>Интеграция настроена!</b>\n\n"
                f"Тип: {itype}\n"
                f"1С: {data.get('onec_base_url')}\n"
                f"Статус: Активна\n\n"
                f"Используйте /start для возврата в меню.",
                parse_mode='HTML',
                reply_markup=get_main_keyboard()
            )
            await state.clear()
        except Exception as e:
            await message.answer(f"❌ Ошибка сохранения: {str(e)[:100]}")


@dp.message(F.text == "🏠 Меню")
async def btn_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔐 <b>SuperAdmin Panel</b>\n\nВыберите действие:", parse_mode="HTML", reply_markup=get_main_keyboard())

@dp.message()
async def handle_any(message: types.Message, state: FSMContext):
    current = await state.get_state()
    if current: return
    await message.answer("Выберите кнопку:", reply_markup=get_main_keyboard())

async def main():
    logging.info("🔐 SuperAdmin Bot starting...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
