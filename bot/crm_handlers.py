"""CRM Handlers - Manager Lead Cards - v5 FINAL"""
from states import EventStates
from calendar_kb import get_calendar, get_hour_picker, get_minute_picker
from states import EventStates
from calendar_kb import get_calendar, get_hour_picker, get_minute_picker
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
    waiting_for_deal_amount = State()
    waiting_for_doc_number = State()
    waiting_for_payment_date = State()
    join_lastname = State()
    join_phone = State()

def get_manager_keyboard():
    """Manager keyboard - NO Menu button"""
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Лиды"), KeyboardButton(text="📁 Мои лиды")],
        [KeyboardButton(text="📊 Мой рейтинг"), KeyboardButton(text="🏆 Лидерборд")],
        [KeyboardButton(text="📅 События")]
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

    # AI анализ — Температура + раздел 3 (Интересы клиента)
    temp_display = contact.get('temperature', '')
    interests = ""
    
    # Извлечь раздел 3 из ai_summary
    if ai_summary and "**3. Интересы клиента**" in ai_summary:
        marker_start = "**3. Интересы клиента**"
        idx_start = ai_summary.index(marker_start)
        text_after = ai_summary[idx_start + len(marker_start):]
        if "**4." in text_after:
            idx_end = text_after.index("**4.")
            interests = text_after[:idx_end].strip()
        else:
            interests = text_after.strip()[:600]
    
    if temp_display or interests:
        if temp_display:
            card += f"\n\n<b>🤖 AI-анализ:</b> {temp_display}"
        else:
            card += "\n\n<b>🤖 AI-анализ:</b>"
        if interests:
            card += f"\n\n<b>Интересы:</b>\n{interests}"

    card += f"\n\n<b>📊 Статус:</b> {status_emoji} {status_name}"
    
    # Показать сделки (только с суммой > 0, нумерация 1, 2, 3)
    deals = lead.get('deals', [])
    completed_deals = [d for d in deals if d.get('deal_amount', 0) > 0]
    if completed_deals:
        card += "\n\n<b>💰 Сделки:</b>"
        for i, d in enumerate(completed_deals, 1):
            amount = d.get('deal_amount', 0)
            currency = d.get('deal_currency', 'KZT')
            formatted = f"{amount:,.0f}".replace(',', ' ')
            # Показать ✅ если подтверждена + дата, иначе ⬜
            if d.get('confirmed'):
                # Показывать payment_date в формате ДД.ММ.ГГГГ
                raw_date = d.get('payment_date') or d.get('confirmed_at', '')
                if raw_date and len(str(raw_date)) >= 10:
                    parts = str(raw_date)[:10].split('-')
                    date_str = f"{parts[2]}.{parts[1]}.{parts[0]}" if len(parts) == 3 else ''
                else:
                    date_str = ''
                card += f"\n💰 Сделка {i}: {formatted} {currency} ✅ — {date_str}"
            else:
                card += f"\n💰 Сделка {i}: {formatted} {currency} ⬜"
    
    # Показать заметки
    notes = lead.get('notes', [])
    if notes:
        card += "\n\n<b>📝 Заметки:</b>"
        for note in notes[:3]:
            author = note.get('user_name', 'Менеджер')
            date = (note.get('created_at') or '')[:10]
            text = (note.get('content') or '')[:50]
            card += f"\n• {date} {author}:\n  {text}"
    
    # Показать события лида
    events = lead.get('events', [])
    if events:
        card += "\n\n<b>📅 Предстоящие события:</b>"
        type_icons = {'call': '📞', 'meeting': '🤝', 'email': '📧', 'task': '📋'}
        for ev in events[:3]:
            icon = type_icons.get(ev.get('event_type', ''), '📅')
            sched = ev.get('scheduled_at', '')[:16].replace('T', ' ') if ev.get('scheduled_at') else ''
            desc = (ev.get('description') or '')[:30]
            card += f"\n{icon} {sched}"
            if desc:
                card += f" — {desc}"
    
    return card

def get_lead_keyboard(lead_id: int, lead: dict, statuses: list) -> InlineKeyboardMarkup:
    buttons = []
    # Кнопка диалога вверху
    buttons.append([InlineKeyboardButton(text="📜 Смотреть Диалог", callback_data=f"dialog:{lead_id}")])
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
        for s in statuses[:7]:
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
    
    buttons.append([
        InlineKeyboardButton(text="📅 Событие", callback_data=f"event:{lead_id}"),
        InlineKeyboardButton(text="« Назад", callback_data="back_leads")
    ])
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
                        # Иконки: мой/чужой/новый
                        if not assigned:
                            icon = "🆕"
                        elif assigned == user_id:
                            icon = "👨‍💼"
                        else:
                            icon = "👤"
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
                amount = m.get('total_deal_amount', 0)
                formatted_amount = f"{amount:,.0f}".replace(',', ' ')
                text = f"📊 <b>Ваш рейтинг</b>\n\n"
                text += f"💰 Монетки: {m.get('coins', 0)}\n"
                text += f"📋 Лидов: {m.get('leads_count', 0)}\n"
                text += f"✅ Сделок: {m.get('deals_count', 0)}\n"
                text += f"💵 Сумма: {formatted_amount} ₸"
                await message.answer(text, parse_mode='HTML')
    except:
        await message.answer("📊 💰 0")

# === Лидерборд ===
@crm_router.message(F.text == "🏆 Лидерборд")
async def leaderboard_handler(message: types.Message):
    await show_leaderboard(message, period='all', sort='coins')

async def show_leaderboard(message_or_callback, period='all', sort='coins'):
    if isinstance(message_or_callback, types.CallbackQuery):
        message = message_or_callback.message
        company_id = message_or_callback.bot.company_id
        is_callback = True
    else:
        message = message_or_callback
        company_id = message.bot.company_id
        is_callback = False
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f'{API_BASE_URL}/crm/{company_id}/leaderboard?period={period}&sort={sort}'
            async with session.get(url) as resp:
                leaders = await resp.json() if resp.status == 200 else []
                if not leaders:
                    text = "🏆 Пусто"
                else:
                    # Заголовок с текущим фильтром
                    period_name = {'week': 'Неделя', 'month': 'Месяц', 'all': 'Всё время'}[period]
                    sort_name = {'coins': '💰', 'amount': '💵', 'deals': '✅'}[sort]
                    text = f"🏆 <b>Лидерборд</b> ({period_name}, {sort_name})\n\n"
                    
                    medals = ['🥇', '🥈', '🥉']
                    for i, m in enumerate(leaders[:10]):
                        medal = medals[i] if i < 3 else f"{i+1}."
                        name = m.get('full_name', '?')
                        coins = m.get('coins', 0)
                        deals = m.get('deals_count', 0)
                        amount = m.get('total_deal_amount', 0)
                        formatted = f"{amount:,.0f}".replace(',', ' ')
                        
                        text += f"{medal} {name}\n"
                        if sort == 'coins':
                            text += f"   💰 Монеты: {coins}\n\n"
                        elif sort == 'amount':
                            text += f"   💵 Деньги: {formatted}₸\n\n"
                        elif sort == 'deals':
                            text += f"   ✅ Сделки: {deals}\n\n"
                        else:
                            text += f"   💰 Монеты: {coins}\n   💵 Деньги: {formatted}₸\n   ✅ Сделки: {deals}\n\n"
                
                # Кнопки периода и сортировки
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="📅 Неделя" + (" ✓" if period=='week' else ""), callback_data=f"lb:week:{sort}"),
                        InlineKeyboardButton(text="📅 Месяц" + (" ✓" if period=='month' else ""), callback_data=f"lb:month:{sort}"),
                        InlineKeyboardButton(text="📅 Всё" + (" ✓" if period=='all' else ""), callback_data=f"lb:all:{sort}")
                    ],
                    [
                        InlineKeyboardButton(text="💰 Монеты" + (" ✓" if sort=='coins' else ""), callback_data=f"lb:{period}:coins"),
                        InlineKeyboardButton(text="💵 Сумма" + (" ✓" if sort=='amount' else ""), callback_data=f"lb:{period}:amount"),
                        InlineKeyboardButton(text="✅ Сделки" + (" ✓" if sort=='deals' else ""), callback_data=f"lb:{period}:deals")
                    ]
                ])
                
                if is_callback:
                    await message.edit_text(text, parse_mode='HTML', reply_markup=kb)
                else:
                    await message.answer(text, parse_mode='HTML', reply_markup=kb)
    except Exception as e:
        logging.error(f"Leaderboard: {e}")
        if is_callback:
            await message_or_callback.answer("❌ Ошибка", show_alert=True)
        else:
            await message.answer("❌ Ошибка")

# Callback для кнопок лидерборда
@crm_router.callback_query(F.data.startswith("lb:"))
async def leaderboard_callback(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    period = parts[1]
    sort = parts[2]
    await show_leaderboard(callback, period=period, sort=sort)
    await callback.answer()

# === Просмотр лида ===
@crm_router.callback_query(F.data.startswith("vld:"))
async def view_lead(callback: types.CallbackQuery):
    lead_id = int(callback.data.split(":")[1])
    company_id = callback.bot.company_id
    lead = await get_lead_details(company_id, lead_id)
    # Загружаем события лида
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}/events') as resp:
                if resp.status == 200:
                    from datetime import datetime
                    events = await resp.json()
                    now = datetime.now()
                    future = [e for e in events if datetime.fromisoformat(e['scheduled_at'].replace('Z', '+00:00')) > now]
                    lead['events'] = sorted(future, key=lambda x: x['scheduled_at'])[:3]
    except Exception as e:
        logging.error(f"Load events error: {e}")
        lead['events'] = []
    if not lead:
        await callback.answer("❌ Не найден", show_alert=True)
        return
    statuses = await get_statuses(company_id)
    logging.info(f"[EVENTS DEBUG] lead_id={lead_id}, events in lead: {lead.get('events', 'KEY NOT FOUND')}")
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
async def change_status(callback: types.CallbackQuery, state: FSMContext):
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
                    
                    # Если требуется ввод суммы (статус "Завершён")
                    if result.get('requires_amount'):
                        await state.set_state(CRMStates.waiting_for_deal_amount)
                        await state.update_data(
                            deal_lead_id=lead_id,
                            deal_id=result.get('deal_id'),
                            deal_currency=result.get('currency', 'KZT')
                        )
                        currency = result.get('currency', 'KZT')
                        await callback.message.answer(f"💰 Введите сумму сделки ({currency}):")
                        await callback.answer(f"✅ {name}" + (f" +{coins}💰" if coins > 0 else ""))
                        return
                    
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

# === Новый лид - показать полный отчет ===
@crm_router.callback_query(F.data.startswith("new_lead:"))
async def new_lead_callback(callback: types.CallbackQuery):
    """Show full AI report when manager clicks new lead notification"""
    lead_id = int(callback.data.split(":")[1])
    company_id = callback.bot.company_id
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}/full_report') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Форматировать как в email
                    text = f"🆕 <b>Новый лид от BizDNAi</b>\n\n"
                    text += f"👤 <b>Имя:</b> {data['name']}\n"
                    text += f"📞 <b>Телефон:</b> {data['phone']}\n\n"
                    
                    if data.get('temperature'):
                        text += f"🌡 <b>Температура:</b> {data['temperature']}\n\n"
                    
                    if data.get('ai_summary'):
                        text += f"🤖 <b>Анализ AI:</b>\n{data['ai_summary'][:2000]}\n\n"
                    
                    # История диалога
                    if data.get('conversation_history'):
                        text += "💬 <b>История диалога:</b>\n"
                        for msg in data['conversation_history'][-10:]:
                            sender_icon = "🧑" if msg['sender'] == 'user' else "🤖"
                            text += f"{sender_icon} {msg['text'][:100]}\n\n"
                    
                    kb = InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="📋 Открыть карточку", callback_data=f"vld:{lead_id}")
                    ]])
                    
                    # Разбить на куски если длинное
                    if len(text) > 4000:
                        await callback.message.edit_text(text[:4000], parse_mode='HTML')
                        await callback.message.answer(text[4000:8000], parse_mode='HTML', reply_markup=kb)
                    else:
                        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=kb)
                    await callback.answer()
                else:
                    await callback.answer("❌ Ошибка загрузки", show_alert=True)
    except Exception as e:
        logging.error(f"New lead callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# === Ввод суммы сделки ===
@crm_router.message(CRMStates.waiting_for_deal_amount)
async def process_deal_amount(message: types.Message, state: FSMContext):
    amount_text = message.text.replace(' ', '').replace(',', '.')
    try:
        amount = float(amount_text)
        if amount <= 0:
            await message.answer("❌ Сумма должна быть положительной")
            return
    except ValueError:
        await message.answer("❌ Введите число. Например: 150000")
        return
    
    data = await state.get_data()
    lead_id = data['deal_lead_id']
    deal_id = data['deal_id']
    currency = data['deal_currency']
    company_id = message.bot.company_id
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}/deal/{deal_id}',
                json={'amount': amount, 'manager_id': message.from_user.id}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    deal_num = result.get('deal_number', 1)
                    formatted = f"{amount:,.0f}".replace(',', ' ')
                    await message.answer(f"✅ Сумма: {formatted} {currency}")
                    
                    # Сохранить данные и запросить номер документа
                    await state.update_data(deal_amount=amount, deal_number=deal_num, deal_result=result)
                    await message.answer("📄 Введите номер документа оплаты:")
                    await state.set_state(CRMStates.waiting_for_doc_number)
                    return
                    
                    # (уведомление админу перенесено в waiting_for_payment_date)
                    if False and result.get('notify_admin'):
                        try:
                            admin_id = message.bot.admin_chat_id
                            deal_id = result.get('deal_id')
                            client = result.get('client_name', 'Клиент')
                            mgr = result.get('manager_name', 'Менеджер')
                            lead_id_val = result.get('lead_id', lead_id)
                            
                            notify_text = (
                                f"💰 <b>Новая сделка!</b>\n\n"
                                f"Лид #{lead_id_val}\n"
                                f"👤 Клиент: {client}\n"
                                f"👨‍💼 Менеджер: {mgr}\n"
                                f"💵 Сумма: {formatted} {currency}"
                            )
                            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                            kb = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_deal:{deal_id}")]
                            ])
                            await message.bot.send_message(admin_id, notify_text, parse_mode='HTML', reply_markup=kb)
                        except Exception as e:
                            logging.error(f"Admin notify: {e}")
                else:
                    await message.answer("❌ Ошибка сохранения")
    except Exception as e:
        logging.error(f"Deal save: {e}")
        await message.answer("❌ Ошибка")
    
    await state.clear()




@crm_router.message(CRMStates.waiting_for_doc_number)
async def process_doc_number(message: types.Message, state: FSMContext):
    """Process document number input"""
    doc_number = message.text.strip()
    if not doc_number:
        await message.answer("❌ Введите номер документа")
        return
    
    await state.update_data(payment_doc_number=doc_number)
    await message.answer("📅 Введите дату оплаты (ДД.ММ.ГГГГ):")
    await state.set_state(CRMStates.waiting_for_payment_date)


@crm_router.message(CRMStates.waiting_for_payment_date)
async def process_payment_date(message: types.Message, state: FSMContext):
    """Process payment date input"""
    date_str = message.text.strip()
    
    # Валидация формата ДД.ММ.ГГГГ
    try:
        from datetime import datetime
        payment_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        payment_date_db = payment_date.strftime("%Y-%m-%d")  # Для БД
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте ДД.ММ.ГГГГ (например: 18.01.2026)")
        return
    
    data = await state.get_data()
    company_id = message.bot.company_id
    deal_id = data.get('deal_id')
    doc_number = data.get('payment_doc_number', '')
    deal_result = data.get('deal_result', {})
    deal_num = data.get('deal_number', 1)
    deal_amount = data.get('deal_amount', 0)
    currency = data.get('deal_currency', 'KZT')
    
    # Сохранить документ и дату в БД
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f'{API_BASE_URL}/crm/{company_id}/deals/{deal_id}/document',
                json={'payment_doc_number': doc_number, 'payment_date': payment_date_db}
            ) as resp:
                if resp.status == 200:
                    formatted = f"{deal_amount:,.0f}".replace(',', ' ')
                    await message.answer(f"✅ Сделка {deal_num}: {formatted} {currency}\n📄 Документ: {doc_number}\n📅 Дата: {date_str}")
                    
                    # Отправить уведомление админу
                    try:
                        admin_id = message.bot.admin_chat_id
                        client = deal_result.get('client_name', 'Клиент')
                        mgr = deal_result.get('manager_name', 'Менеджер')
                        lead_id = deal_result.get('lead_id', 0)
                        
                        notify_text = (
                            f"💰 <b>Новая сделка!</b>\n\n"
                            f"Лид #{lead_id}\n"
                            f"👤 Клиент: {client}\n"
                            f"👨‍💼 Менеджер: {mgr}\n"
                            f"💵 Сумма: {formatted} {currency}\n"
                            f"📄 Документ: {doc_number}\n"
                            f"📅 Дата оплаты: {date_str}"
                        )
                        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                        kb = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_deal:{deal_id}")]
                        ])
                        await message.bot.send_message(admin_id, notify_text, parse_mode='HTML', reply_markup=kb)
                    except Exception as e:
                        logging.error(f"Admin notify: {e}")
                else:
                    await message.answer("❌ Ошибка сохранения документа")
    except Exception as e:
        logging.error(f"Save doc: {e}")
        await message.answer("❌ Ошибка")
    
    await state.clear()

# === Смотреть Диалог ===
@crm_router.callback_query(F.data.startswith("dialog:"))
async def view_dialog_callback(callback: types.CallbackQuery):
    lead_id = int(callback.data.split(":")[1])
    company_id = callback.bot.company_id
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}/full_report') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    text = f"📜 <b>Диалог с {data.get('name', 'клиентом')}</b>\n\n"
                    
                    if data.get('ai_summary'):
                        text += f"🤖 <b>AI-анализ:</b>\n{data['ai_summary'][:2000]}\n\n"
                    
                    if data.get('conversation_history'):
                        text += "💬 <b>История:</b>\n"
                        for msg in data['conversation_history'][-15:]:
                            sender_icon = "🧑" if msg.get('sender') == 'user' else "🤖"
                            text += f"{sender_icon} {msg.get('text', '')[:150]}\n\n"
                    
                    kb = InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="⬅️ Назад к карточке", callback_data=f"vld:{lead_id}")
                    ]])
                    
                    if len(text) > 4000:
                        text = text[:4000] + "..."
                    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=kb)
                    await callback.answer()
                else:
                    await callback.answer("❌ Ошибка загрузки", show_alert=True)
    except Exception as e:
        logging.error(f"Dialog: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

# === Назад ===
@crm_router.callback_query(F.data == "back_leads")
async def back(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()

# === СОБЫТИЯ И НАПОМИНАНИЯ ===

EVENT_TYPES = {
    'call': '📞 Звонок',
    'meeting': '🤝 Встреча',
    'email': '📧 Письмо',
    'task': '📋 Задача'
}

@crm_router.callback_query(F.data.startswith("event:"))
async def start_create_event(callback: types.CallbackQuery, state: FSMContext):
    """Start creating event for lead"""
    lead_id = callback.data.split(":")[1]
    await state.update_data(event_lead_id=lead_id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Звонок", callback_data="etype:call")],
        [InlineKeyboardButton(text="🤝 Встреча", callback_data="etype:meeting")],
        [InlineKeyboardButton(text="📧 Письмо", callback_data="etype:email")],
        [InlineKeyboardButton(text="📋 Задача", callback_data="etype:task")]
    ])
    await callback.message.edit_text("📅 Выберите тип события:", reply_markup=kb)
    await state.set_state(EventStates.selecting_type)


@crm_router.callback_query(F.data.startswith("etype:"))
async def select_event_type(callback: types.CallbackQuery, state: FSMContext):
    """Event type selected - show calendar"""
    event_type = callback.data.split(":")[1]
    await state.update_data(event_type=event_type)
    kb = get_calendar()
    await callback.message.edit_text("📅 Выберите дату:", reply_markup=kb)
    await state.set_state(EventStates.selecting_date)


@crm_router.callback_query(F.data == "cal_ignore")
async def calendar_ignore(callback: types.CallbackQuery):
    """Ignore non-clickable calendar buttons"""
    await callback.answer()


@crm_router.callback_query(F.data.startswith("cal_m:"))
async def calendar_nav_month(callback: types.CallbackQuery):
    """Navigate calendar by month"""
    _, year, month = callback.data.split(":")
    kb = get_calendar(int(year), int(month))
    await callback.message.edit_reply_markup(reply_markup=kb)


@crm_router.callback_query(F.data.startswith("cal_y:"))
async def calendar_nav_year(callback: types.CallbackQuery):
    """Navigate calendar by year"""
    _, year, month = callback.data.split(":")
    kb = get_calendar(int(year), int(month))
    await callback.message.edit_reply_markup(reply_markup=kb)


@crm_router.callback_query(F.data.startswith("cal_day:"))
async def calendar_day_selected(callback: types.CallbackQuery, state: FSMContext):
    """Day selected - show hour picker"""
    date_str = callback.data.split(":")[1]  # 2026-01-19
    await state.update_data(selected_date=date_str)
    data = await state.get_data()
    event_type = EVENT_TYPES.get(data.get('event_type', ''), '📋 Событие')
    # Формат: 19.01.2026
    formatted_date = f"{date_str[8:10]}.{date_str[5:7]}.{date_str[:4]}"
    kb = get_hour_picker(12)
    await callback.message.edit_text(f"{event_type}: {formatted_date}\n\n⏰ Выберите час:", reply_markup=kb)
    await state.set_state(EventStates.selecting_hour)


@crm_router.callback_query(F.data.startswith("cal_h:"))
async def hour_scroll(callback: types.CallbackQuery, state: FSMContext):
    """Scroll hours"""
    hour = int(callback.data.split(":")[1])
    data = await state.get_data()
    event_type = EVENT_TYPES.get(data.get('event_type', ''), '📋 Событие')
    date_str = data.get('selected_date', '')
    formatted_date = f"{date_str[8:10]}.{date_str[5:7]}.{date_str[:4]}" if date_str else ''
    kb = get_hour_picker(hour)
    await callback.message.edit_text(f"{event_type}: {formatted_date}\n\n⏰ Выберите час:", reply_markup=kb)


@crm_router.callback_query(F.data.startswith("cal_hok:"))
async def hour_confirmed(callback: types.CallbackQuery, state: FSMContext):
    """Hour confirmed - show minute picker"""
    hour = int(callback.data.split(":")[1])
    await state.update_data(selected_hour=hour)
    data = await state.get_data()
    event_type = EVENT_TYPES.get(data.get('event_type', ''), '📋 Событие')
    date_str = data.get('selected_date', '')
    formatted_date = f"{date_str[8:10]}.{date_str[5:7]}.{date_str[:4]}" if date_str else ''
    kb = get_minute_picker(0)
    await callback.message.edit_text(f"{event_type}: {formatted_date} в {hour:02d}:__\n\n⏰ Выберите минуты:", reply_markup=kb)
    await state.set_state(EventStates.selecting_minute)


@crm_router.callback_query(F.data.startswith("cal_min:"))
async def minute_scroll(callback: types.CallbackQuery, state: FSMContext):
    """Scroll minutes"""
    minute = int(callback.data.split(":")[1])
    data = await state.get_data()
    event_type = EVENT_TYPES.get(data.get('event_type', ''), '📋 Событие')
    date_str = data.get('selected_date', '')
    formatted_date = f"{date_str[8:10]}.{date_str[5:7]}.{date_str[:4]}" if date_str else ''
    hour = data.get('selected_hour', 0)
    kb = get_minute_picker(minute)
    await callback.message.edit_text(f"{event_type}: {formatted_date} в {hour:02d}:__\n\n⏰ Выберите минуты:", reply_markup=kb)


@crm_router.callback_query(F.data.startswith("cal_minok:"))
async def minute_confirmed(callback: types.CallbackQuery, state: FSMContext):
    """Minute confirmed - show description options or update event if editing"""
    minute = int(callback.data.split(":")[1])
    data = await state.get_data()
    scheduled_at = f"{data['selected_date']}T{data['selected_hour']:02d}:{minute:02d}:00"
    await state.update_data(scheduled_at=scheduled_at, selected_minute=minute)
    
    # Если редактируем существующее событие
    if data.get('is_editing') and data.get('editing_event_id'):
        event_id = data.get('editing_event_id')
        company_id = getattr(callback.bot, 'company_id', 1)
        async with aiohttp.ClientSession() as session:
            await session.patch(f'{API_BASE_URL}/crm/{company_id}/events/{event_id}', json={'scheduled_at': scheduled_at})
        await state.clear()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_event:{event_id}"),
             InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_event:{event_id}")],
            [InlineKeyboardButton(text="✅ Сохранить", callback_data=f"save_event:{event_id}")]
        ])
        await callback.message.edit_text(f"✅ Дата/время изменено!", reply_markup=kb)
        await callback.answer()
        return
    
    event_type = EVENT_TYPES.get(data.get('event_type', ''), '📋 Событие')
    date_str = data.get('selected_date', '')
    formatted_date = f"{date_str[8:10]}.{date_str[5:7]}.{date_str[:4]}" if date_str else ''
    hour = data.get('selected_hour', 0)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Добавить описание", callback_data="edesc:add")],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="edesc:skip")]
    ])
    await callback.message.edit_text(f"{event_type}: {formatted_date} в {hour:02d}:{minute:02d}\n\n📝 Описание:", reply_markup=kb)
    await state.set_state(EventStates.entering_description)


@crm_router.callback_query(F.data == "edesc:skip")
async def skip_description(callback: types.CallbackQuery, state: FSMContext):
    """Skip description - show reminder options"""
    await state.update_data(event_description='')
    data = await state.get_data()
    event_type = EVENT_TYPES.get(data.get('event_type', ''), '📋 Событие')
    date_str = data.get('selected_date', '')
    formatted_date = f"{date_str[8:10]}.{date_str[5:7]}.{date_str[:4]}" if date_str else ''
    hour = data.get('selected_hour', 0)
    minute = data.get('selected_minute', 0)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="15 мин", callback_data="eremind:15"),
            InlineKeyboardButton(text="30 мин", callback_data="eremind:30"),
        ],
        [
            InlineKeyboardButton(text="45 мин", callback_data="eremind:45"),
            InlineKeyboardButton(text="60 мин", callback_data="eremind:60"),
        ]
    ])
    await callback.message.edit_text(f"{event_type}: {formatted_date} в {hour:02d}:{minute:02d}\n\n⏰ Напомнить за:", reply_markup=kb)
    await state.set_state(EventStates.selecting_reminder)


@crm_router.callback_query(F.data == "edesc:add")
async def add_description(callback: types.CallbackQuery, state: FSMContext):
    """User wants to add description"""
    await callback.message.edit_text("📝 Введите описание:")
    await state.set_state(EventStates.entering_description)


# Old datetime handler removed - using calendar now


@crm_router.message(EventStates.entering_description)
async def process_event_description(message: types.Message, state: FSMContext):
    """Process description and show reminder options"""
    desc = message.text.strip() if message.text.strip() != '.' else ''
    await state.update_data(event_description=desc)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="15 мин", callback_data="eremind:15"),
            InlineKeyboardButton(text="30 мин", callback_data="eremind:30"),
        ],
        [
            InlineKeyboardButton(text="45 мин", callback_data="eremind:45"),
            InlineKeyboardButton(text="60 мин", callback_data="eremind:60"),
        ]
    ])
    await message.answer("⏰ Напомнить за:", reply_markup=kb)
    await state.set_state(EventStates.selecting_reminder)


@crm_router.callback_query(F.data.startswith("eremind:"))
async def save_event(callback: types.CallbackQuery, state: FSMContext):
    """Save event to database"""
    remind = int(callback.data.split(":")[1])
    data = await state.get_data()
    company_id = callback.bot.company_id
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{API_BASE_URL}/crm/{company_id}/events',
                json={
                    'lead_id': int(data['event_lead_id']) if data.get('event_lead_id') else None,
                    'user_id': callback.from_user.id,
                    'event_type': data['event_type'],
                    'description': data.get('event_description', ''),
                    'scheduled_at': data['scheduled_at'],
                    'remind_before_minutes': remind
                }
            ) as resp:
                if resp.status == 200:
                    event_type = EVENT_TYPES.get(data['event_type'], data['event_type'])
                    result = await resp.json()
                    event_id = result.get('id', 0)
                    
                    # Если из меню — спрашиваем про повторение
                    if data.get('from_menu'):
                        await state.update_data(created_event_id=event_id)
                        kb = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🔁 Ежедневно", callback_data=f"recur:daily:{event_id}")],
                            [InlineKeyboardButton(text="🔁 Еженедельно", callback_data=f"recur:weekly:{event_id}")],
                            [InlineKeyboardButton(text="🔁 Ежемесячно", callback_data=f"recur:monthly:{event_id}")],
                            [InlineKeyboardButton(text="❌ Не повторять", callback_data=f"recur:none:{event_id}")]
                        ])
                        await callback.message.edit_text(
                            f"✅ Событие создано!\n\n"
                            f"{event_type}\n"
                            f"📅 {data.get('selected_date', '')[8:10]}.{data.get('selected_date', '')[5:7]}.{data.get('selected_date', '')[:4]} "
                            f"{data.get('selected_hour', 0):02d}:{data.get('selected_minute', 0):02d}\n"
                            f"⏰ Напоминание за {remind} мин\n\n"
                            f"🔁 Повторять событие?",
                            reply_markup=kb
                        )
                        await state.clear()
                        return
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_event:{event_id}"),
                         InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_event:{event_id}")],
                        [InlineKeyboardButton(text="✅ Сохранить", callback_data=f"save_event:{event_id}")]
                    ])
                    await callback.message.edit_text(
                        f"✅ Событие создано!\n\n"
                        f"{event_type}\n"
                        f"📅 {data.get('selected_date', '')[8:10]}.{data.get('selected_date', '')[5:7]}.{data.get('selected_date', '')[:4]} {data.get('selected_hour', 0):02d}:{data.get('selected_minute', 0):02d}\n"
                        f"⏰ Напоминание за {remind} мин",
                        reply_markup=kb
                    )
                else:
                    await callback.message.edit_text("❌ Ошибка создания события")
    except Exception as e:
        logging.error(f"Event create error: {e}")
        await callback.message.edit_text("❌ Ошибка")
    
    await state.clear()


@crm_router.callback_query(F.data.startswith("edone:"))
async def event_done(callback: types.CallbackQuery):
    """Mark event as done"""
    event_id = callback.data.split(":")[1]
    company_id = callback.bot.company_id
    
    async with aiohttp.ClientSession() as session:
        await session.patch(
            f'{API_BASE_URL}/crm/{company_id}/events/{event_id}',
            json={'status': 'done'}
        )
    await callback.message.edit_text("✅ Событие выполнено!")


@crm_router.callback_query(F.data.startswith("edelay:"))
async def event_delay(callback: types.CallbackQuery):
    """Delay event by 15 minutes"""
    parts = callback.data.split(":")
    event_id = parts[1]
    current_time = parts[2] if len(parts) > 2 else None
    company_id = callback.bot.company_id
    
    from datetime import datetime, timedelta
    if current_time:
        new_time = datetime.fromisoformat(current_time) + timedelta(minutes=15)
    else:
        new_time = datetime.now() + timedelta(minutes=15)
    
    async with aiohttp.ClientSession() as session:
        await session.patch(
            f'{API_BASE_URL}/crm/{company_id}/events/{event_id}',
            json={'scheduled_at': new_time.isoformat()}
        )
    await callback.message.edit_text(f"⏰ Отложено на 15 минут (до {new_time.strftime('%H:%M')})")


@crm_router.callback_query(F.data.startswith("ecancel:"))
async def event_cancel(callback: types.CallbackQuery):
    """Cancel event"""
    event_id = callback.data.split(":")[1]
    company_id = callback.bot.company_id
    
    async with aiohttp.ClientSession() as session:
        await session.patch(
            f'{API_BASE_URL}/crm/{company_id}/events/{event_id}',
            json={'status': 'cancelled'}
        )
    await callback.message.edit_text("❌ Событие отменено")

# === РЕДАКТИРОВАНИЕ И УДАЛЕНИЕ СОБЫТИЙ ===

@crm_router.callback_query(F.data.startswith("ev_edit:"))
async def edit_event(callback: types.CallbackQuery, state: FSMContext):
    """Edit event - restart creation flow"""
    event_id = callback.data.split(":")[1]
    company_id = callback.bot.company_id
    
    # Получить событие
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_BASE_URL}/crm/{company_id}/events?user_id={callback.from_user.id}') as resp:
            events = await resp.json() if resp.status == 200 else []
    
    event = next((e for e in events if str(e.get('id')) == event_id), None)
    if not event:
        await callback.answer("Событие не найдено", show_alert=True)
        return
    
    # Удалить старое событие
    async with aiohttp.ClientSession() as session:
        await session.patch(f'{API_BASE_URL}/crm/{company_id}/events/{event_id}', json={'status': 'cancelled'})
    
    # Начать создание нового
    await state.update_data(event_lead_id=event.get('lead_id'))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Звонок", callback_data="etype:call")],
        [InlineKeyboardButton(text="🤝 Встреча", callback_data="etype:meeting")],
        [InlineKeyboardButton(text="📧 Письмо", callback_data="etype:email")],
        [InlineKeyboardButton(text="📋 Задача", callback_data="etype:task")]
    ])
    await callback.message.edit_text("✏️ Редактирование события\n\n📅 Выберите тип:", reply_markup=kb)
    await state.set_state(EventStates.selecting_type)


@crm_router.callback_query(F.data.startswith("ev_del:"))
async def delete_event(callback: types.CallbackQuery):
    """Delete event"""
    event_id = callback.data.split(":")[1]
    company_id = callback.bot.company_id
    
    async with aiohttp.ClientSession() as session:
        await session.patch(f'{API_BASE_URL}/crm/{company_id}/events/{event_id}', json={'status': 'cancelled'})
    
    await callback.answer("🗑 Событие удалено", show_alert=True)
    # Обновить список
    await callback.message.delete()




# ========== EVENT EDIT/DELETE/SAVE HANDLERS ==========

@crm_router.callback_query(F.data.startswith("edit_event:"))
async def edit_event_menu(callback: types.CallbackQuery):
    """Меню редактирования события"""
    event_id = int(callback.data.split(":")[1])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Тип", callback_data=f"eedit_type:{event_id}")],
        [InlineKeyboardButton(text="📅 Дата/время", callback_data=f"eedit_dt:{event_id}")],
        [InlineKeyboardButton(text="📝 Описание", callback_data=f"eedit_desc:{event_id}")],
        [InlineKeyboardButton(text="⏰ Напоминание", callback_data=f"eedit_rem:{event_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_event:{event_id}")]
    ])
    await callback.message.edit_text("✏️ Что изменить?", reply_markup=kb)
    await callback.answer()

@crm_router.callback_query(F.data.startswith("back_event:"))
async def back_to_event(callback: types.CallbackQuery):
    """Назад к событию"""
    event_id = int(callback.data.split(":")[1])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_event:{event_id}"),
         InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_event:{event_id}")],
        [InlineKeyboardButton(text="✅ Сохранить", callback_data=f"save_event:{event_id}")]
    ])
    await callback.message.edit_text(f"📅 Событие #{event_id}", reply_markup=kb)
    await callback.answer()

@crm_router.callback_query(F.data.startswith("eedit_type:"))
async def edit_event_type(callback: types.CallbackQuery):
    """Изменить тип события"""
    event_id = int(callback.data.split(":")[1])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Звонок", callback_data=f"eset_type:call:{event_id}")],
        [InlineKeyboardButton(text="🤝 Встреча", callback_data=f"eset_type:meeting:{event_id}")],
        [InlineKeyboardButton(text="📧 Письмо", callback_data=f"eset_type:email:{event_id}")],
        [InlineKeyboardButton(text="📋 Задача", callback_data=f"eset_type:task:{event_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_event:{event_id}")]
    ])
    await callback.message.edit_text("🎯 Выберите тип:", reply_markup=kb)
    await callback.answer()

@crm_router.callback_query(F.data.startswith("eset_type:"))
async def set_event_type(callback: types.CallbackQuery):
    """Сохранить тип события"""
    parts = callback.data.split(":")
    new_type, event_id = parts[1], int(parts[2])
    company_id = getattr(callback.bot, 'company_id', 1)
    async with aiohttp.ClientSession() as session:
        await session.patch(f'{API_BASE_URL}/crm/{company_id}/events/{event_id}', json={'event_type': new_type})
    types_map = {'call': '📞 Звонок', 'meeting': '🤝 Встреча', 'email': '📧 Письмо', 'task': '📋 Задача'}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_event:{event_id}"),
         InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_event:{event_id}")],
        [InlineKeyboardButton(text="✅ Сохранить", callback_data=f"save_event:{event_id}")]
    ])
    await callback.message.edit_text(f"✅ Тип изменён на {types_map.get(new_type, new_type)}!", reply_markup=kb)
    await callback.answer()

@crm_router.callback_query(F.data.startswith("eedit_dt:"))
async def edit_event_dt(callback: types.CallbackQuery, state: FSMContext):
    """Изменить дату/время через календарь"""
    event_id = int(callback.data.split(":")[1])
    await state.set_state(EventStates.selecting_date)
    await state.update_data(editing_event_id=event_id, is_editing=True)
    kb = get_calendar()
    await callback.message.edit_text("📅 Выберите новую дату:", reply_markup=kb)
    await callback.answer()

@crm_router.callback_query(F.data.startswith("eedit_desc:"))
async def edit_event_desc(callback: types.CallbackQuery, state: FSMContext):
    """Изменить описание"""
    event_id = int(callback.data.split(":")[1])
    await state.set_state(EventStates.editing_description)
    await state.update_data(editing_event_id=event_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Сохранить пустым", callback_data=f"edesc_empty:{event_id}")]
    ])
    await callback.message.edit_text("📝 Введите новое описание:", reply_markup=kb)
    await callback.answer()

@crm_router.message(EventStates.editing_description)
async def process_desc_edit(message: types.Message, state: FSMContext):
    """Сохранить описание"""
    data = await state.get_data()
    event_id = data.get('editing_event_id')
    company_id = getattr(message.bot, 'company_id', 1)
    async with aiohttp.ClientSession() as session:
        await session.patch(f'{API_BASE_URL}/crm/{company_id}/events/{event_id}', json={'description': message.text or ''})
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_event:{event_id}"),
         InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_event:{event_id}")],
        [InlineKeyboardButton(text="✅ Сохранить", callback_data=f"save_event:{event_id}")]
    ])
    await message.answer("✅ Описание обновлено!", reply_markup=kb)
    await state.clear()

@crm_router.callback_query(F.data.startswith("edesc_empty:"))
async def save_empty_desc(callback: types.CallbackQuery, state: FSMContext):
    """Сохранить пустое описание"""
    event_id = int(callback.data.split(":")[1])
    company_id = getattr(callback.bot, 'company_id', 1)
    async with aiohttp.ClientSession() as session:
        await session.patch(f'{API_BASE_URL}/crm/{company_id}/events/{event_id}', json={'description': ''})
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_event:{event_id}"),
         InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_event:{event_id}")],
        [InlineKeyboardButton(text="✅ Сохранить", callback_data=f"save_event:{event_id}")]
    ])
    await callback.message.edit_text("✅ Описание очищено!", reply_markup=kb)
    await callback.answer()

@crm_router.callback_query(F.data.startswith("eedit_rem:"))
async def edit_event_rem(callback: types.CallbackQuery):
    """Изменить напоминание"""
    event_id = int(callback.data.split(":")[1])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="15м", callback_data=f"eset_rem:15:{event_id}"),
         InlineKeyboardButton(text="30м", callback_data=f"eset_rem:30:{event_id}"),
         InlineKeyboardButton(text="60м", callback_data=f"eset_rem:60:{event_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_event:{event_id}")]
    ])
    await callback.message.edit_text("⏰ За сколько напомнить?", reply_markup=kb)
    await callback.answer()

@crm_router.callback_query(F.data.startswith("eset_rem:"))
async def set_event_rem(callback: types.CallbackQuery):
    """Сохранить напоминание"""
    parts = callback.data.split(":")
    mins, event_id = int(parts[1]), int(parts[2])
    company_id = getattr(callback.bot, 'company_id', 1)
    async with aiohttp.ClientSession() as session:
        await session.patch(f'{API_BASE_URL}/crm/{company_id}/events/{event_id}', json={'remind_before_minutes': mins})
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_event:{event_id}"),
         InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_event:{event_id}")],
        [InlineKeyboardButton(text="✅ Сохранить", callback_data=f"save_event:{event_id}")]
    ])
    await callback.message.edit_text(f"✅ Напоминание: за {mins} мин", reply_markup=kb)
    await callback.answer()

@crm_router.callback_query(F.data.startswith("del_event:"))
async def del_event_confirm(callback: types.CallbackQuery):
    """Подтверждение удаления"""
    event_id = int(callback.data.split(":")[1])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"del_yes:{event_id}"),
         InlineKeyboardButton(text="❌ Нет", callback_data=f"back_event:{event_id}")]
    ])
    await callback.message.edit_text(f"🗑 Удалить событие #{event_id}?", reply_markup=kb)
    await callback.answer()

@crm_router.callback_query(F.data.startswith("del_yes:"))
async def del_event_yes(callback: types.CallbackQuery):
    """Удалить событие"""
    event_id = int(callback.data.split(":")[1])
    company_id = getattr(callback.bot, 'company_id', 1)
    async with aiohttp.ClientSession() as session:
        await session.delete(f'{API_BASE_URL}/crm/{company_id}/events/{event_id}')
    await callback.message.edit_text(f"✅ Событие #{event_id} удалено!")
    await callback.answer()

@crm_router.callback_query(F.data.startswith("save_event:"))
async def save_event_done(callback: types.CallbackQuery):
    """Сохранить событие - завершение"""
    event_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(f"✅ Событие #{event_id} сохранено!")
    await callback.answer()




# ========== МЕНЮ СОБЫТИЯ (v2) ==========

@crm_router.message(F.text == "📅 События")
async def show_events_menu(message: types.Message):
    """Показать меню событий - компактно"""
    await show_events_list(message, offset=0, filter_type=None, filter_period=None)


async def show_events_list(msg_or_cb, offset=0, filter_type=None, filter_period=None):
    """Показать список событий с фильтрами"""
    if hasattr(msg_or_cb, 'bot'):
        company_id = getattr(msg_or_cb.bot, 'company_id', 1)
        user_id = msg_or_cb.from_user.id
    else:
        company_id = getattr(msg_or_cb.message.bot, 'company_id', 1)
        user_id = msg_or_cb.from_user.id
    
    # Получаем события
    url = f'{API_BASE_URL}/crm/{company_id}/events?user_id={user_id}&offset={offset}&limit=50'
    if filter_type:
        url += f'&event_type={filter_type}'
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            events = await resp.json() if resp.status == 200 else []
    
    # Фильтр по периоду (клиентская сторона пока)
    from datetime import datetime, timedelta
    if filter_period == 'today':
        today = datetime.now().date().isoformat()
        events = [e for e in events if e.get('scheduled_at', '')[:10] == today]
    elif filter_period == 'week':
        today = datetime.now().date().isoformat()
        week_end = (datetime.now() + timedelta(days=6)).date().isoformat()
        events = [e for e in events if today <= e.get('scheduled_at', '')[:10] <= week_end]
    
    type_icons = {'call': '📞', 'meeting': '🤝', 'email': '📧', 'task': '📋'}
    buttons = []
    
    # Каждое событие — одна кнопка
    for ev in events[:5]:
        eid = ev.get('id')
        icon = type_icons.get(ev.get('event_type', ''), '📅')
        sched = ev.get('scheduled_at', '')[:16].replace('T', ' ') if ev.get('scheduled_at') else ''
        client = (ev.get('client_name') or 'Без лида')[:15]
        desc = (ev.get('description') or '')[:15]
        # Формат: 20.01.2026 Клиент + 🔁 для recurring + 🏷️ для без лида
        date_part = sched[:10] if sched else ""
        if date_part:
            date_formatted = f"{date_part[8:10]}.{date_part[5:7]}.{date_part[:4]}"
        else:
            date_formatted = ""
        
        # Иконка повторения
        recur_icon = "🔁" if ev.get('is_recurring') else ""
        
        # Различие с лидом / без лида
        if ev.get('lead_id'):
            client_text = f"👤{client[:12]}"
        else:
            client_text = "🏷️Личное"
        
        btn_text = f"{recur_icon}{icon} {date_formatted} {client_text}"
        # Описание не нужно в кнопке
        buttons.append([InlineKeyboardButton(text=btn_text[:40], callback_data=f"view_ev:{eid}")])
    
    # Пагинация
    page = (offset // 5) + 1
    nav_row = [
        InlineKeyboardButton(text="◀️", callback_data=f"evp:{max(0,offset-5)}:{filter_type or ''}:{filter_period or ''}"),
        InlineKeyboardButton(text=f"стр.{page}", callback_data="ev_ign"),
        InlineKeyboardButton(text="▶️", callback_data=f"evp:{offset+5}:{filter_type or ''}:{filter_period or ''}")
    ]
    buttons.append(nav_row)
    
    # Фильтры по типу + recurring
    type_row = [
        InlineKeyboardButton(text="📞" + ("✓" if filter_type=='call' else ""), callback_data=f"evf:call:{filter_period or ''}"),
        InlineKeyboardButton(text="🤝" + ("✓" if filter_type=='meeting' else ""), callback_data=f"evf:meeting:{filter_period or ''}"),
        InlineKeyboardButton(text="📧" + ("✓" if filter_type=='email' else ""), callback_data=f"evf:email:{filter_period or ''}"),
        InlineKeyboardButton(text="📋" + ("✓" if filter_type=='task' else ""), callback_data=f"evf:task:{filter_period or ''}"),
        InlineKeyboardButton(text="🔁" + ("✓" if filter_type=='recurring' else ""), callback_data=f"evf:recurring:{filter_period or ''}"),
        InlineKeyboardButton(text="Все", callback_data=f"evf::{filter_period or ''}")
    ]
    buttons.append(type_row)
    
    # Фильтры по периоду
    period_row = [
        InlineKeyboardButton(text="Сегодня" + ("✓" if filter_period=='today' else ""), callback_data=f"evd:today:{filter_type or ''}"),
        InlineKeyboardButton(text="Неделя" + ("✓" if filter_period=='week' else ""), callback_data=f"evd:week:{filter_type or ''}"),
        InlineKeyboardButton(text="Все" + ("✓" if not filter_period else ""), callback_data=f"evd::{filter_type or ''}")
    ]
    buttons.append(period_row)
    
    # Создать событие
    buttons.append([
        InlineKeyboardButton(text="➕ Создать событие", callback_data="create_ev_menu"),
        InlineKeyboardButton(text="📜 История", callback_data="ev_history:0")
    ])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = "<b>📅 Мои события</b>" if events else "<b>📅 Нет событий</b>"
    
    if hasattr(msg_or_cb, 'message'):
        await msg_or_cb.message.edit_text(text, parse_mode='HTML', reply_markup=kb)
    else:
        await msg_or_cb.answer(text, parse_mode='HTML', reply_markup=kb)


@crm_router.callback_query(F.data.startswith("evp:"))
async def events_page(callback: types.CallbackQuery):
    """Пагинация"""
    parts = callback.data.split(":")
    offset = int(parts[1])
    ftype = parts[2] if len(parts) > 2 and parts[2] else None
    fperiod = parts[3] if len(parts) > 3 and parts[3] else None
    await show_events_list(callback, offset, ftype, fperiod)
    await callback.answer()


@crm_router.callback_query(F.data.startswith("evf:"))
async def events_filter_type(callback: types.CallbackQuery):
    """Фильтр по типу"""
    parts = callback.data.split(":")
    ftype = parts[1] if parts[1] else None
    fperiod = parts[2] if len(parts) > 2 and parts[2] else None
    await show_events_list(callback, 0, ftype, fperiod)
    await callback.answer()


@crm_router.callback_query(F.data.startswith("evd:"))
async def events_filter_period(callback: types.CallbackQuery):
    """Фильтр по периоду"""
    parts = callback.data.split(":")
    fperiod = parts[1] if parts[1] else None
    ftype = parts[2] if len(parts) > 2 and parts[2] else None
    await show_events_list(callback, 0, ftype, fperiod)
    await callback.answer()


@crm_router.callback_query(F.data == "ev_ign")
async def ev_ignore(callback: types.CallbackQuery):
    await callback.answer()


@crm_router.callback_query(F.data.startswith("view_ev:"))
async def view_event_detail(callback: types.CallbackQuery):
    """Просмотр события"""
    event_id = int(callback.data.split(":")[1])
    company_id = getattr(callback.bot, 'company_id', 1)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_BASE_URL}/crm/{company_id}/events') as resp:
            events = await resp.json() if resp.status == 200 else []
            ev = next((e for e in events if e.get('id') == event_id), None)
    
    if ev:
        types_map = {'call': '📞 Звонок', 'meeting': '🤝 Встреча', 'email': '📧 Письмо', 'task': '📋 Задача'}
        icon = types_map.get(ev.get('event_type', ''), '📅 Событие')
        sched = ev.get('scheduled_at', '')[:16].replace('T', ' ')
        client = ev.get('client_name') or 'Без лида'
        desc = ev.get('description') or ''
        
        # Формат даты СНГ
        if sched:
            date_formatted = f"{sched[8:10]}.{sched[5:7]}.{sched[:4]} {sched[11:16]}"
        else:
            date_formatted = sched
        
        # Инфо о повторении
        pattern_names = {'daily': 'Ежедневно', 'weekly': 'Еженедельно', 'monthly': 'Ежемесячно'}
        recurring_info = ""
        if ev.get('is_recurring'):
            recurring_info = f"\n🔁 {pattern_names.get(ev.get('recurring_pattern', ''), 'Да')}"
        
        # Различие с/без лида
        if ev.get('lead_id'):
            client_line = f"👤 {client}"
        else:
            client_line = "🏷️ Личное событие"
        
        text = f"<b>📅 Событие #{event_id}</b>\n\n{icon}\n📅 {date_formatted}\n{client_line}{recurring_info}"
        if desc:
            text += f"\n📝 {desc}"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_event:{event_id}"),
             InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_event:{event_id}")],
            [InlineKeyboardButton(text="« Назад", callback_data="back_ev_list")]
        ])
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=kb)
    else:
        await callback.message.edit_text("❌ Событие не найдено")
    await callback.answer()


@crm_router.callback_query(F.data == "back_ev_list")
async def back_events_list(callback: types.CallbackQuery):
    await show_events_list(callback, 0, None, None)
    await callback.answer()


@crm_router.callback_query(F.data.startswith("ev_history:"))
async def show_event_history(callback: types.CallbackQuery):
    """История событий"""
    offset = int(callback.data.split(":")[1])
    company_id = getattr(callback.bot, 'company_id', 1)
    user_id = callback.from_user.id
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_BASE_URL}/crm/{company_id}/events/history?user_id={user_id}&offset={offset}&limit=5') as resp:
            events = await resp.json() if resp.status == 200 else []
    
    type_icons = {'call': '📞', 'meeting': '🤝', 'email': '📧', 'task': '📋'}
    status_icons = {'done': '✅', 'missed': '⚠️', 'cancelled': '❌'}
    
    if events:
        text = "<b>📜 История событий:</b>\n\n"
        for ev in events[:5]:
            icon = type_icons.get(ev.get('event_type', ''), '📅')
            st_icon = status_icons.get(ev.get('status', ''), '❓')
            sched = ev.get('scheduled_at', '')[:10]
            date_fmt = f"{sched[8:10]}.{sched[5:7]}.{sched[:4]}" if sched else ""
            client = (ev.get('client_name') or 'Личное')[:15]
            text += f"{st_icon}{icon} {date_fmt} — {client}\n"
    else:
        text = "<b>📜 История пуста</b>"
    
    page = (offset // 5) + 1
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️", callback_data=f"ev_history:{max(0,offset-5)}"),
         InlineKeyboardButton(text=f"стр.{page}", callback_data="ev_ign"),
         InlineKeyboardButton(text="▶️", callback_data=f"ev_history:{offset+5}")],
        [InlineKeyboardButton(text="« Назад", callback_data="back_ev_list")]
    ])
    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=kb)
    await callback.answer()

async def back_events_list(callback: types.CallbackQuery):
    await show_events_list(callback, 0, None, None)
    await callback.answer()


@crm_router.callback_query(F.data == "create_ev_menu")
async def create_event_from_menu(callback: types.CallbackQuery, state: FSMContext):
    """Создать событие из меню (без лида)"""
    await state.update_data(lead_id=None, from_menu=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Звонок", callback_data="etype:call")],
        [InlineKeyboardButton(text="🤝 Встреча", callback_data="etype:meeting")],
        [InlineKeyboardButton(text="📧 Письмо", callback_data="etype:email")],
        [InlineKeyboardButton(text="📋 Задача", callback_data="etype:task")],
        [InlineKeyboardButton(text="« Отмена", callback_data="back_ev_list")]
    ])
    await callback.message.edit_text("📅 Выберите тип:", reply_markup=kb)
    await state.set_state(EventStates.selecting_type)
    await callback.answer()



# ========== RECURRING EVENTS ==========

@crm_router.callback_query(F.data.startswith("recur:"))
async def set_recurring(callback: types.CallbackQuery):
    """Установить повторение события"""
    parts = callback.data.split(":")
    pattern = parts[1]  # daily/weekly/monthly/none
    event_id = int(parts[2])
    company_id = getattr(callback.bot, 'company_id', 1)
    
    if pattern == "none":
        # Не повторять — показываем кнопки редактирования
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_event:{event_id}"),
             InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_event:{event_id}")],
            [InlineKeyboardButton(text="✅ Сохранить", callback_data=f"save_event:{event_id}")]
        ])
        await callback.message.edit_text(f"✅ Событие #{event_id} создано!", reply_markup=kb)
    else:
        # Устанавливаем повторение в БД
        async with aiohttp.ClientSession() as session:
            await session.patch(
                f'{API_BASE_URL}/crm/{company_id}/events/{event_id}',
                json={'is_recurring': True, 'recurring_pattern': pattern}
            )
        
        pattern_names = {'daily': 'Ежедневно', 'weekly': 'Еженедельно', 'monthly': 'Ежемесячно'}
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_event:{event_id}"),
             InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_event:{event_id}")],
            [InlineKeyboardButton(text="✅ Сохранить", callback_data=f"save_event:{event_id}")]
        ])
        await callback.message.edit_text(
            f"✅ Событие #{event_id} создано!\n🔁 Повтор: {pattern_names.get(pattern)}",
            reply_markup=kb
        )
    await callback.answer()

