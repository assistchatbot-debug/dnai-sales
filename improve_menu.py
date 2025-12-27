#!/usr/bin/env python3
"""Improve manager menu and help"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Improving menu...")

# 1. Update help command text
old_help = '''        await message.answer(
            "📋 <b>Доступные команды:</b>\\n\\n"
            "<b>статус</b> - полная проверка всех систем\\n"
            "<b>лиды</b> - просмотр последних 5 лидов\\n"
            "<b>помощь</b> - список команд\\n\\n"
            "Также работают голосовые сообщения!",
            parse_mode='HTML'
        )'''

new_help = '''        await message.answer(
            "📋 <b>Доступные команды:</b>\\n\\n"
            "<b>📊 Статус</b> - проверка всех систем\\n"
            "<b>📋 Лиды</b> - просмотр последних лидов\\n"
            "<b>📢 Каналы</b> - список социальных каналов\\n"
            "<b>🌐 Виджет</b> - управление виджетом\\n"
            "<b>создать канал</b> - создать новый канал\\n\\n"
            "💡 Также работают голосовые сообщения!\\n\\n"
            "Используйте кнопки меню для быстрого доступа.",
            parse_mode='HTML'
        )'''

content = content.replace(old_help, new_help)
print("✅ Updated help text")

# 2. Add "🏠 Меню" button to the keyboard
old_keyboard = '''        kb=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📊 Статус"),KeyboardButton(text="📋 Лиды")],[KeyboardButton(text="📢 Каналы"),KeyboardButton(text="🌐 Виджет")],[KeyboardButton(text="❓ Помощь")]],resize_keyboard=True)'''

new_keyboard = '''        kb=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📊 Статус"),KeyboardButton(text="📋 Лиды")],[KeyboardButton(text="📢 Каналы"),KeyboardButton(text="🌐 Виджет")],[KeyboardButton(text="❓ Помощь"),KeyboardButton(text="🏠 Меню")]],resize_keyboard=True)'''

content = content.replace(old_keyboard, new_keyboard)
print("✅ Added '🏠 Меню' button")

# 3. Add handler for "🏠 Меню" button in process_manager_command
menu_handler = '''    # Menu button - restart command
    elif 'меню' in text_lower or 'menu' in text_lower:
        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📊 Статус"), KeyboardButton(text="📋 Лиды")],
                [KeyboardButton(text="📢 Каналы"), KeyboardButton(text="🌐 Виджет")],
                [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="🏠 Меню")]
            ],
            resize_keyboard=True
        )
        await message.answer("🏠 <b>Главное меню</b>", reply_markup=kb, parse_mode='HTML')
    
    # Help'''

old_help_section = '''    # Help'''
content = content.replace(old_help_section, menu_handler, 1)
print("✅ Added menu button handler")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ All improvements applied!")
