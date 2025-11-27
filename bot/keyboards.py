from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
def get_start_keyboard():
    kb = [[KeyboardButton(text="🚀 Подобрать решение")], [KeyboardButton(text="📞 Связаться с менеджером")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
def get_recommendation_keyboard(session_id: str):
    kb = [[InlineKeyboardButton(text="📄 Подробнее", callback_data=f"details_{session_id}")], [InlineKeyboardButton(text="✅ Оформить заявку", callback_data=f"order_{session_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)
