#!/usr/bin/env python3
"""Simplify client bot - remove menu, add language selection"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Simplifying client bot...")

# 1. Remove get_start_keyboard() call and replace with language selection
old_start = """    await state.set_state(SalesFlow.qualifying)
    await start_session(message.from_user.id, company_id=1)
    await message.answer("Привет! Я Умный Агент (BizDNAi).\\n\\n🚀 Я новое поколение корпоративного AI.\\n\\nЯ помогу подобрать идеальное решение.\\nПишите или говорите, и я вам отвечу.\\n\\nДля смены языка используйте /lang",reply_markup=get_start_keyboard())"""

new_start = """    await state.set_state(SalesFlow.qualifying)
    await start_session(message.from_user.id, company_id=1)
    
    # Language selection buttons
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    lang_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_en")],
        [InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang_kz"),
         InlineKeyboardButton(text="🇰🇬 Кыргызча", callback_data="lang_ky")],
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
         InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_uk")]
    ])
    
    await message.answer(
        "Привет! Я Умный Агент (BizDNAi).\\n🚀 Я новое поколение корпоративного AI.\\n\\n"
        "Hello! I'm Smart Agent (BizDNAi).\\n🚀 I'm the new generation of corporate AI.\\n\\n"
        "Выберите язык / Choose language:",
        reply_markup=lang_kb
    )"""

content = content.replace(old_start, new_start)
print("✅ Replaced start message with language selection")

# 2. Remove /lang command handler
import re
lang_handler = r"@router\.message\(Command\('lang'\)\).*?await message\.answer\([^)]+\)"
content = re.sub(lang_handler, '', content, flags=re.DOTALL)
print("✅ Removed /lang command")

# 3. Add language selection callback handler (insert after cmd_start)
lang_callback = """

@router.callback_query(F.data.startswith("lang_"))
async def set_language_callback(callback: types.CallbackQuery, state: FSMContext):
    \"\"\"Handle language selection\"\"\"
    lang = callback.data.split("_")[1]
    await state.update_data(language=lang)
    
    greetings = {
        'ru': 'Отлично! Теперь пишите или говорите, и я вам отвечу.',
        'en': 'Great! Now write or speak, and I will answer you.',
        'kz': 'Тамаша! Енді жазыңыз немесе сөйлеңіз, мен сізге жауап беремін.',
        'ky': 'Мыкты! Эми жазыңыз же сүйлөңүз, мен сизге жооп берем.',
        'uz': 'Ajoyib! Endi yozing yoki gapiring, men sizga javob beraman.',
        'uk': 'Чудово! Тепер пишіть або говоріть, і я вам відповім.'
    }
    
    await callback.message.edit_text(greetings.get(lang, greetings['ru']))
    await callback.answer()
"""

# Find where to insert (after cmd_start function)
marker = "@router.message(Command('id'))"
content = content.replace(marker, lang_callback + "\n" + marker)
print("✅ Added language selection callback")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Client bot simplified!")
