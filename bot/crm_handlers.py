"""
CRM Handlers Module - Manager Lead Cards
"""

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

def get_manager_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мои лиды"), KeyboardButton(text="📊 Мой рейтинг")],
            [KeyboardButton(text="🏆 Лидерборд"), KeyboardButton(text="🏠 Меню")]
        ],
        resize_keyboard=True
    )

async def is_manager(user_id: int, company_id: int) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/managers') as resp:
                if resp.status == 200:
                    managers = await resp.json()
                    return any(m.get('user_id') == user_id for m in managers)
    except:
        pass
    return False

async def get_lead_details(company_id: int, lead_id: int) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}') as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logging.error(f"Get lead error: {e}")
    return None

async def get_statuses(company_id: int) -> list:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/statuses') as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logging.error(f"Get statuses error: {e}")
    return []

def format_lead_card(lead: dict, statuses: list = None) -> str:
    contact = lead.get('contact_info', {}) or {}
    name = contact.get('name', 'Не указано')
    phone = contact.get('phone', 'Не указан')
    temperature = contact.get('temperature', '')
    source = lead.get('source', 'web')
    created = lead.get('created_at', '')[:16].replace('T', ' ') if lead.get('created_at') else ''
    current_status = lead.get('status', 'new')
    status_emoji, status_name = "🆕", "Новый"
    if statuses:
        for s in statuses:
            if s.get('code') == current_status or s.get('name') == current_status:
                status_emoji = s.get('emoji', '🆕')
                status_name = s.get('name', current_status)
                break
    ai_section = ""
    if temperature:
        ai_section = f"\n🔥 Температура: {temperature}"
    return f"""📋 <b>Лид #{lead.get('id', '?')}</b>

👤 {name}
📞 <code>{phone}</code>
📱 {source}
📅 {created}
{ai_section}

📊 Статус: {status_emoji} {status_name}"""

def get_lead_keyboard(lead_id: int, lead: dict, statuses: list) -> InlineKeyboardMarkup:
    buttons = []
    
    # Статусы - в одну строку
    row = []
    for s in statuses[:5]:
        code = s.get('code', str(s.get('id', '')))
        emoji = s.get('emoji', '⚪')
        row.append(InlineKeyboardButton(text=emoji, callback_data=f"lst:{lead_id}:{code}"))
    if row:
        buttons.append(row)
    
    # Контакты - прямые ссылки
    contact = lead.get('contact_info', {}) or {}
    phone = contact.get('phone', '').replace('+', '').replace(' ', '').replace('-', '')
    tg_id = lead.get('telegram_user_id')
    
    contact_row = []
    if phone:
        contact_row.append(InlineKeyboardButton(text="💬 WhatsApp", url=f"https://wa.me/{phone}"))
    if tg_id:
        contact_row.append(InlineKeyboardButton(text="✈️ Telegram", url=f"tg://user?id={tg_id}"))
    if contact_row:
        buttons.append(contact_row)
    
    # Действия
    buttons.append([
        InlineKeyboardButton(text="📞 Номер", callback_data=f"lph:{lead_id}"),
        InlineKeyboardButton(text="📝 Заметка", callback_data=f"lnt:{lead_id}")
    ])
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back_leads")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# === /join ===
@crm_router.message(Command('join'))
async def cmd_join(message: types.Message):
    company_id = getattr(message.bot, 'company_id', 1)
    user_id = message.from_user.id
    username = message.from_user.username or ''
    full_name = message.from_user.full_name or 'Менеджер'
    
    if await is_manager(user_id, company_id):
        await message.answer(f"👋 С возвращением, {full_name}!", reply_markup=get_manager_keyboard())
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{API_BASE_URL}/crm/{company_id}/managers',
                json={'telegram_id': user_id, 'telegram_username': username, 'full_name': full_name}) as resp:
                if resp.status == 200:
                    await message.answer(f"🎉 <b>Добро пожаловать, {full_name}!</b>\n\nВы зарегистрированы как менеджер.", parse_mode='HTML', reply_markup=get_manager_keyboard())
                else:
                    await message.answer("❌ Ошибка регистрации")
    except Exception as e:
        logging.error(f"Join error: {e}")
        await message.answer("❌ Ошибка")

# === Мои лиды ===
@crm_router.message(F.text == "📋 Мои лиды")
async def my_leads_handler(message: types.Message):
    company_id = getattr(message.bot, 'company_id', 1)
    if not await is_manager(message.from_user.id, company_id):
        await message.answer("❌ Напишите /join")
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/{company_id}/leads', params={'limit': 20}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    leads = data if isinstance(data, list) else data.get('leads', [])
                    leads = [l for l in leads if l.get('contact_info') and (l['contact_info'].get('name') or l['contact_info'].get('phone'))]
                    
                    if not leads:
                        await message.answer("📋 Лидов пока нет")
                        return
                    
                    text = "📋 <b>Мои лиды</b>\n\n"
                    buttons = []
                    for lead in leads[:10]:
                        contact = lead.get('contact_info', {}) or {}
                        name = contact.get('name', 'Без имени')
                        lead_id = lead.get('id', 0)
                        text += f"• #{lead_id} {name}\n"
                        buttons.append([InlineKeyboardButton(text=f"👁 #{lead_id} {name[:20]}", callback_data=f"vld:{lead_id}")])
                    
                    await message.answer(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception as e:
        logging.error(f"Leads error: {e}")
        await message.answer("❌ Ошибка")

# === Мой рейтинг ===
@crm_router.message(F.text == "📊 Мой рейтинг")
async def my_rating_handler(message: types.Message):
    company_id = getattr(message.bot, 'company_id', 1)
    if not await is_manager(message.from_user.id, company_id):
        await message.answer("❌ Напишите /join")
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/managers/{message.from_user.id}') as resp:
                if resp.status == 200:
                    m = await resp.json()
                    await message.answer(f"📊 <b>Ваш рейтинг</b>\n\n💰 Монетки: {m.get('coins', 0)}\n📋 Лидов: {m.get('leads_count', 0)}\n✅ Сделок: {m.get('deals_count', 0)}", parse_mode='HTML')
                else:
                    await message.answer("📊 <b>Ваш рейтинг</b>\n\n💰 Монетки: 0", parse_mode='HTML')
    except:
        await message.answer("📊 💰 Монетки: 0")

# === Лидерборд ===
@crm_router.message(F.text == "🏆 Лидерборд")
async def leaderboard_handler(message: types.Message):
    company_id = getattr(message.bot, 'company_id', 1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/leaderboard') as resp:
                if resp.status == 200:
                    leaders = await resp.json()
                    if not leaders:
                        await message.answer("🏆 <b>Лидерборд</b>\n\nПока пусто", parse_mode='HTML')
                        return
                    text = "🏆 <b>Лидерборд</b>\n\n"
                    medals = ['🥇', '🥈', '🥉']
                    for i, m in enumerate(leaders[:10]):
                        medal = medals[i] if i < 3 else f"{i+1}."
                        text += f"{medal} {m.get('full_name', '?')} — {m.get('coins', 0)} 💰\n"
                    await message.answer(text, parse_mode='HTML')
                else:
                    await message.answer("🏆 Пока пусто")
    except:
        await message.answer("❌ Ошибка")

# === Меню ===
@crm_router.message(F.text == "🏠 Меню")
async def manager_menu_handler(message: types.Message):
    company_id = getattr(message.bot, 'company_id', 1)
    if await is_manager(message.from_user.id, company_id):
        await message.answer("🏠 <b>Меню</b>", parse_mode='HTML', reply_markup=get_manager_keyboard())

# === Просмотр лида ===
@crm_router.callback_query(F.data.startswith("vld:"))
async def view_lead_callback(callback: types.CallbackQuery):
    lead_id = int(callback.data.split(":")[1])
    company_id = getattr(callback.bot, 'company_id', 1)
    lead = await get_lead_details(company_id, lead_id)
    if not lead:
        await callback.answer("❌ Лид не найден", show_alert=True)
        return
    statuses = await get_statuses(company_id)
    card = format_lead_card(lead, statuses)
    kb = get_lead_keyboard(lead_id, lead, statuses)
    await callback.message.edit_text(card, parse_mode='HTML', reply_markup=kb)
    await callback.answer()

# === Смена статуса ===
@crm_router.callback_query(F.data.startswith("lst:"))
async def change_status_callback(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    lead_id, new_status = int(parts[1]), parts[2]
    company_id = getattr(callback.bot, 'company_id', 1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}/status',
                json={'status': new_status, 'manager_id': callback.from_user.id}) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    coins = result.get('coins_earned', 0)
                    name = result.get('status_name', 'OK')
                    msg = f"✅ {name}" + (f" +{coins}💰" if coins > 0 else "")
                    await callback.answer(msg, show_alert=coins > 0)
                    # Обновить карточку
                    lead = await get_lead_details(company_id, lead_id)
                    statuses = await get_statuses(company_id)
                    if lead:
                        await callback.message.edit_text(format_lead_card(lead, statuses), parse_mode='HTML', reply_markup=get_lead_keyboard(lead_id, lead, statuses))
                else:
                    await callback.answer("❌ Ошибка", show_alert=True)
    except Exception as e:
        logging.error(f"Status error: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

# === Показать номер ===
@crm_router.callback_query(F.data.startswith("lph:"))
async def phone_callback(callback: types.CallbackQuery):
    lead_id = int(callback.data.split(":")[1])
    company_id = getattr(callback.bot, 'company_id', 1)
    lead = await get_lead_details(company_id, lead_id)
    if lead:
        phone = (lead.get('contact_info', {}) or {}).get('phone', '')
        if phone:
            await callback.message.answer(f"📞 <b>Номер телефона:</b>\n\n<code>{phone}</code>", parse_mode='HTML')
            await callback.answer()
        else:
            await callback.answer("❌ Нет номера", show_alert=True)
    else:
        await callback.answer("❌ Лид не найден", show_alert=True)

# === Заметка ===
@crm_router.callback_query(F.data.startswith("lnt:"))
async def note_callback(callback: types.CallbackQuery, state: FSMContext):
    lead_id = int(callback.data.split(":")[1])
    await state.update_data(note_lead_id=lead_id)
    await state.set_state(CRMStates.entering_note)
    await callback.message.answer(f"📝 Введите заметку к лиду #{lead_id}:\n\n/cancel для отмены")
    await callback.answer()

@crm_router.message(CRMStates.entering_note)
async def process_note(message: types.Message, state: FSMContext):
    if message.text == '/cancel':
        await state.clear()
        await message.answer("❌ Отменено")
        return
    data = await state.get_data()
    lead_id = data.get('note_lead_id')
    company_id = getattr(message.bot, 'company_id', 1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}/notes',
                json={'text': message.text, 'manager_id': message.from_user.id}) as resp:
                if resp.status == 200:
                    await message.answer(f"✅ Заметка сохранена")
                else:
                    await message.answer(f"❌ Ошибка: {resp.status}")
    except Exception as e:
        logging.error(f"Note error: {e}")
        await message.answer("❌ Ошибка сохранения")
    await state.clear()

# === Назад ===
@crm_router.callback_query(F.data == "back_leads")
async def back_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()
