"""
CRM Handlers Module for BizDNAi Telegram Bot
Handles: Manager menu, Lead cards, Status changes, Notes, Coins
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


# === Manager Keyboard (закреплённое меню) ===

def get_manager_keyboard():
    """Manager bot keyboard - like admin but for sales managers"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мои лиды"), KeyboardButton(text="📊 Мой рейтинг")],
            [KeyboardButton(text="🏆 Лидерборд"), KeyboardButton(text="🏠 Меню")]
        ],
        resize_keyboard=True
    )


# === Helper Functions ===

async def is_manager(user_id: int, company_id: int) -> bool:
    """Check if user is registered manager for company"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/managers') as resp:
                if resp.status == 200:
                    managers = await resp.json()
                    return any(m.get('user_id') == user_id for m in managers)
    except:
        pass
    return False


async def get_manager_info(user_id: int, company_id: int) -> dict:
    """Get manager info from API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/managers/{user_id}') as resp:
                if resp.status == 200:
                    return await resp.json()
    except:
        pass
    return None


async def get_lead_details(company_id: int, lead_id: int) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}', timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logging.error(f"Get lead error: {e}")
    return None


async def get_statuses(company_id: int) -> list:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/statuses', timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logging.error(f"Get statuses error: {e}")
    return []


def format_lead_card(lead: dict, statuses: list = None) -> str:
    contact = lead.get('contact_info', {}) or {}
    name = contact.get('name', 'Не указано')
    phone = contact.get('phone', 'Не указан')
    temperature = contact.get('temperature', '🌤 Тёплый')
    interests = contact.get('interests', '')
    source = lead.get('source', 'web')
    created = lead.get('created_at', '')[:16].replace('T', ' ')
    current_status = lead.get('status', 'new')
    status_emoji, status_name = "🆕", "Новый"
    if statuses:
        for s in statuses:
            if s.get('code') == current_status:
                status_emoji = s.get('emoji', '🆕')
                status_name = s.get('name', current_status)
                break
    ai_section = ""
    if temperature or interests:
        ai_section = "\n🤖 <b>AI-анализ:</b>\n"
        if temperature: ai_section += f"🔥 Температура: {temperature}\n"
        if interests: ai_section += f"💡 Интересы: {interests}\n"
    return f"""📋 <b>Лид #{lead.get('id', '?')}</b>

👤 Имя: {name}
📞 Телефон: {phone}
📱 Источник: {source}
📅 Создан: {created}
{ai_section}
📊 Статус: {status_emoji} {status_name}"""


def get_status_keyboard(lead_id: int, statuses: list, current_status: str) -> InlineKeyboardMarkup:
    buttons, row = [], []
    for s in statuses:
        code, emoji = s.get('code', ''), s.get('emoji', '⚪')
        text = f"✓ {emoji}" if code == current_status else emoji
        row.append(InlineKeyboardButton(text=text, callback_data=f"lead_status:{lead_id}:{code}"))
        if len(row) >= 3:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    buttons.append([
        InlineKeyboardButton(text="📝 Заметка", callback_data=f"lead_note:{lead_id}")
    ])
    buttons.append([
        InlineKeyboardButton(text="📞 Позвонить", callback_data=f"lead_call:{lead_id}"),
        InlineKeyboardButton(text="💬 WhatsApp", callback_data=f"lead_wa:{lead_id}"),
        InlineKeyboardButton(text="✈️ Telegram", callback_data=f"lead_tg:{lead_id}")
    ])
    buttons.append([InlineKeyboardButton(text="« Назад к списку", callback_data="back_to_leads")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# === /join Command ===

@crm_router.message(Command('join'))
async def cmd_join(message: types.Message):
    """Manager joins company CRM"""
    company_id = getattr(message.bot, 'company_id', 1)
    user_id = message.from_user.id
    username = message.from_user.username or ''
    full_name = message.from_user.full_name or 'Менеджер'
    
    # Check if already registered
    if await is_manager(user_id, company_id):
        await message.answer(
            f"👋 С возвращением, {full_name}!\n\n"
            "Используйте меню для работы с лидами.",
            reply_markup=get_manager_keyboard()
        )
        return
    
    # Register as manager
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{API_BASE_URL}/crm/{company_id}/managers',
                json={
                    'telegram_id': user_id,
                    'telegram_username': username,
                    'full_name': full_name
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    await message.answer(
                        f"🎉 <b>Добро пожаловать, {full_name}!</b>\n\n"
                        "Вы зарегистрированы как менеджер.\n\n"
                        "📋 <b>Мои лиды</b> — работа с клиентами\n"
                        "📊 <b>Мой рейтинг</b> — ваши монетки\n"
                        "🏆 <b>Лидерборд</b> — топ менеджеров",
                        parse_mode='HTML',
                        reply_markup=get_manager_keyboard()
                    )
                else:
                    await message.answer("❌ Ошибка регистрации. Попробуйте позже.")
    except Exception as e:
        logging.error(f"Join error: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:50]}")


# === Manager Menu Handlers ===

@crm_router.message(F.text == "📋 Мои лиды")
async def my_leads_handler(message: types.Message):
    """Show leads assigned to manager"""
    company_id = getattr(message.bot, 'company_id', 1)
    user_id = message.from_user.id
    
    # Check if manager
    if not await is_manager(user_id, company_id):
        await message.answer("❌ Вы не зарегистрированы как менеджер.\nНапишите /join")
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            # Get leads (all for now, later filter by manager)
            async with session.get(
                f'{API_BASE_URL}/sales/{company_id}/leads',
                params={'limit': 20},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    leads = data if isinstance(data, list) else data.get('leads', [])
                    
                    # Filter leads with contacts
                    leads = [l for l in leads if l.get('contact_info') and 
                            (l['contact_info'].get('name') or l['contact_info'].get('phone'))]
                    
                    if not leads:
                        await message.answer("📋 <b>Мои лиды</b>\n\nЛидов пока нет", parse_mode='HTML')
                        return
                    
                    text = "📋 <b>Мои лиды</b>\n\n"
                    buttons = []
                    
                    for lead in leads[:10]:
                        contact = lead.get('contact_info', {}) or {}
                        name = contact.get('name', 'Без имени')
                        phone = contact.get('phone', '')[:10] if contact.get('phone') else ''
                        lead_id = lead.get('id', 0)
                        status = lead.get('status', 'new')
                        
                        # Status emoji
                        status_emoji = {'new': '🆕', 'in_progress': '📞', 'meeting': '📅', 'deal': '✅', 'rejected': '❌'}.get(status, '⚪')
                        
                        text += f"{status_emoji} #{lead_id} {name}"
                        if phone: text += f" ({phone}...)"
                        text += "\n"
                        
                        buttons.append([InlineKeyboardButton(
                            text=f"{status_emoji} Лид #{lead_id} - {name[:15]}",
                            callback_data=f"view_lead:{lead_id}"
                        )])
                    
                    text += "\n<i>Нажмите для просмотра карточки</i>"
                    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                    await message.answer(text, parse_mode='HTML', reply_markup=keyboard)
                else:
                    await message.answer("⚠️ Ошибка получения лидов")
    except Exception as e:
        logging.error(f"My leads error: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:50]}")


@crm_router.message(F.text == "📊 Мой рейтинг")
async def my_rating_handler(message: types.Message):
    """Show manager's coins and stats"""
    company_id = getattr(message.bot, 'company_id', 1)
    user_id = message.from_user.id
    
    if not await is_manager(user_id, company_id):
        await message.answer("❌ Вы не зарегистрированы. Напишите /join")
        return
    
    manager = await get_manager_info(user_id, company_id)
    if manager:
        coins = manager.get('coins', 0)
        leads_count = manager.get('leads_count', 0)
        deals_count = manager.get('deals_count', 0)
        
        await message.answer(
            f"📊 <b>Ваш рейтинг</b>\n\n"
            f"💰 Монетки: {coins}\n"
            f"📋 Лидов обработано: {leads_count}\n"
            f"✅ Сделок закрыто: {deals_count}",
            parse_mode='HTML'
        )
    else:
        await message.answer("📊 <b>Ваш рейтинг</b>\n\n💰 Монетки: 0\n\nНачните работать с лидами!", parse_mode='HTML')


@crm_router.message(F.text == "🏆 Лидерборд")
async def leaderboard_handler(message: types.Message):
    """Show top managers"""
    company_id = getattr(message.bot, 'company_id', 1)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/crm/{company_id}/leaderboard') as resp:
                if resp.status == 200:
                    leaders = await resp.json()
                    
                    if not leaders:
                        await message.answer("🏆 <b>Лидерборд</b>\n\nПока пусто. Будьте первым!", parse_mode='HTML')
                        return
                    
                    text = "🏆 <b>Лидерборд</b>\n\n"
                    medals = ['🥇', '🥈', '🥉']
                    
                    for i, m in enumerate(leaders[:10]):
                        medal = medals[i] if i < 3 else f"{i+1}."
                        name = m.get('full_name', 'Менеджер')
                        coins = m.get('coins', 0)
                        text += f"{medal} {name} — {coins} 💰\n"
                    
                    await message.answer(text, parse_mode='HTML')
                else:
                    await message.answer("🏆 <b>Лидерборд</b>\n\nПока пусто", parse_mode='HTML')
    except Exception as e:
        logging.error(f"Leaderboard error: {e}")
        await message.answer("❌ Ошибка загрузки")


@crm_router.message(F.text == "🏠 Меню")
async def manager_menu_handler(message: types.Message):
    """Show manager menu"""
    company_id = getattr(message.bot, 'company_id', 1)
    user_id = message.from_user.id
    
    if await is_manager(user_id, company_id):
        await message.answer("🏠 <b>Меню менеджера</b>", parse_mode='HTML', reply_markup=get_manager_keyboard())
    # If admin - don't handle, let handlers.py process


# === Lead Card Callbacks ===

@crm_router.callback_query(F.data.startswith("view_lead:"))
async def view_lead_callback(callback: types.CallbackQuery, state: FSMContext):
    lead_id = int(callback.data.split(":")[1])
    company_id = getattr(callback.bot, 'company_id', 1)
    lead = await get_lead_details(company_id, lead_id)
    if not lead:
        await callback.answer("❌ Лид не найден", show_alert=True)
        return
    statuses = await get_statuses(company_id)
    card_text = format_lead_card(lead, statuses)
    keyboard = get_status_keyboard(lead_id, statuses, lead.get('status', 'new'))
    await callback.message.edit_text(card_text, parse_mode='HTML', reply_markup=keyboard)
    await callback.answer()


@crm_router.callback_query(F.data.startswith("lead_status:"))
async def change_status_callback(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    lead_id, new_status = int(parts[1]), parts[2]
    company_id = getattr(callback.bot, 'company_id', 1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}/status',
                json={'status': new_status, 'manager_id': callback.from_user.id},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    coins = result.get('coins_earned', 0)
                    status_name = result.get('status_name', new_status)
                    await callback.answer(f"✅ {status_name} | +{coins} 💰" if coins > 0 else f"✅ {status_name}", show_alert=coins > 0)
                    lead = await get_lead_details(company_id, lead_id)
                    statuses = await get_statuses(company_id)
                    await callback.message.edit_text(format_lead_card(lead, statuses), parse_mode='HTML', reply_markup=get_status_keyboard(lead_id, statuses, new_status))
                else:
                    await callback.answer("❌ Ошибка", show_alert=True)
    except Exception as e:
        logging.error(f"Status error: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@crm_router.callback_query(F.data.startswith("lead_note:"))
async def add_note_callback(callback: types.CallbackQuery, state: FSMContext):
    lead_id = int(callback.data.split(":")[1])
    await state.update_data(note_lead_id=lead_id)
    await state.set_state(CRMStates.entering_note)
    await callback.message.answer(f"📝 <b>Заметка к лиду #{lead_id}</b>\n\nВведите текст:\n<i>/cancel для отмены</i>", parse_mode='HTML')
    await callback.answer()


@crm_router.message(CRMStates.entering_note)
async def process_note_text(message: types.Message, state: FSMContext):
    if message.text and message.text.startswith('/cancel'):
        await state.clear()
        await message.answer("❌ Отменено")
        return
    data = await state.get_data()
    lead_id = data.get('note_lead_id')
    company_id = getattr(message.bot, 'company_id', 1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{API_BASE_URL}/crm/{company_id}/leads/{lead_id}/notes',
                json={'text': message.text, 'manager_id': message.from_user.id, 'note_type': 'text'}
            ) as resp:
                if resp.status == 200:
                    await message.answer(f"✅ Заметка сохранена к лиду #{lead_id}")
                else:
                    await message.answer("❌ Ошибка")
    except Exception as e:
        logging.error(f"Note error: {e}")
        await message.answer("❌ Ошибка")
    await state.clear()


@crm_router.callback_query(F.data.startswith("lead_call:"))
async def call_lead_callback(callback: types.CallbackQuery):
    lead_id = int(callback.data.split(":")[1])
    company_id = getattr(callback.bot, 'company_id', 1)
    lead = await get_lead_details(company_id, lead_id)
    if lead:
        phone = (lead.get('contact_info', {}) or {}).get('phone', '')
        if phone:
            # Показать как кликабельную ссылку
            clean_phone = phone.replace(' ', '').replace('-', '')
            if not clean_phone.startswith('+'):
                clean_phone = '+' + clean_phone
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"📞 {phone}", url=f"tel:{clean_phone}")]
            ])
            await callback.message.answer("📞 Нажмите для звонка:", reply_markup=kb)
            await callback.answer()
        else:
            await callback.answer("❌ Телефон не указан", show_alert=True)
    else:
        await callback.answer("❌ Лид не найден", show_alert=True)


@crm_router.callback_query(F.data.startswith("lead_wa:"))
async def whatsapp_lead_callback(callback: types.CallbackQuery):
    lead_id = int(callback.data.split(":")[1])
    company_id = getattr(callback.bot, 'company_id', 1)
    lead = await get_lead_details(company_id, lead_id)
    if lead:
        phone = (lead.get('contact_info', {}) or {}).get('phone', '').replace('+', '').replace(' ', '').replace('-', '')
        if phone:
            await callback.message.answer(f"💬 <b>WhatsApp:</b>\nhttps://wa.me/{phone}", parse_mode='HTML')
            await callback.answer()
        else:
            await callback.answer("❌ Телефон не указан", show_alert=True)
    else:
        await callback.answer("❌ Лид не найден", show_alert=True)


@crm_router.callback_query(F.data == "back_to_leads")
async def back_to_leads_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()
