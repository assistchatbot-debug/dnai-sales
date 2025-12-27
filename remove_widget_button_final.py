#!/usr/bin/env python3
"""Remove Widget button from manager menu completely"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Removing Widget button...")

# Remove from menu keyboard (there are 2 different menus)
content = content.replace(
    '[KeyboardButton(text="📢 Каналы"), KeyboardButton(text="🌐 Виджет")]',
    '[KeyboardButton(text="📢 Каналы")]'
)

content = content.replace(
    '[KeyboardButton(text="📢 Каналы"),KeyboardButton(text="🌐 Виджет")]',
    '[KeyboardButton(text="📢 Каналы")]'
)

# Remove from help text
content = content.replace(
    '"<b>🌐 Виджет</b> - управление виджетом\\n"',
    ''
)

print("✅ Removed Widget button")

# Add leads period buttons to menu
old_menu_line = '[KeyboardButton(text="❓ Помощь"),KeyboardButton(text="🏠 Меню")]'
new_menu_line = '[KeyboardButton(text="📊 Лиды за неделю"),KeyboardButton(text="📊 Лиды за месяц")],[KeyboardButton(text="🏠 Меню")]'

content = content.replace(old_menu_line, new_menu_line)
print("✅ Added Leads period buttons")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Done!")
