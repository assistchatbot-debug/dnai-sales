"""CRM Handlers - Manager Lead Cards - v5 FINAL"""
import logging
import aiohttp
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from config import API_BASE_URL

crm_router = Router()

class CRMStates(StatesGroup):
    entering_note = State()
    join_firstname = State()
    join_lastname = State()
    join_phone = State()

def get_manager_keyboard():
    """Manager keyboard - NO Menu button"""
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Лиды"), KeyboardButton(text="📁 Мои лиды")],
        [KeyboardButton(text="📊 Мой рейтинг"), KeyboardButton(text="🏆 Лидерборд")]
    ], resize_keyboard=True)

async def get_manager_fullname(company_id: int, user_id: int) -> str:
    """Get manager full_name from DB"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/managers/{user_id}') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('full_name', '')
    except: pass
    return ''

async def is_manager(user_id: int, company_id: int) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/managers') as resp:
                if resp.status == 200:
                    return any(m.get('user_id') == user_id for m in await resp.json())
    except: pass
    return False

async def get_lead_details(company_id: int, lead_id: int) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}') as resp:
                if resp.status == 200: return await resp.json()
    except Exception as e: logging.error(f"Get lead: {e}")
    return None

async def get_statuses(company_id: int) -> list:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/statuses') as resp:
                if resp.status == 200: return await resp.json()
    except: pass
    return [{"code": "1", "emoji": "🆕", "name": "Новый"}, {"code": "2", "emoji": "📞", "name": "В работе"},
            {"code": "3", "emoji": "📅", "name": "Встреча"}, {"code": "4", "emoji": "✅", "name": "Сделка"},
            {"code": "5", "emoji": "❌", "name": "Отказ"}]

def format_temperature(temp) -> str:
    if isinstance(temp, str) and any(w in temp.lower() for w in ['горяч', 'тепл', 'холод']):
        return temp
    if isinstance(temp, (int, float)):
        if temp >= 70: return "🔥 горячий"
        elif temp >= 40: return "🌤 тёплый"
        else: return "❄️ холодный"
    return str(temp) if temp else ""

def format_lead_card(lead: dict, statuses: list = None) -> str:
    contact = lead.get('contact_info', {}) or {}
    name = contact.get('name', 'Не указано')
    phone = contact.get('phone', 'Не указан')
    source = lead.get('source', 'web')
    created = (lead.get('created_at') or '')[:16].replace('T', ' ')
    manager_name = lead.get('assigned_user_name', '')
    ai_summary = lead.get('ai_summary', '')
    conversation = lead.get('conversation_summary', '')
    temp_raw = contact.get('temperature') or lead.get('temperature')
    temperature = format_temperature(temp_raw)
    status_emoji = lead.get('status_emoji', '🆕')
    status_name = lead.get('status_name', lead.get('status', 'Новый'))
    tg_username = contact.get('telegram_username') or contact.get('username', '')
    tg_user_id = lead.get('telegram_user_id')
    
    card = f"""📋 <b>Лид #{lead.get('id', '?')}</b>

<b>👤 Клиент:</b> {name}
<b>📞 Телефон:</b> <code>{phone}</code>
<b>📱 Источник:</b> {source}
<b>📅 Создан:</b> {created}"""

    if manager_name:
        card += f"\n<b>👨‍💼 Менеджер:</b> {manager_name}"
    else:
        card += f"\n<b>👨‍💼 Менеджер:</b> <i>не назначен</i>"

    if tg_username:
        card += f"\n<b>✈️ Telegram:</b> @{tg_username}"
    elif tg_user_id:
        card += f"\n<b>✈️ Telegram ID:</b> {tg_user_id}"

    if ai_summary or conversation or temperature:
        card += "\n\n<b>🤖 AI-анализ:</b>"
        if temperature:
            card += f"\nТемпература: {temperature}"
        if ai_summary:
            card += f"\n{ai_summary[:200]}"
        elif conversation:
            card += f"\n{conversation[:200]}"

    card += f"\n\n<b>📊 Статус:</b> {status_emoji} {status_name}"
    
    # Показать заметки
    notes = lead.get('notes', [])
    if notes:
        card += "\n\n<b>📝 Заметки:</b>"
        for note in notes[:3]:
            author = note.get('user_name', 'Менеджер')
            date = (note.get('created_at') or '')[:10]
            text = (note.get('content') or '')[:50]
            card += f"\n• {date} {author}:\n  {text}"
    
    return card

def get_lead_keyboard(lead_id: int, lead: dict, statuses: list) -> InlineKeyboardMarkup:
    buttons = []
    contact = lead.get('contact_info', {}) or {}
    phone = contact.get('phone', '').replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    tg_username = contact.get('telegram_username') or contact.get('username', '')
    tg_user_id = lead.get('telegram_user_id')
    assigned = lead.get('assigned_user_id')
    
    if not assigned:
        # Только "Взять в работу"
        buttons.append([InlineKeyboardButton(text="📞 Взять в работу", callback_data=f"take:{lead_id}")])
    else:
        # Статусы вертикально
        for s in statuses[:5]:
            code = str(s.get('code', s.get('id', '')))
            emoji = s.get('emoji', '⚪')
            name = s.get('name', '')
            buttons.append([InlineKeyboardButton(text=f"{emoji} {name}", callback_data=f"lst:{lead_id}:{code}")])
        
        # Контакты: WhatsApp + Telegram
        contact_row = []
        if phone:
            contact_row.append(InlineKeyboardButton(text="💬 WhatsApp", url=f"https://wa.me/{phone}"))
            # Telegram через номер телефона
            contact_row.append(InlineKeyboardButton(text="✈️ Telegram", url=f"https://t.me/+{phone}"))
        if contact_row:
            buttons.append(contact_row)
        
        # Действия
        buttons.append([
            InlineKeyboardButton(text="📞 Номер", callback_data=f"lph:{lead_id}"),
            InlineKeyboardButton(text="📝 Заметка", callback_data=f"lnt:{lead_id}")
        ])
    
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_leads")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# === /reset ===
@crm_router.message(Command('reset'))
async def cmd_reset(message: types.Message, state: FSMContext):
    company_id = message.bot.company_id
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(f'{API_BASE_URL}/crm/{company_id}/managers/{message.from_user.id}') as resp:
                await state.clear()
                await message.answer("✅ Данные сброшены.\n\nНапишите /join")
    except:
        await message.answer("❌ Ошибка")

# === /join ===
@crm_router.message(Command('join'))
async def cmd_join(message: types.Message, state: FSMContext):
    company_id = message.bot.company_id
    if await is_manager(message.from_user.id, company_id):
        manager_name = await get_manager_fullname(company_id, message.from_user.id)
        # Проверить полноту данных
        if manager_name and ' ' in manager_name and '.' not in manager_name:
            await message.answer(f"👋 С возвращением, {manager_name}!", reply_markup=get_manager_keyboard())
            return
    await state.set_state(CRMStates.join_firstname)
    await message.answer("👤 <b>Регистрация</b>\n\nВведите ваше <b>Имя</b>:", parse_mode='HTML')

@crm_router.message(CRMStates.join_firstname)
async def join_firstname(message: types.Message, state: FSMContext):
    await state.update_data(firstname=message.text.strip())
    await state.set_state(CRMStates.join_lastname)
    await message.answer("Введите вашу <b>Фамилию</b>:", parse_mode='HTML')

@crm_router.message(CRMStates.join_lastname)
async def join_lastname(message: types.Message, state: FSMContext):
    await state.update_data(lastname=message.text.strip())
    await state.set_state(CRMStates.join_phone)
    await message.answer("Введите ваш <b>Телефон</b>:", parse_mode='HTML')

@crm_router.message(CRMStates.join_phone)
async def join_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    full_name = f"{data.get('firstname', '')} {data.get('lastname', '')}"
    company_id = message.bot.company_id
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{API_BASE_URL}/crm/{company_id}/managers',
                json={'telegram_id': message.from_user.id, 'telegram_username': message.from_user.username or '',
                      'full_name': full_name, 'update_existing': True}) as resp:
                if resp.status == 200:
                    await message.answer(f"🎉 <b>Готово, {full_name}!</b>", parse_mode='HTML', reply_markup=get_manager_keyboard())
    except:
        await message.answer("❌ Ошибка")
    await state.clear()

# === Лиды (все) ===
@crm_router.message(F.text == "📋 Лиды")
async def all_leads_handler(message: types.Message, state: FSMContext):
    await state.update_data(leads_mode='all', leads_offset=0)
    await show_leads_page(message, 0, 'all')

# === Мои лиды ===
@crm_router.message(F.text == "📁 Мои лиды")
async def my_leads_handler(message: types.Message, state: FSMContext):
    await state.update_data(leads_mode='my', leads_offset=0)
    await show_leads_page(message, 0, 'my', message.from_user.id)

async def show_leads_page(message_or_callback, offset: int, mode: str = 'all', filter_user_id: int = None):
    if isinstance(message_or_callback, types.CallbackQuery):
        message = message_or_callback.message
        company_id = message_or_callback.bot.company_id
        user_id = message_or_callback.from_user.id
        is_callback = True
    else:
        message = message_or_callback
        company_id = message.bot.company_id
        user_id = message.from_user.id
        is_callback = False
    
    if not await is_manager(user_id, company_id):
        await message.answer("❌ Напишите /join")
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/leads', params={'limit': 200}) as resp:
                if resp.status == 200:
                    all_leads = await resp.json()
                    all_leads = [l for l in all_leads if l.get('contact_info') and (l['contact_info'].get('name') or l['contact_info'].get('phone'))]
                    
                    # Фильтр: Мои лиды
                    if mode == 'my' and filter_user_id:
                        all_leads = [l for l in all_leads if l.get('assigned_user_id') == filter_user_id]
                    
                    if not all_leads:
                        await message.answer("📋 Лидов пока нет")
                        return
                    
                    page_size = 5
                    total = len(all_leads)
                    offset = max(0, min(offset, total - 1))
                    leads = all_leads[offset:offset+page_size]
                    
                    title = "📁 <b>Мои лиды</b>" if mode == 'my' else "📋 <b>Лиды</b>"
                    text = f"{title} ({offset+1}-{min(offset+page_size, total)} из {total})\n\n"
                    buttons = []
                    
                    for lead in leads:
                        contact = lead.get('contact_info', {}) or {}
                        name = contact.get('name', 'Без имени')
                        phone = contact.get('phone', '')
                        lead_id = lead.get('id', 0)
                        assigned = lead.get('assigned_user_id')
                        icon = "👨‍💼" if assigned else "🆕"
                        text += f"{icon} #{lead_id} {name} {phone}\n"
                        buttons.append([InlineKeyboardButton(text=f"{icon} #{lead_id} {name} {phone}", callback_data=f"vld:{lead_id}")])
                    
                    # Навигация
                    nav_row = []
                    if offset > 0:
                        nav_row.append(InlineKeyboardButton(text="⬆️", callback_data=f"lp:{mode}:{offset-1}"))
                    if offset + page_size < total:
                        nav_row.append(InlineKeyboardButton(text="⬇️", callback_data=f"lp:{mode}:{offset+1}"))
                    if nav_row:
                        buttons.append(nav_row)
                    
                    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
                    if is_callback:
                        await message.edit_text(text, parse_mode='HTML', reply_markup=kb)
                    else:
                        await message.answer(text, parse_mode='HTML', reply_markup=kb)
    except Exception as e:
        logging.error(f"Leads: {e}")
        await message.answer("❌ Ошибка")

@crm_router.callback_query(F.data.startswith("lp:"))
async def leads_page_callback(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    mode, offset = parts[1], int(parts[2])
    filter_uid = callback.from_user.id if mode == 'my' else None
    await show_leads_page(callback, offset, mode, filter_uid)
    await callback.answer()

# === Рейтинг ===
@crm_router.message(F.text == "📊 Мой рейтинг")
async def my_rating_handler(message: types.Message):
    company_id = message.bot.company_id
    if not await is_manager(message.from_user.id, company_id):
        await message.answer("❌ Напишите /join")
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/managers/{message.from_user.id}') as resp:
                m = await resp.json() if resp.status == 200 else {}
                await message.answer(f"📊 <b>Ваш рейтинг</b>\n\n💰 Монетки: {m.get('coins', 0)}\n📋 Лидов: {m.get('leads_count', 0)}\n✅ Сделок: {m.get('deals_count', 0)}", parse_mode='HTML')
    except:
        await message.answer("📊 💰 0")

# === Лидерборд ===
@crm_router.message(F.text == "🏆 Лидерборд")
async def leaderboard_handler(message: types.Message):
    company_id = message.bot.company_id
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/leaderboard') as resp:
                leaders = await resp.json() if resp.status == 200 else []
                if not leaders:
                    await message.answer("🏆 Пусто", parse_mode='HTML')
                    return
                text = "🏆 <b>Лидерборд</b>\n\n"
                medals = ['🥇', '🥈', '🥉']
                for i, m in enumerate(leaders[:10]):
                    medal = medals[i] if i < 3 else f"{i+1}."
                    text += f"{medal} {m.get('full_name', '?')} — {m.get('coins', 0)} 💰\n"
                await message.answer(text, parse_mode='HTML')
    except:
        await message.answer("❌ Ошибка")

# === Просмотр лида ===
@crm_router.callback_query(F.data.startswith("vld:"))
async def view_lead(callback: types.CallbackQuery):
    lead_id = int(callback.data.split(":")[1])
    company_id = callback.bot.company_id
    lead = await get_lead_details(company_id, lead_id)
    if not lead:
        await callback.answer("❌ Не найден", show_alert=True)
        return
    statuses = await get_statuses(company_id)
    await callback.message.edit_text(format_lead_card(lead, statuses), parse_mode='HTML', reply_markup=get_lead_keyboard(lead_id, lead, statuses))
    await callback.answer()

# === Взять в работу ===
@crm_router.callback_query(F.data.startswith("take:"))
async def take_lead(callback: types.CallbackQuery):
    lead_id = int(callback.data.split(":")[1])
    company_id = callback.bot.company_id
    user_id = callback.from_user.id
    # Брать имя из БД
    user_name = await get_manager_fullname(company_id, user_id) or callback.from_user.full_name
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}/assign',
                json={'user_id': user_id, 'user_name': user_name}) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    coins = result.get('coins_earned', 0)
                    await callback.answer(f"✅ Лид ваш! +{coins}💰", show_alert=True)
                    lead = await get_lead_details(company_id, lead_id)
                    statuses = await get_statuses(company_id)
                    if lead:
                        await callback.message.edit_text(format_lead_card(lead, statuses), parse_mode='HTML', reply_markup=get_lead_keyboard(lead_id, lead, statuses))
                else:
                    await callback.answer("❌ Ошибка", show_alert=True)
    except Exception as e:
        logging.error(f"Take: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

# === Смена статуса ===
@crm_router.callback_query(F.data.startswith("lst:"))
async def change_status(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    lead_id, new_status = int(parts[1]), parts[2]
    company_id = callback.bot.company_id
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}/status',
                json={'status': new_status, 'manager_id': callback.from_user.id}) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    coins = result.get('coins_earned', 0)
                    name = result.get('status_name', 'OK')
                    await callback.answer(f"✅ {name}" + (f" +{coins}💰" if coins > 0 else ""), show_alert=coins > 0)
                    lead = await get_lead_details(company_id, lead_id)
                    statuses = await get_statuses(company_id)
                    if lead:
                        await callback.message.edit_text(format_lead_card(lead, statuses), parse_mode='HTML', reply_markup=get_lead_keyboard(lead_id, lead, statuses))
    except Exception as e:
        logging.error(f"Status: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

# === Номер ===
@crm_router.callback_query(F.data.startswith("lph:"))
async def phone_callback(callback: types.CallbackQuery):
    lead_id = int(callback.data.split(":")[1])
    company_id = callback.bot.company_id
    lead = await get_lead_details(company_id, lead_id)
    if lead:
        phone = (lead.get('contact_info', {}) or {}).get('phone', '')
        if phone:
            await callback.message.answer(f"📞 <b>Номер:</b>\n\n<code>{phone}</code>", parse_mode='HTML')
            await callback.answer()
        else:
            await callback.answer("❌ Нет номера", show_alert=True)
    else:
        await callback.answer("❌ Не найден", show_alert=True)

# === Заметка ===
@crm_router.callback_query(F.data.startswith("lnt:"))
async def note_start(callback: types.CallbackQuery, state: FSMContext):
    lead_id = int(callback.data.split(":")[1])
    company_id = callback.bot.company_id
    # Брать имя из БД
    user_name = await get_manager_fullname(company_id, callback.from_user.id) or callback.from_user.full_name
    await state.update_data(note_lead_id=lead_id, note_user_name=user_name)
    await state.set_state(CRMStates.entering_note)
    await callback.message.answer(f"📝 Введите заметку:\n\n/cancel для отмены")
    await callback.answer()

@crm_router.message(CRMStates.entering_note)
async def note_save(message: types.Message, state: FSMContext):
    if message.text == '/cancel':
        await state.clear()
        await message.answer("❌ Отменено")
        return
    data = await state.get_data()
    lead_id = data.get('note_lead_id')
    user_name = data.get('note_user_name')
    company_id = message.bot.company_id
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}/notes',
                json={'text': message.text, 'manager_id': message.from_user.id, 'user_name': user_name}) as resp:
                if resp.status == 200:
                    await message.answer("✅ Сохранено")
                else:
                    await message.answer("❌ Ошибка")
    except:
        await message.answer("❌ Ошибка")
    await state.clear()

# === Назад ===
@crm_router.callback_query(F.data == "back_leads")
async def back(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()
