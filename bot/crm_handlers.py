"""CRM Handlers - Manager Lead Cards - ПОЛНАЯ ВЕРСИЯ"""
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
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Мои лиды"), KeyboardButton(text="📊 Мой рейтинг")],
        [KeyboardButton(text="🏆 Лидерборд"), KeyboardButton(text="🏠 Меню")]
    ], resize_keyboard=True)

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
    return [
        {"code": "1", "emoji": "🆕", "name": "Новый"},
        {"code": "2", "emoji": "📞", "name": "В работе"},
        {"code": "3", "emoji": "📅", "name": "Встреча"},
        {"code": "4", "emoji": "✅", "name": "Сделка"},
        {"code": "5", "emoji": "❌", "name": "Отказ"}
    ]

def format_lead_card(lead: dict, statuses: list = None) -> str:
    contact = lead.get('contact_info', {}) or {}
    name = contact.get('name', 'Не указано')
    phone = contact.get('phone', 'Не указан')
    source = lead.get('source', 'web')
    created = (lead.get('created_at') or '')[:16].replace('T', ' ')
    
    # Менеджер
    manager_name = lead.get('assigned_user_name', '')
    
    # AI данные
    ai_summary = lead.get('ai_summary', '')
    conversation = lead.get('conversation_summary', '')
    temperature = lead.get('temperature') or contact.get('temperature', '')
    
    # Статус из лида или из настроек
    status_emoji = lead.get('status_emoji', '🆕')
    status_name = lead.get('status_name', lead.get('status', 'Новый'))
    
    # Telegram username из contact_info
    tg_username = contact.get('telegram_username', '')
    
    # Формируем карточку
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

    # AI анализ
    if ai_summary or conversation or temperature:
        card += "\n\n<b>🤖 AI-анализ:</b>"
        if temperature:
            card += f"\nТемпература: {temperature}"
        if ai_summary:
            card += f"\n{ai_summary[:200]}"
        if conversation and not ai_summary:
            card += f"\n{conversation[:200]}"

    card += f"\n\n<b>📊 Статус:</b> {status_emoji} {status_name}"
    
    return card

def get_lead_keyboard(lead_id: int, lead: dict, statuses: list, current_user_id: int) -> InlineKeyboardMarkup:
    buttons = []
    
    # Если лид не назначен — кнопка "Взять в работу"
    if not lead.get('assigned_user_id'):
        buttons.append([InlineKeyboardButton(text="📞 Взять в работу", callback_data=f"take:{lead_id}")])
    
    # Статусы - иконка + полное название, вертикально
    for s in statuses[:5]:
        code = str(s.get('code', s.get('id', '')))
        emoji = s.get('emoji', '⚪')
        name = s.get('name', '')
        buttons.append([InlineKeyboardButton(text=f"{emoji} {name}", callback_data=f"lst:{lead_id}:{code}")])
    
    # Контакты
    contact = lead.get('contact_info', {}) or {}
    phone = contact.get('phone', '').replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    tg_username = contact.get('telegram_username', '')
    
    contact_row = []
    if phone:
        contact_row.append(InlineKeyboardButton(text="💬 WhatsApp", url=f"https://wa.me/{phone}"))
    if tg_username:
        contact_row.append(InlineKeyboardButton(text="✈️ Telegram", url=f"https://t.me/{tg_username}"))
    if contact_row:
        buttons.append(contact_row)
    
    # Действия
    buttons.append([
        InlineKeyboardButton(text="📞 Номер", callback_data=f"lph:{lead_id}"),
        InlineKeyboardButton(text="📝 Заметка", callback_data=f"lnt:{lead_id}")
    ])
    buttons.append([InlineKeyboardButton(text="« Назад к списку", callback_data="back_leads")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# === /join ===
@crm_router.message(Command('join'))
async def cmd_join(message: types.Message):
    company_id = message.bot.company_id
    user_id = message.from_user.id
    if await is_manager(user_id, company_id):
        await message.answer(f"👋 С возвращением, {message.from_user.full_name}!", reply_markup=get_manager_keyboard())
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{API_BASE_URL}/crm/{company_id}/managers',
                json={'telegram_id': user_id, 'telegram_username': message.from_user.username or '', 'full_name': message.from_user.full_name or 'Менеджер'}) as resp:
                if resp.status == 200:
                    await message.answer(f"🎉 <b>Добро пожаловать!</b>\n\nВы зарегистрированы.", parse_mode='HTML', reply_markup=get_manager_keyboard())
                else:
                    await message.answer("❌ Ошибка регистрации")
    except Exception as e:
        logging.error(f"Join: {e}")
        await message.answer("❌ Ошибка")

# === Мои лиды ===
@crm_router.message(F.text == "📋 Мои лиды")
async def my_leads_handler(message: types.Message):
    company_id = message.bot.company_id
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
                        phone = contact.get('phone', '')
                        lead_id = lead.get('id', 0)
                        status_emoji = lead.get('status_emoji', '🆕')
                        
                        text += f"{status_emoji} #{lead_id} {name} {phone}\n"
                        buttons.append([InlineKeyboardButton(text=f"{status_emoji} #{lead_id} {name} {phone}", callback_data=f"vld:{lead_id}")])
                    
                    await message.answer(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception as e:
        logging.error(f"Leads: {e}")
        await message.answer("❌ Ошибка")

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
        await message.answer("📊 💰 Монетки: 0")

# === Лидерборд ===
@crm_router.message(F.text == "🏆 Лидерборд")
async def leaderboard_handler(message: types.Message):
    company_id = message.bot.company_id
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/leaderboard') as resp:
                leaders = await resp.json() if resp.status == 200 else []
                if not leaders:
                    await message.answer("🏆 <b>Лидерборд</b>\n\nПока пусто", parse_mode='HTML')
                    return
                text = "🏆 <b>Лидерборд</b>\n\n"
                medals = ['🥇', '🥈', '🥉']
                for i, m in enumerate(leaders[:10]):
                    medal = medals[i] if i < 3 else f"{i+1}."
                    text += f"{medal} {m.get('full_name', '?')} — {m.get('coins', 0)} 💰\n"
                await message.answer(text, parse_mode='HTML')
    except:
        await message.answer("❌ Ошибка")

# === Меню ===
@crm_router.message(F.text == "🏠 Меню")
async def manager_menu(message: types.Message):
    company_id = message.bot.company_id
    if await is_manager(message.from_user.id, company_id):
        await message.answer("🏠 <b>Меню</b>", parse_mode='HTML', reply_markup=get_manager_keyboard())

# === Просмотр лида ===
@crm_router.callback_query(F.data.startswith("vld:"))
async def view_lead(callback: types.CallbackQuery):
    lead_id = int(callback.data.split(":")[1])
    company_id = callback.bot.company_id
    lead = await get_lead_details(company_id, lead_id)
    if not lead:
        await callback.answer("❌ Лид не найден", show_alert=True)
        return
    statuses = await get_statuses(company_id)
    await callback.message.edit_text(format_lead_card(lead, statuses), parse_mode='HTML', reply_markup=get_lead_keyboard(lead_id, lead, statuses, callback.from_user.id))
    await callback.answer()

# === Взять в работу ===
@crm_router.callback_query(F.data.startswith("take:"))
async def take_lead(callback: types.CallbackQuery):
    lead_id = int(callback.data.split(":")[1])
    company_id = callback.bot.company_id
    user_id = callback.from_user.id
    user_name = callback.from_user.full_name
    
    try:
        async with aiohttp.ClientSession() as session:
            # Назначить менеджера и сменить статус на "В работе"
            async with session.patch(f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}/assign',
                json={'user_id': user_id, 'user_name': user_name}) as resp:
                if resp.status == 200:
                    await callback.answer(f"✅ Лид #{lead_id} теперь ваш!", show_alert=True)
                    # Обновить карточку
                    lead = await get_lead_details(company_id, lead_id)
                    statuses = await get_statuses(company_id)
                    if lead:
                        await callback.message.edit_text(format_lead_card(lead, statuses), parse_mode='HTML', reply_markup=get_lead_keyboard(lead_id, lead, statuses, user_id))
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
                        await callback.message.edit_text(format_lead_card(lead, statuses), parse_mode='HTML', reply_markup=get_lead_keyboard(lead_id, lead, statuses, callback.from_user.id))
                else:
                    await callback.answer(f"❌ Ошибка {resp.status}", show_alert=True)
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
            await callback.message.answer(f"📞 <b>Номер телефона:</b>\n\n<code>{phone}</code>", parse_mode='HTML')
            await callback.answer()
        else:
            await callback.answer("❌ Нет номера", show_alert=True)
    else:
        await callback.answer("❌ Лид не найден", show_alert=True)

# === Заметка ===
@crm_router.callback_query(F.data.startswith("lnt:"))
async def note_start(callback: types.CallbackQuery, state: FSMContext):
    lead_id = int(callback.data.split(":")[1])
    await state.update_data(note_lead_id=lead_id, note_user_name=callback.from_user.full_name)
    await state.set_state(CRMStates.entering_note)
    await callback.message.answer(f"📝 Введите заметку к лиду #{lead_id}:\n\n/cancel для отмены")
    await callback.answer()

@crm_router.message(CRMStates.entering_note)
async def note_save(message: types.Message, state: FSMContext):
    if message.text == '/cancel':
        await state.clear()
        await message.answer("❌ Отменено")
        return
    data = await state.get_data()
    lead_id = data.get('note_lead_id')
    user_name = data.get('note_user_name', message.from_user.full_name)
    company_id = message.bot.company_id
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}/notes',
                json={'text': message.text, 'manager_id': message.from_user.id, 'user_name': user_name, 'is_voice': False}) as resp:
                if resp.status == 200:
                    await message.answer("✅ Заметка сохранена")
                else:
                    await message.answer(f"❌ Ошибка {resp.status}")
    except Exception as e:
        logging.error(f"Note: {e}")
        await message.answer("❌ Ошибка")
    await state.clear()

# === Назад ===
@crm_router.callback_query(F.data == "back_leads")
async def back(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()
