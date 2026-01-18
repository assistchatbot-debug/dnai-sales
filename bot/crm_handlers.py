"""CRM Handlers - Manager Lead Cards - v5 FINAL"""
from states import EventStates
from states import EventStates
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
    """Event type selected"""
    event_type = callback.data.split(":")[1]
    await state.update_data(event_type=event_type)
    await callback.message.edit_text("📅 Введите дату и время (ДД.ММ.ГГГГ ЧЧ:ММ):\nНапример: 19.01.2026 10:00")
    await state.set_state(EventStates.entering_datetime)


@crm_router.message(EventStates.entering_datetime)
async def process_event_datetime(message: types.Message, state: FSMContext):
    """Process event datetime input"""
    from datetime import datetime
    try:
        # Поддержка 10.00 и 10:00
        text = message.text.strip().replace('.', ':', 2)  # Первые 2 точки оставить, третью заменить
        # Формат: ДД.ММ.ГГГГ ЧЧ:ММ или ДД.ММ.ГГГГ ЧЧ.ММ
        parts = message.text.strip().split(' ')
        if len(parts) == 2:
            date_part = parts[0]  # ДД.ММ.ГГГГ
            time_part = parts[1].replace('.', ':')  # 10.00 → 10:00
            text = date_part + ' ' + time_part
        else:
            text = message.text.strip()
        dt = datetime.strptime(text, "%d.%m.%Y %H:%M")
        if dt < datetime.now():
            await message.answer("❌ Дата должна быть в будущем")
            return
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте: ДД.ММ.ГГГГ ЧЧ:ММ")
        return
    
    await state.update_data(scheduled_at=dt.isoformat())
    await message.answer("📝 Введите описание (или '.' чтобы пропустить):")
    await state.set_state(EventStates.entering_description)


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
                    'lead_id': int(data['event_lead_id']),
                    'user_id': callback.from_user.id,
                    'event_type': data['event_type'],
                    'description': data.get('event_description', ''),
                    'scheduled_at': data['scheduled_at'],
                    'remind_before_minutes': remind
                }
            ) as resp:
                if resp.status == 200:
                    event_type = EVENT_TYPES.get(data['event_type'], data['event_type'])
                    await callback.message.edit_text(
                        f"✅ Событие создано!\n\n"
                        f"{event_type}\n"
                        f"📅 {data['scheduled_at'][:16].replace('T', ' ')}\n"
                        f"⏰ Напоминание за {remind} мин"
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

