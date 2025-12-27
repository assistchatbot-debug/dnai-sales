#!/usr/bin/env python3
"""Fix manager menu - remove Widget button, add Leads period buttons"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing manager menu...")

# Find and replace the menu on line 72
old_menu = 'kb=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📊 Статус"),KeyboardButton(text="📋 Лиды")],[KeyboardButton(text="📢 Каналы"),KeyboardButton(text="🌐 Виджет")],[KeyboardButton(text="❓ Помощь"),KeyboardButton(text="🏠 Меню")]],resize_keyboard=True)'

new_menu = 'kb=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📊 Статус"),KeyboardButton(text="📋 Лиды")],[KeyboardButton(text="📢 Каналы")],[KeyboardButton(text="📊 Лиды за неделю"),KeyboardButton(text="📊 Лиды за месяц")],[KeyboardButton(text="🏠 Меню")]],resize_keyboard=True)'

content = content.replace(old_menu, new_menu)
print("✅ Updated manager menu")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Done!")
