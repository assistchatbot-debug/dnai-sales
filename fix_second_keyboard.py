#!/usr/bin/env python3
"""Fix second keyboard to match the first one"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing second keyboard...")

# Find and replace the second keyboard (lines 394-400)
old_kb = """        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📊 Статус"), KeyboardButton(text="📋 Лиды")],
                [KeyboardButton(text="📢 Каналы")],
                [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="🏠 Меню")]
            ],"""

new_kb = """        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📊 Статус"), KeyboardButton(text="📋 Лиды")],
                [KeyboardButton(text="📢 Каналы")],
                [KeyboardButton(text="📊 Лиды за неделю"), KeyboardButton(text="📊 Лиды за месяц")],
                [KeyboardButton(text="🏠 Меню")]
            ],"""

content = content.replace(old_kb, new_kb)
print("✅ Fixed second keyboard")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Done!")
